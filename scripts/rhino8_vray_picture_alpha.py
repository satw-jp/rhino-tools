#! python3
# -*- coding: utf-8 -*-
"""Apply PNG cutout alpha through Rhino PBR, supported by V-Ray.

Rhino 8 Windows / Python 3. Host/render integration is not yet certified.
See docs/vray-picture-alpha.md. The default is a read-only dry-run.
"""
import hashlib
import json
import math
import os
import shutil
import tempfile
import struct
import zlib

VERSION = "1.0.2"


class PreflightError(RuntimeError):
    pass


class ApplyError(RuntimeError):
    """Includes rollback errors rather than claiming a successful restoration."""


def png_chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def png_metadata(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PreflightError("PNG required")
    position, chunks = 8, []
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        end = position + 12 + length
        if end > len(data):
            raise PreflightError("Truncated PNG")
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        crc = struct.unpack(">I", data[position + 8 + length:end])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise PreflightError("PNG checksum mismatch")
        chunks.append((kind, payload))
        position = end
        if kind == b"IEND":
            break
    if (not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13
            or chunks[-1] != (b"IEND", b"") or position != len(data)):
        raise PreflightError("Invalid PNG structure")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1])
    if (not width or not height or width * height > 16000000
            or depth == 16 or compression != 0 or filtering != 0 or interlace not in (0, 1)):
        raise PreflightError("Unsupported PNG (16-bit or over 16 million pixels)")
    if b"acTL" in [kind for kind, _ in chunks]:
        raise PreflightError("Static PNG required")
    if color not in (4, 6) and not any(kind == b"tRNS" for kind, _ in chunks):
        raise PreflightError("PNG has no alpha/tRNS")
    return width, height


def _decode_windows(data):
    """Use Rhino's installed .NET / Windows GDI+. No pip, NuGet or download."""
    if os.name != "nt":
        raise PreflightError("PNG decoding requires Rhino's Windows .NET runtime")
    import clr
    clr.AddReference("System.Drawing")
    from System import Array, Byte
    from System.Drawing import Bitmap
    from System.IO import MemoryStream
    stream = MemoryStream(Array[Byte](data))
    bitmap = None
    try:
        bitmap = Bitmap(stream)
        width, height = int(bitmap.Width), int(bitmap.Height)
        # GetPixel supports indexed/gray/RGBA images without unsafe pixel-format
        # conversions. Alpha is taken directly; RGB/color management is irrelevant.
        pixels = bytes(int(bitmap.GetPixel(x, y).A)
                       for y in range(height) for x in range(width))
        return width, height, pixels
    finally:
        if bitmap is not None:
            bitmap.Dispose()
        stream.Dispose()


def encode_alpha_png(width, height, pixels):
    if len(pixels) != width * height:
        raise PreflightError("Decoded alpha size mismatch")
    scanlines = b"".join(b"\x00" + pixels[y * width:(y + 1) * width]
                         for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(scanlines)) + png_chunk(b"IEND", b""))


def read_png(path):
    with open(path, "rb") as stream:
        data = stream.read()
    width, height = png_metadata(data)
    decoded_width, decoded_height, pixels = _decode_windows(data)
    if (decoded_width, decoded_height) != (width, height) or len(pixels) != width * height:
        raise PreflightError("Decoded PNG size mismatch")
    extrema = (min(pixels), max(pixels))
    if extrema == (255, 255):
        raise PreflightError("PNG is fully opaque: " + path)
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "size": [width, height], "alpha_range": list(extrema),
            "mask_bytes": encode_alpha_png(width, height, pixels)}


def resolve_image(path, document_path):
    if not path:
        raise PreflightError("Picture has no external bitmap path")
    if not os.path.isabs(path):
        if not document_path:
            raise PreflightError("Save the 3dm before resolving a relative image path")
        path = os.path.join(os.path.dirname(document_path), path)
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise PreflightError("External PNG missing (embedded-only images unsupported): " + path)
    return path


def matrix_values(matrix):
    values = [float(matrix[row, col]) for row in range(4) for col in range(4)]
    if not all(math.isfinite(value) for value in values):
        raise PreflightError("Non-finite UV transform")
    return values


def uv_signature(simulation):
    """Snapshot the actual mapping, including the full matrix, not just scale."""
    return {"matrix": matrix_values(simulation.LocalMappingTransform),
            "channel": int(simulation.MappingChannel),
            "projection": str(simulation.ProjectionMode),
            "repeating": bool(simulation.Repeating)}


def same_uv(left, right):
    return (all(left[key] == right[key] for key in ("channel", "projection", "repeating"))
            and all(abs(a - b) <= 1e-10 for a, b in zip(left["matrix"], right["matrix"])))


