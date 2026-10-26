import importlib.util
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    "probe", Path(__file__).resolve().parents[1] / "scripts/rhino8_vray_picture_alpha_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_apply_refused_before_host_access(self):
        for value in (False, None, 1, "true"):
            with self.assertRaises(probe.ApplyUnavailable):
                probe.run(None, None, dry_run=value)

    def test_relative_path_not_resolved(self):
        self.assertEqual(probe.png_header("image.png")["status"], "unresolved")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(probe.png_header(str(Path(directory) / "missing.png"))["status"], "unreadable")

    def test_truncated_header(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(b"\x89PNG\r\n\x1a\n")
            file.flush()
            self.assertEqual(probe.png_header(file.name)["status"], "not_png_header")

    def test_alpha_and_indexed_headers(self):
        for color in (2, 3, 4, 6):
            with tempfile.NamedTemporaryFile() as file:
                # A synthetic header, deliberately not a valid decoded PNG.
                file.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                           + struct.pack(">IIBBBBB", 12, 34, 8, color, 0, 0, 0) + b"0000")
                file.flush()
                result = probe.png_header(file.name)
                self.assertEqual(result["alpha_channel_in_header"], color in (4, 6))
                self.assertFalse(result["decoded_pixels"])
                self.assertEqual(result["trns"], "not_inspected")

    def fixture(self, paths, source="MaterialFromObject"):
        objects, materials = [], []
        for index, path in enumerate(paths):
            objects.append(NS(Id=str(index), Geometry=NS(GetType=lambda: NS(Name="Brep")),
                              Attributes=NS(MaterialSource=source, MaterialIndex=index)))
            materials.append(NS(GetBitmapTexture=lambda p=path: NS(FileName=p)))
        class Materials(list):
            @property
            def Count(self):
                return len(self)
        table = NS(GetSelectedObjects=Mock(return_value=objects))
        doc = NS(Objects=table, Materials=Materials(materials))
        vray = NS(Version=74002, VRayVersion=70000,
                  Scene=NS(PluginFromObject=Mock(return_value=None)))
        return doc, vray

    def test_individual_paths_kept_without_geometry_writes(self):
        doc, vray = self.fixture(["one.png", "two.png"])
        report = probe.run(doc, vray)
        self.assertEqual([r["image_path"] for r in report["objects"]], ["one.png", "two.png"])
        self.assertFalse(report["apply_available"])
        doc.Objects.GetSelectedObjects.assert_called_once_with(False, False)
        self.assertEqual(vray.Scene.PluginFromObject.call_count, 2)

    def test_layer_material_not_guessed(self):
        doc, vray = self.fixture(["one.png"], "MaterialFromLayer")
        result = probe.run(doc, vray)["objects"][0]
        self.assertEqual(result["path_status"], "unsupported_material_source")
        self.assertNotIn("image_path", result)

    def test_host_error_reported_without_fallback(self):
        doc, vray = self.fixture(["one.png"])
        vray.Scene.PluginFromObject.side_effect = RuntimeError("not linked")
        result = probe.run(doc, vray)["objects"][0]
        self.assertEqual(result["inspection_error"], "not linked")


if __name__ == "__main__":
    unittest.main()
