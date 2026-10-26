# -*- coding: utf-8 -*-
"""Rhino 8 / V-Ray 7: assign cloned, alpha-enabled V-Ray material to Pictures.

IMPORTANT: First create ONE working V-Ray Generic template in Asset Editor:
Diffuse Bitmap = transparent PNG; Opacity source = Diffuse Texture Alpha;
UV channel = original Picture's mapping (normally 1).
Test that template renders correctly in V-Ray before running.
This tool does NOT reverse-engineer undocumented Chaos settings.
"""
import os
import rhinoscriptsyntax as rs
import scriptcontext as sc

def normalized(path):
    return os.path.normcase(os.path.abspath(path)) if path else None

def texture_nodes(content):
    """Walk Rhino RenderContent tree, including nested V-Ray Bitmap nodes."""
    if content is None:
        return
    yield content
    child = content.FirstChild
    while child is not None:
        for node in texture_nodes(child):
            yield node
        child = child.NextSibling

def file_paths(content):
    result = []
    for node in texture_nodes(content):
        try:
            filename = str(node.Filename or "")
            if filename and os.path.splitext(filename)[1].lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
                result.append(filename)
        except Exception:
            pass
    return list(dict.fromkeys(result))

def picture_path(obj):
    # Rhino Picture normally has a conventional Rhino material with a bitmap.
    try:
        m = obj.RenderMaterial
        candidates = file_paths(m)
        if len(candidates) == 1:
            return candidates[0]
    except Exception:
        pass
    try:
        idx = obj.Attributes.MaterialIndex
        if idx >= 0:
            m = sc.doc.Materials[idx]
            for method in ("GetBitmapTexture",):
                tex = getattr(m, method)()
                if tex is not None and tex.FileName:
                    return str(tex.FileName)
    except Exception:
        pass
    return None

def replace_template_bitmaps(material, old, new):
    count = 0
    for node in texture_nodes(material):
        try:
            current = str(node.Filename or "")
            if normalized(current) == normalized(old):
                node.Filename = new
                if normalized(str(node.Filename or "")) != normalized(new):
                    raise RuntimeError("Bitmap path was not accepted by renderer")
                count += 1
        except RuntimeError:
            raise
        except Exception:
            pass
    if count == 0:
        raise RuntimeError("Template Bitmap is not editable via RhinoCommon")
    return count

def main():
    print("Picture -> V-Ray alpha material (template clone)")
    template_id = rs.GetObject(
        "Select a Picture with a VERIFIED transparent V-Ray Generic material",
        preselect=False)
    if not template_id:
        return
    template_object = sc.doc.Objects.FindId(template_id)
    template_material = template_object.RenderMaterial
    if template_material is None:
        print("ERROR: No render material on template.")
        return

    template_files = file_paths(template_material)
    if len(template_files) != 1:
        print("ERROR: Template needs exactly one source bitmap path. Found: {}".format(template_files))
        return
    source_template = template_files[0]

    targets = rs.GetObjects("Select Picture objects to convert", preselect=True)
    if not targets:
        return
    # Prepare every material BEFORE modifying any object.
    staged = []
    errors = []
    for oid in targets:
        obj = sc.doc.Objects.FindId(oid)
        if obj is None or oid == template_id:
            continue
        original_png = picture_path(obj)
        if not original_png or os.path.splitext(original_png)[1].lower() != ".png":
            errors.append("{}: cannot identify unique source PNG".format(oid))
            continue
        if not os.path.isfile(original_png):
            errors.append("{}: PNG not found: {}".format(oid, original_png))
            continue
        try:
            copy = template_material.MakeCopy()
            copy.Name = "VRAY_ALPHA_" + os.path.basename(original_png)
            replace_template_bitmaps(copy, source_template, original_png)
            staged.append((obj, copy, original_png))
        except Exception as ex:
            errors.append("{}: {}".format(oid, ex))

    print("Prepared {} / skipped {}".format(len(staged), len(errors)))
    for error in errors:
        print("SKIP " + error)
    if not staged:
        return
    answer = rs.MessageBox(
        "Apply {} new materials? Geometry and UV will NOT be changed.\n"
        "Save a backup first. Skipped: {}".format(len(staged), len(errors)),
        4 | 32, "V-Ray Picture alpha")
    if answer != 6:
        print("Cancelled. No changes made.")
        return

    success = 0
    for obj, material, path in staged:
        try:
            obj.RenderMaterial = material
            obj.CommitChanges()
            success += 1
            print("OK {} -> {}".format(obj.Id, path))
        except Exception as ex:
            print("FAILED {}: {}".format(obj.Id, ex))
    sc.doc.Views.Redraw()
    print("Completed: {} materials assigned. Test in V-Ray before production.".format(success))

if __name__ == "__main__":
    main()