def prepare(host, object_ids):
    """Read/validate the entire batch before allowing any filesystem/model write."""
    if not object_ids or len(set(map(str, object_ids))) != len(object_ids):
        raise PreflightError("Select one or more distinct whole Picture objects")
    plan = []
    for object_id in object_ids:
        item = host.inspect(object_id)
        item["path"] = resolve_image(item["original_path"], host.document_path)
        item["png"] = read_png(item["path"])
        plan.append(item)
    return plan


def summary(plan):
    return {"version": VERSION, "method": "Rhino PBR Alpha mask (V-Ray direct rendering)",
            "objects": [{"object_id": str(item["id"]),
                         "source_image": item["original_path"],
                         "resolved_image": item["path"], "uv": item["uv"],
                         "size": item["png"]["size"],
                         "alpha_range": item["png"]["alpha_range"]} for item in plan]}


def run(host, object_ids, dry_run=True, output_parent=None):
    if type(dry_run) is not bool:
        raise PreflightError("dry_run must be True or False")
    plan = prepare(host, object_ids)
    if dry_run:
        return dict(summary(plan), status="dry-run")
    if output_parent is None:
        raise PreflightError("A persistent mask folder is required for Apply")
    return apply(host, plan, output_parent)


def apply(host, plan, output_parent):
    """Explicit compensation; V-Ray Transaction is not assumed to roll back.

    New materials are isolated per object. Original materials remain untouched.
    The host must be quiescent (no interactive render or other scripts running).
    """
    if not plan:
        raise PreflightError("Empty plan")
    if not os.path.isdir(output_parent):
        raise PreflightError("Choose an existing folder for persistent alpha masks")
    # Reject stale geometry, attributes, image content or bitmap settings.
    for item in plan:
        host.check_original(item)
        with open(item["path"], "rb") as stream:
            if hashlib.sha256(stream.read()).hexdigest() != item["png"]["sha256"]:
                raise PreflightError("Image changed after dry-run: " + item["path"])
    folder, staged, touched, token = None, [], [], None
    try:
        folder = tempfile.mkdtemp(prefix="rhino-picture-alpha-", dir=output_parent)
        # Stage every image/material before assigning anything to model objects.
        for index, item in enumerate(plan):
            mask = os.path.join(folder, "alpha-{:04d}.png".format(index + 1))
            with open(mask, "xb") as stream:
                stream.write(item["png"]["mask_bytes"])
            material = host.build_material(item, mask)
            staged.append(material)
        token = host.begin()
        for item, material in zip(plan, staged):
            host.check_original(item)
            host.attach(material)
            # Register before assignment: a host can mutate then report failure.
            touched.append(item)
            host.assign(item, material)
            host.verify(item, material)
        host.end(token)
        token = None
    except BaseException as error:
        rollback_errors = []
        for item in reversed(touched):
            try:
                host.restore(item)
            except BaseException as restore_error:
                rollback_errors.append("restore {}: {}".format(item["id"], restore_error))
        # Keep materials/files if restoration failed, to avoid dangling references.
        if not rollback_errors:
            for material in reversed(staged):
                try:
                    host.discard(material)
                except BaseException as remove_error:
                    rollback_errors.append("material cleanup: " + str(remove_error))
        if token is not None and not rollback_errors:
            try:
                host.finish_rollback()
            except BaseException as finish_error:
                rollback_errors.append("document cleanup: " + str(finish_error))
        if token is not None:
            try:
                host.end(token)
            except BaseException as end_error:
                rollback_errors.append("undo record: " + str(end_error))
        if folder and not rollback_errors:
            try:
                shutil.rmtree(folder)
            except OSError as file_error:
                rollback_errors.append("mask cleanup: " + str(file_error))
        if rollback_errors:
            raise ApplyError("FAILED; restoration incomplete. Do not save over the original. "
                             "Masks: {}. Cause: {}. Details: {}".format(
                                 folder, error, "; ".join(rollback_errors))) from error
        raise ApplyError("Failed; object assignments restored and new assets removed: "
                         + str(error)) from error
    return {"status": "applied", "count": len(plan), "mask_folder": folder}


