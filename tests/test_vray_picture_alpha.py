"""Real PNG tests and fault injection; no Rhino/V-Ray render is simulated as proof."""
import copy
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "alpha", Path(__file__).resolve().parents[1] / "scripts/rhino8_vray_picture_alpha.py")
alpha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alpha)


class FakeHost:
    """Fault-injectable storage, independent of the Rhino material API."""
    def __init__(self, paths, fail=None):
        self.document_path = str(Path(paths[0]).parent / "model.3dm")
        self.paths = paths
        self.fail = fail
        self.assignments = {str(i): "original-shared" for i in range(len(paths))}
        self.materials = []
        self.calls = []
        self.counter = 0

    def inspect(self, object_id):
        self.calls.append("inspect")
        if self.fail == "inspect" and object_id == "1":
            raise alpha.PreflightError("invalid second object")
        return {"id": object_id, "original_path": self.paths[int(object_id)],
                "uv": {"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                       "channel": 2, "projection": "MappingChannel", "repeating": True},
                "original": self.assignments[object_id]}

    def check_original(self, item):
        self.calls.append("check")
        if self.fail == "stale":
            raise alpha.PreflightError("stale")
        if self.assignments[item["id"]] != item["original"]:
            raise alpha.PreflightError("assignment changed")

    def build_material(self, item, mask):
        self.calls.append("build")
        if self.fail == "build" and item["id"] == "1":
            raise RuntimeError("factory failed")
        return {"id": item["id"], "image": item["path"], "mask": mask,
                "uv": copy.deepcopy(item["uv"])}

    def begin(self):
        self.calls.append("begin")
        if self.fail == "begin":
            raise RuntimeError("undo unavailable")
        return 42

    def end(self, token):
        self.calls.append("end")

    def attach(self, material):
        self.calls.append("attach")
        self.materials.append(material)
        if self.fail == "attach" and material["id"] == "1":
            raise RuntimeError("attach mutated then failed")

    def assign(self, item, material):
        self.calls.append("assign")
        self.assignments[item["id"]] = material
        if self.fail in ("assign", "restore", "cleanup") and item["id"] == "1":
            raise RuntimeError("assign mutated then failed")

    def verify(self, item, material):
        self.calls.append("verify")
        if self.fail == "verify" and item["id"] == "1":
            raise RuntimeError("verification failed")

    def restore(self, item):
        self.calls.append("restore")
        if self.fail == "restore":
            raise RuntimeError("host restoration failed")
        self.assignments[item["id"]] = item["original"]

    def discard(self, material):
        self.calls.append("discard")
        if self.fail == "cleanup":
            raise RuntimeError("host cleanup failed")
        if material in self.materials:
            self.materials.remove(material)

    def finish_rollback(self):
        self.calls.append("finish_rollback")


class AlphaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.paths = []
        for i, values in enumerate(([0, 64, 128, 255], [255, 160, 80, 0])):
            path = self.folder / ("source-{}.png".format(i))
            image = Image.new("RGBA", (2, 2))
            image.putdata([(10, 20, 30, value) for value in values])
            image.save(path)
            self.paths.append(str(path))
        self.initial_files = set(self.folder.iterdir())

    def tearDown(self):
        self.temp.cleanup()

    def test_alpha_bytes_exact_not_inverted_or_flipped(self):
        result = alpha.read_png(self.paths[0])
        with Image.open(io.BytesIO(result["mask_bytes"])) as mask:
            self.assertEqual(mask.size, (2, 2))
            self.assertEqual(list(mask.getdata()), [0, 64, 128, 255])
        self.assertEqual(result["alpha_range"], [0, 255])

    def test_palette_trns_supported(self):
        path = self.folder / "palette.png"
        image = Image.new("P", (2, 1))
        image.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
        image.putdata([0, 1])
        image.save(path, transparency=0)
        result = alpha.read_png(str(path))
        with Image.open(io.BytesIO(result["mask_bytes"])) as mask:
            self.assertEqual(list(mask.getdata()), [0, 255])

    def test_no_alpha_or_fully_opaque_refused(self):
        for mode in ("RGB", "RGBA"):
            path = self.folder / "opaque.png"
            Image.new(mode, (1, 1), "white").save(path)
            with self.assertRaises(alpha.PreflightError):
                alpha.read_png(str(path))

    def test_16bit_and_broken_png_refused(self):
        path = self.folder / "bad.png"
        Image.new("I;16", (2, 2)).save(path)
        with self.assertRaises(alpha.PreflightError):
            alpha.read_png(str(path))
        path.write_bytes(b"broken")
        with self.assertRaises(alpha.PreflightError):
            alpha.read_png(str(path))

    def test_relative_image_resolves_only_against_document(self):
        self.assertEqual(alpha.resolve_image("source-0.png", str(self.folder / "model.3dm")), self.paths[0])
        with self.assertRaises(alpha.PreflightError):
            alpha.resolve_image("source-0.png", "")
        with self.assertRaises(alpha.PreflightError):
            alpha.resolve_image("missing.png", str(self.folder / "model.3dm"))

    def test_default_dry_run_never_calls_mutations_or_writes_files(self):
        host = FakeHost(self.paths)
        report = alpha.run(host, ["0", "1"])
        self.assertEqual(report["status"], "dry-run")
        self.assertEqual(host.calls, ["inspect", "inspect"])
        self.assertEqual(set(self.folder.iterdir()), self.initial_files)
        self.assertEqual(host.assignments, {"0": "original-shared", "1": "original-shared"})

    def test_bad_batch_fails_before_any_mutation(self):
        host = FakeHost(self.paths, "inspect")
        with self.assertRaises(alpha.PreflightError):
            alpha.run(host, ["0", "1"], False, str(self.folder))
        self.assertEqual(host.calls, ["inspect", "inspect"])
        self.assertEqual(set(self.folder.iterdir()), self.initial_files)

    def test_empty_duplicate_and_nonboolean_mode_refused(self):
        for ids in ([], ["0", "0"]):
            with self.assertRaises(alpha.PreflightError):
                alpha.run(FakeHost(self.paths), ids)
        with self.assertRaises(alpha.PreflightError):
            alpha.run(FakeHost(self.paths), ["0"], "Apply")

    def test_apply_uses_individual_paths_and_uv_is_unchanged(self):
        host = FakeHost(self.paths)
        result = alpha.run(host, ["0", "1"], False, str(self.folder))
        self.assertEqual(result["status"], "applied")
        self.assertEqual([host.assignments[i]["image"] for i in ("0", "1")], self.paths)
        self.assertEqual(len(host.materials), 2)
        for item in host.materials:
            self.assertTrue(Path(item["mask"]).is_file())
            self.assertEqual(item["uv"]["channel"], 2)
        self.assertLess(host.calls.index("build"), host.calls.index("begin"))
        self.assertEqual(host.calls[-1], "end")

    def test_every_operational_failure_restores_all_assignments_and_files(self):
        for stage in ("build", "begin", "attach", "assign", "verify"):
            with self.subTest(stage=stage):
                host = FakeHost(self.paths, stage)
                with self.assertRaisesRegex(alpha.ApplyError, "restored"):
                    alpha.run(host, ["0", "1"], False, str(self.folder))
                self.assertEqual(host.assignments, {"0": "original-shared", "1": "original-shared"})
                self.assertEqual(host.materials, [])
                self.assertEqual(set(self.folder.iterdir()), self.initial_files)

    def test_image_change_or_stale_plan_refused_before_writes(self):
        host = FakeHost(self.paths)
        plan = alpha.prepare(host, ["0", "1"])
        Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(self.paths[1])
        with self.assertRaises(alpha.PreflightError):
            alpha.apply(host, plan, str(self.folder))
        self.assertNotIn("build", host.calls)
        host = FakeHost(self.paths, "stale")
        with self.assertRaises(alpha.PreflightError):
            alpha.run(host, ["0"], False, str(self.folder))
        self.assertNotIn("build", host.calls)

    def test_restore_failure_keeps_assets_and_reports_incomplete(self):
        host = FakeHost(self.paths, "restore")
        with self.assertRaisesRegex(alpha.ApplyError, "restoration incomplete"):
            alpha.run(host, ["0", "1"], False, str(self.folder))
        self.assertTrue(host.materials)
        self.assertNotIn("discard", host.calls)
        self.assertEqual(len(list(self.folder.glob("rhino-picture-alpha-*"))), 1)

    def test_cleanup_failure_is_reported(self):
        host = FakeHost(self.paths, "cleanup")
        with self.assertRaisesRegex(alpha.ApplyError, "material cleanup"):
            alpha.run(host, ["0", "1"], False, str(self.folder))
        self.assertEqual(host.assignments, {"0": "original-shared", "1": "original-shared"})

    def test_uv_comparison_rejects_changed_channel_or_transform(self):
        uv = FakeHost(self.paths).inspect("0")["uv"]
        self.assertTrue(alpha.same_uv(uv, copy.deepcopy(uv)))
        for key, value in (("channel", 7), ("matrix", [0] * 16)):
            other = dict(uv, **{key: value})
            self.assertFalse(alpha.same_uv(uv, other))


if __name__ == "__main__":
    unittest.main()
