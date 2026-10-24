# -*- coding: utf-8 -*-
"""Rhino 8 Windows / ScriptEditor Python 3
Place an A3/A4 grid of paper frames with live cursor preview.
No files or existing objects are changed until the placement click.
"""
import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rd
import Rhino.Input.Custom as ric
import Rhino.Input as ri
import scriptcontext as sc
import rhinoscriptsyntax as rs
from System.Drawing import Color

LAYER = 'SHEET_FRAME'
SIZES = {'A4': (210.0, 297.0), 'A3': (297.0, 420.0)}


def ask_choice(prompt, values, default):
    value = rs.GetString(prompt, default, values)
    return value


def rectangle_polyline(x, y, z, w, h):
    return rg.Polyline([
        rg.Point3d(x, y, z), rg.Point3d(x + w, y, z),
        rg.Point3d(x + w, y - h, z), rg.Point3d(x, y - h, z),
        rg.Point3d(x, y, z)
    ])


def grid_bounds(point, width, height, cols, rows, spacing):
    x, y, z = point.X, point.Y, point.Z
    for r in range(rows):
        for c in range(cols):
            yield r, c, rectangle_polyline(
                x + c * (width + spacing),
                y - r * (height + spacing),
                z, width, height
            )


def get_or_create_layer(doc):
    idx = doc.Layers.FindByFullPath(LAYER, -1)
    if idx >= 0:
        layer = doc.Layers[idx]
        if layer.IsLocked or not layer.IsVisible:
            raise RuntimeError('SHEET_FRAME layer is locked or hidden; unlock/show it first.')
        return idx
    layer = rd.Layer()
    layer.Name = LAYER
    layer.Color = Color.FromArgb(20, 154, 208)
    idx = doc.Layers.Add(layer)
    if idx < 0:
        raise RuntimeError('Could not create SHEET_FRAME layer')
    return idx


def main():
    doc = sc.doc
    if doc.ModelUnitSystem != Rhino.UnitSystem.Millimeters:
        print('Cancelled: document units must be millimeters (mm).')
        return
    view = doc.Views.ActiveView
    if view is None or isinstance(view, Rhino.Display.RhinoPageView):
        print('Activate a model-space Top view.')
        return
    vp = view.ActiveViewport
    direction = vp.CameraDirection
    if (not vp.IsParallelProjection or abs(direction.X) > 0.001 or
            abs(direction.Y) > 0.001 or direction.Z > -0.999):
        print('Activate the standard Top view (parallel projection).')
        return

    size = ask_choice('Paper size', ['A4', 'A3'], 'A3')
    if not size: return
    orientation = ask_choice('Orientation', ['Landscape', 'Portrait'], 'Landscape')
    if not orientation: return
    cols = rs.GetInteger('Number of sheets horizontally (columns)', 3, 1, 30)
    if cols is None: return
    rows = rs.GetInteger('Number of sheets vertically (rows)', 2, 1, 30)
    if rows is None: return
    scale = rs.GetReal('Drawing scale denominator (1 = 1:1, 100 = 1:100)', 1.0, 0.001, 10000.0)
    if scale is None: return
    gap_mm = rs.GetReal('Gap between papers, in paper mm', 15.0, 0.0, 1000.0)
    if gap_mm is None: return

    short, long = SIZES[size]
    paper_w, paper_h = (long, short) if orientation == 'Landscape' else (short, long)
    w = paper_w * scale
    h = paper_h * scale
    gap = gap_mm * scale
    grid_w = cols * w + (cols - 1) * gap
    grid_h = rows * h + (rows - 1) * gap
    print('{} {} | {} columns x {} rows | scale 1:{} | overall {:.1f} x {:.1f} model mm'.format(
        size, orientation, cols, rows, scale, grid_w, grid_h))
    print('Preview anchor is the TOP-LEFT corner. Move mouse and click to place; Esc cancels.')

    gp = ric.GetPoint()
    gp.SetCommandPrompt('Place TOP-LEFT corner of sheet grid (live preview; Esc cancels)')
    gp.ConstrainToConstructionPlane(False)
    def draw(sender, args):
        p = args.CurrentPoint
        p = rg.Point3d(p.X, p.Y, 0.0)
        for r, c, poly in grid_bounds(p, w, h, cols, rows, gap):
            args.Display.DrawPolyline(poly, Color.FromArgb(20, 170, 240), 2)
        args.Display.DrawLine(p, rg.Point3d(p.X + grid_w, p.Y - grid_h, 0),
                              Color.FromArgb(240, 160, 40), 1)
    gp.DynamicDraw += draw
    try:
        result = gp.Get()
    finally:
        gp.DynamicDraw -= draw
    if result != ri.GetResult.Point:
        print('Cancelled; no sheets added.')
        return
    p = gp.Point()
    anchor = rg.Point3d(p.X, p.Y, 0.0)
    layer_index = get_or_create_layer(doc)
    added = []
    try:
        for row, col, poly in grid_bounds(anchor, w, h, cols, rows, gap):
            attrs = rd.ObjectAttributes()
            attrs.LayerIndex = layer_index
            attrs.Name = '{}_{}_R{:02d}C{:02d}_1to{}'.format(size, orientation, row+1, col+1, scale)
            attrs.SetUserString('sheet.paper', size)
            attrs.SetUserString('sheet.orientation', orientation)
            attrs.SetUserString('sheet.scale', str(scale))
            attrs.SetUserString('sheet.row', str(row + 1))
            attrs.SetUserString('sheet.column', str(col + 1))
            attrs.SetUserString('sheet.paper_width_mm', str(paper_w))
            attrs.SetUserString('sheet.paper_height_mm', str(paper_h))
            object_id = doc.Objects.AddPolyline(poly, attrs)
            if object_id == System.Guid.Empty:
                raise RuntimeError('Failed to add a paper frame')
            added.append(object_id)
    except Exception:
        for object_id in added:
            doc.Objects.Delete(object_id, True)
        raise
    doc.Views.Redraw()
    print('Created {} sheets on layer {} ({} {}, 1:{}).'.format(len(added), LAYER, size, orientation, scale))


if __name__ == '__main__':
    import System
    main()
