# Rhino 8 / Windows / Python 3
# Batch PDF from axis-aligned A3/A4 rectangles on SHEET_FRAME layer.
# Supports scale metadata created by rhino8_sheet_create.py.
# Model document units must be millimeters; use Top parallel viewport.

import os
import traceback
import Rhino
import Rhino.Geometry as rg
import Rhino.Display as rd
import Rhino.FileIO as rio
import rhinoscriptsyntax as rs
import scriptcontext as sc
from System.Drawing import Size

FRAME_LAYER = "SHEET_FRAME"
DPI = 300
SIZE_TOLERANCE_MM = 0.5
# A3 and A4, orientations inferred from rectangle dimensions
SHEET_DIMENSIONS = {
    (420, 297): "A3 landscape",
    (297, 420): "A3 portrait",
    (297, 210): "A4 landscape",
    (210, 297): "A4 portrait",
}


def find_sheets(doc):
    result = []
    for obj in doc.Objects:
        layer = doc.Layers[obj.Attributes.LayerIndex]
        if layer.Name != FRAME_LAYER:
            continue
        curve = obj.Geometry if isinstance(obj.Geometry, rg.Curve) else None
        if curve is None or not curve.IsClosed or not curve.IsPlanar():
            continue
        bb = curve.GetBoundingBox(True)
        if not bb.IsValid or abs(bb.Max.Z - bb.Min.Z) > 0.01:
            continue
        width, height = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
        scale_value = obj.Attributes.GetUserString('sheet.scale')
        try:
            scale = float(scale_value) if scale_value else 1.0
        except (ValueError, TypeError):
            continue
        if not (0.001 <= scale <= 10000):
            continue
        paper = next(((w, h, label) for (w, h), label in SHEET_DIMENSIONS.items()
                      if abs(width - w * scale) <= SIZE_TOLERANCE_MM * max(1.0, scale)
                      and abs(height - h * scale) <= SIZE_TOLERANCE_MM * max(1.0, scale)), None)
        if paper is None:
            continue
        # Rectangles must be actual rectangular curves, not arbitrary closed shapes
        if not isinstance(curve, rg.PolylineCurve) or curve.PointCount != 5:
            continue
        pts = [curve.Point(i) for i in range(5)]
        corners = {(round(p.X, 3), round(p.Y, 3)) for p in pts[:-1]}
        expected = {(round(x, 3), round(y, 3))
                    for x in (bb.Min.X, bb.Max.X)
                    for y in (bb.Min.Y, bb.Max.Y)}
        if corners != expected:
            continue
        result.append((bb, paper[0], paper[1], paper[2], obj.Id, scale))
    # Top row first; within each row left-to-right. Sort with stable 10 mm row bucket.
    # This assumes sheets arranged on a roughly regular grid.
    result.sort(key=lambda s: (-round(s[0].Max.Y / 10.0), s[0].Min.X))
    return result


def main():
    doc = sc.doc
    if doc.ModelUnitSystem != Rhino.UnitSystem.Millimeters:
        print("Stopped: please set model units to millimeters first.")
        return
    view = doc.Views.ActiveView
    if view is None or isinstance(view, rd.RhinoPageView):
        print("Stopped: activate a model-space Top viewport.")
        return
    vp = view.ActiveViewport
    # Ensure the world XY plane is seen from above. Do not silently switch user views.
    if not vp.IsParallelProjection:
        print("Stopped: activate Top in parallel projection (not perspective).")
        return
    camera_direction = vp.CameraDirection
    if abs(camera_direction.X) > 0.001 or abs(camera_direction.Y) > 0.001 or camera_direction.Z > -0.999:
        print("Stopped: activate the standard Top viewport (looking down -Z).")
        return
    sheets = find_sheets(doc)
    if not sheets:
        print("No A3/A4 rectangular closed polylines found on layer " + FRAME_LAYER)
        return
    filename = rs.SaveFileName("Save multi-page PDF", "PDF (*.pdf)|*.pdf||", None, "sheets.pdf")
    if not filename:
        return
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    pdf = rio.FilePdf.Create()
    count = 0
    captures = []
    try:
        for bb, width_mm, height_mm, label, obj_id, scale in sheets:
            px = Size(int(round(float(width_mm) / 25.4 * DPI)),
                      int(round(float(height_mm) / 25.4 * DPI)))
            settings = rd.ViewCaptureSettings(view, px, float(DPI))
            captures.append(settings)
            settings.RasterMode = False
            settings.DrawGrid = False
            settings.DrawAxis = False
            settings.DrawBackground = False
            settings.ViewArea = rd.ViewCaptureSettings.ViewAreaMapping.Window
            # World XY bounds map to full page; A3/A4 rectangle dimensions match physical media.
            settings.SetWindowRect(rg.Point3d(bb.Min.X, bb.Min.Y, bb.Min.Z),
                                   rg.Point3d(bb.Max.X, bb.Max.Y, bb.Min.Z))
            index = pdf.AddPage(settings)
            if index < 0:
                raise RuntimeError("PDF page creation failed for " + label)
            count += 1
            print("Page {}: {} ({} x {} paper mm), 1:{}".format(
                count, label, int(width_mm), int(height_mm), float(scale)))
        write_result = pdf.Write(filename)
        if not os.path.isfile(filename):
            raise RuntimeError("PDF file was not created")
        print("Saved {} pages: {}".format(count, filename))
    except Exception as exc:
        print("Export failed: " + str(exc))
        traceback.print_exc()
    finally:
        for capture in captures:
            capture.Dispose()


if __name__ == "__main__":
    main()