class RhinoHost:
    def __init__(self, doc):
        import Rhino
        self.R = Rhino
        self.doc = doc
        self.document_path = doc.Path
        self.generation = Rhino.Render.RenderTexture.TextureGeneration.Disallow
        self.context = Rhino.Render.RenderContent.ChangeContexts.Program
        self.serialization = Rhino.FileIO.SerializationOptions()
        self.serialization.WriteUserData = True

    def data_signature(self, value):
        # ObjectAttributes/TextureMapping are not GeometryBase and have no DataCRC.
        serialized = value.ToJSON(self.serialization)
        if not serialized:
            raise PreflightError("Cannot serialize attributes or mapping for comparison")
        canonical = json.dumps(json.loads(serialized), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def mapping_signature(self, obj):
        result = []
        for channel in sorted(obj.GetTextureChannels()):
            mapping, transform = obj.GetTextureMapping(
                channel, self.R.Geometry.Transform.Identity)
            if mapping is None:
                raise PreflightError("Cannot read existing UV mapping channel")
            result.append((int(channel), self.data_signature(mapping),
                           matrix_values(mapping.PrimitiveTransform),
                           matrix_values(mapping.UvwTransform), matrix_values(transform)))
        return result

    def inspect(self, object_id):
        obj = self.doc.Objects.FindId(object_id)
        if obj is None or not obj.IsPictureFrame:
            raise PreflightError("Not a Picture: " + str(object_id))
        if (obj.IsLocked or obj.IsReference or obj.IsInstanceDefinitionGeometry
                or obj.HasSubobjectMaterials or obj.HasDynamicTransform):
            raise PreflightError("Locked/reference/block/subobject/dynamic Picture unsupported")
        material = obj.GetRenderMaterial(True)
        if material is None:
            raise PreflightError("Picture render material unavailable")
        # Restrict to the native Picture shader, not a procedural/V-Ray graph.
        if material.TypeId != self.R.Render.ContentUuids.PictureMaterialType:
            raise PreflightError("Expected a native Picture material")
        bitmap = material.GetTextureFromUsage(
            self.R.Render.RenderMaterial.StandardChildSlots.Diffuse)
        bitmap_types = (self.R.Render.ContentUuids.BitmapTextureType,
                        self.R.Render.ContentUuids.SimpleBitmapTextureType)
        if bitmap is None or bitmap.TypeId not in bitmap_types:
            raise PreflightError("Expected a plain Picture bitmap texture")
        simulation = bitmap.SimulatedTexture(self.generation)
        try:
            uv = uv_signature(simulation)
        finally:
            simulation.Dispose()
        return {"id": obj.Id, "attributes": obj.Attributes.Duplicate(),
                "attribute_signature": self.data_signature(obj.Attributes),
                "geometry_crc": int(obj.Geometry.DataCRC(0)),
                "object_mapping": self.mapping_signature(obj),
                "bitmap": bitmap, "bitmap_hash": int(bitmap.RenderHash),
                "original_path": str(bitmap.Filename or ""), "uv": uv}

    def check_original(self, item):
        obj = self.doc.Objects.FindId(item["id"])
        if (obj is None or int(obj.Geometry.DataCRC(0)) != item["geometry_crc"]
                or self.data_signature(obj.Attributes) != item["attribute_signature"]
                or int(item["bitmap"].RenderHash) != item["bitmap_hash"]
                or self.mapping_signature(obj) != item["object_mapping"]):
            raise PreflightError("Picture changed after inspection: " + str(item["id"]))

    def build_material(self, item, mask):
        R = self.R
        material = R.Render.RenderContentType.NewContentFromTypeId(
            R.Render.ContentUuids.PhysicallyBasedMaterialType)
        if material is None:
            raise PreflightError("PBR factory unavailable")
        try:
            material.Name = "PNG Alpha " + str(item["id"])
            names = R.Render.ParameterNames.PhysicallyBased
            material.BeginChange(self.context)
            try:
                from System import Double
                for name, value in ((names.Alpha, 1.0), (names.Opacity, 1.0),
                                    (names.Metallic, 0.0), (names.Specular, 0.0),
                                    (names.Roughness, 1.0)):
                    if not material.SetParameter(name, Double(value)):
                        raise PreflightError("PBR parameter rejected: " + name)
                if not material.SetParameter(names.BaseColor, R.Display.Color4f.White):
                    raise PreflightError("PBR BaseColor rejected")
                slots = R.Render.ChildSlotNames.PhysicallyBased
                for slot, path in ((slots.BaseColor, item["path"]), (slots.Alpha, mask)):
                    # A fresh bitmap avoids carrying Picture color adjustments into alpha.
                    sim = item["bitmap"].SimulatedTexture(self.generation)
                    try:
                        sim.Filename = path
                        texture = R.Render.RenderTexture.NewBitmapTexture(sim, self.doc)
                    finally:
                        sim.Dispose()
                    if texture is None:
                        raise PreflightError("Bitmap factory unavailable")
                    if os.path.normcase(os.path.abspath(texture.Filename)) != os.path.normcase(path):
                        texture.Dispose()
                        raise PreflightError("Bitmap factory did not retain the image path")
                    # Refuse any conversion which changes the texture mapping.
                    probe = texture.SimulatedTexture(self.generation)
                    try:
                        if not same_uv(item["uv"], uv_signature(probe)):
                            texture.Dispose()
                            raise PreflightError("Bitmap factory changed the original UV")
                    finally:
                        probe.Dispose()
                    if not material.SetChild(texture, slot):
                        texture.Dispose()
                        raise PreflightError("PBR texture slot rejected: " + slot)
                    material.SetChildSlotOn(slot, True, self.context)
                    material.SetChildSlotAmount(slot, 100.0, self.context)
                    if not material.ChildSlotOn(slot) or material.ChildSlotAmount(slot) != 100.0:
                        raise PreflightError("PBR texture enable/amount not retained")
            finally:
                material.EndChange()
            return material
        except BaseException:
            material.Dispose()
            raise

    def begin(self):
        # RDK assignment can generate legacy material rows as a side effect.
        self.legacy_before = {str(material.Id) for material in self.doc.Materials}
        self.rdk_before = {str(material.Id) for material in self.doc.RenderMaterials}
        token = self.doc.BeginUndoRecord("Picture PNG alpha")
        if not token:
            raise PreflightError("Cannot open a separate undo record; run from ScriptEditor")
        return token

    def end(self, token):
        if not self.doc.EndUndoRecord(token):
            raise ApplyError("Cannot close undo record")

    def attach(self, material):
        if not self.doc.RenderMaterials.Add(material):
            raise ApplyError("Cannot add PBR material")

    def assign(self, item, material):
        attributes = item["attributes"].Duplicate()
        attributes.RenderMaterial = material
        if not self.doc.Objects.ModifyAttributes(item["id"], attributes, True):
            raise ApplyError("Material assignment failed: " + str(item["id"]))

    def verify(self, item, material):
        obj = self.doc.Objects.FindId(item["id"])
        assigned = obj.GetRenderMaterial(True)
        if (int(obj.Geometry.DataCRC(0)) != item["geometry_crc"] or assigned is None
                or assigned.Id != material.Id):
            raise ApplyError("Geometry/assignment verification failed")
        # Check both the mapping definition and its object transform for all channels.
        if self.mapping_signature(obj) != item["object_mapping"]:
            raise ApplyError("Object UV mapping changed")
        slots = self.R.Render.ChildSlotNames.PhysicallyBased
        for slot in (slots.BaseColor, slots.Alpha):
            texture = assigned.FindChild(slot)
            if texture is None:
                raise ApplyError("Assigned PBR texture is missing")
            probe = texture.SimulatedTexture(self.generation)
            try:
                if not same_uv(item["uv"], uv_signature(probe)):
                    raise ApplyError("Assigned PBR texture UV changed")
            finally:
                probe.Dispose()

    def restore(self, item):
        if not self.doc.Objects.ModifyAttributes(item["id"], item["attributes"], True):
            raise ApplyError("Cannot restore attributes")
        obj = self.doc.Objects.FindId(item["id"])
        if (self.data_signature(obj.Attributes) != item["attribute_signature"]
                or int(obj.Geometry.DataCRC(0)) != item["geometry_crc"]
                or self.mapping_signature(obj) != item["object_mapping"]):
            raise ApplyError("Restored state does not match snapshot")

    def discard(self, material):
        if material.DocumentOwner is not None:
            if not self.doc.RenderMaterials.Remove(material):
                raise ApplyError("Cannot remove staged material")
        else:
            material.Dispose()

    def finish_rollback(self):
        # Only rows created during this operation; original shared materials survive.
        for material in list(self.doc.Materials):
            if not material.IsDeleted and str(material.Id) not in self.legacy_before:
                if not self.doc.Materials.Delete(material.MaterialIndex, True):
                    raise ApplyError("Cannot remove generated legacy material")
        if {str(material.Id) for material in self.doc.RenderMaterials} != self.rdk_before:
            raise ApplyError("Render material table differs after rollback")


def main():
    import Rhino
    import rhinoscriptsyntax as rs
    import scriptcontext as sc
    if Rhino.RhinoApp.ExeVersion != 8 or os.name != "nt":
        raise PreflightError("Rhino 8 Windows / ScriptEditor Python 3 required")
    objects = list(sc.doc.Objects.GetSelectedObjects(False, False))
    if not objects:
        print("Select existing whole Picture objects, then run again.")
        return
    host = RhinoHost(sc.doc)
    plan = prepare(host, [obj.Id for obj in objects])
    print(json.dumps(summary(plan), ensure_ascii=False, indent=2))
    choice = rs.GetString("PNG Alpha: DryRun or Apply", "DryRun", ["DryRun", "Apply"])
    if choice != "Apply":
        print("Dry-run complete. No model or mask files changed.")
        return
    parent = rs.BrowseForFolder(None, "Choose a persistent folder for alpha masks")
    if not parent:
        return
    try:
        result = apply(host, plan, parent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        sc.doc.Views.Redraw()


if __name__ == "__main__":
    main()
