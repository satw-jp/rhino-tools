# -*- coding: utf-8 -*-
"""Read-only evidence collector. NOT an alpha conversion tool.

Rhino 8 / Windows / ScriptEditor Python 3. See docs/vray-picture-alpha.md.
No scene transactions, parameter setters, material simulation or document writes.
"""
import json
import os
import struct


class ApplyUnavailable(RuntimeError):
    pass


def png_header(path):
    """Read only the signature/IHDR; do not claim decoded alpha coverage.

    Indexed PNGs can use tRNS: unknown here rather than a false 'no alpha'.
    Relative/embedded paths are not resolved or substituted.
    """
    if not path or not os.path.isabs(path):
        return {"status": "unresolved", "reason": "absolute external path required"}
    try:
        with open(path, "rb") as stream:
            header = stream.read(33)
    except OSError as exc:
        return {"status": "unreadable", "reason": str(exc)}
    if (len(header) != 33 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[8:16] != b"\x00\x00\x00\x0dIHDR"):
        return {"status": "not_png_header"}
    width, height, depth, color_type = struct.unpack(">IIBB", header[16:26])
    return {"status": "header_only", "width": width, "height": height,
            "bit_depth": depth, "color_type": color_type,
            "alpha_channel_in_header": color_type in (4, 6),
            "trns": "not_inspected", "decoded_pixels": False}


def plugin_info(plugin):
    if plugin is None:
        return None
    # Names/types only: arbitrary COM parameter values may not be JSON serializable.
    return {"name": str(plugin.Name), "type": str(plugin.Type),
            "parameters": [str(name) for name in plugin.ParamNames]}


def collect(doc, vray):
    """Inspect preselected candidates. Selection is NOT proof of Picture identity.

    Only directly assigned legacy material slots are read. No fallback to a
    guessed path, parent/layer material, generated simulation or shared asset.
    PluginFromObject is diagnostic: its result is not assumed to be a material.
    """
    report = {"schema": 1, "mode": "dry-run", "apply_available": False,
              "vray_version_raw": str(vray.Version),
              "vray_core_version_raw": str(vray.VRayVersion), "objects": [],
              "blockers": ["7.40.02 opacity user-data names/values not verified",
                           "Picture-to-V-Ray material binding not verified",
                           "atomic rollback across Rhino/V-Ray not verified"]}
    for obj in doc.Objects.GetSelectedObjects(False, False):
        item = {"object_id": str(obj.Id), "picture_identity": "not_verified",
                "geometry_type": str(obj.Geometry.GetType().Name),
                "material_source": str(obj.Attributes.MaterialSource),
                "material_index": int(obj.Attributes.MaterialIndex)}
        try:
            # Do not access Material.RenderMaterial: its getter may create data.
            if str(obj.Attributes.MaterialSource) != "MaterialFromObject":
                item["path_status"] = "unsupported_material_source"
            elif not 0 <= item["material_index"] < doc.Materials.Count:
                item["path_status"] = "no_legacy_material"
            else:
                texture = doc.Materials[item["material_index"]].GetBitmapTexture()
                if texture is None:
                    item["path_status"] = "no_legacy_bitmap"
                else:
                    path = str(texture.FileName or "")
                    item.update(image_path=path, path_status="legacy_slot_only",
                                png=png_header(path))
            item["linked_plugin"] = plugin_info(
                vray.Scene.PluginFromObject(str(obj.Id)))
        except Exception as exc:
            item["inspection_error"] = str(exc)
        report["objects"].append(item)
    return report


def run(doc, vray, dry_run=True):
    # Guard before accessing either host; never treat a transaction as rollback.
    if dry_run is not True:
        raise ApplyUnavailable("Apply disabled: verified 7.40.02 schema, binding and rollback required")
    return collect(doc, vray)


def main():
    import scriptcontext as sc
    import rh8VRay as vray
    print(json.dumps(run(sc.doc, vray), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
