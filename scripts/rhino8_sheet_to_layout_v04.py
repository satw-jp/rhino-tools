# -*- coding: utf-8 -*-
"""Rhino 8 Windows / ScriptEditor Python 3.
Convert SHEET_FRAME model-space rectangles to native Rhino Layout pages.
Original model geometry / SHEET_FRAME objects are never modified.
"""
import traceback
import Rhino
import Rhino.Geometry as rg
import Rhino.Display as display
import rhinoscriptsyntax as rs
import scriptcontext as sc

FRAME_LAYER = 'SHEET_FRAME'
PAGE_PREFIX = 'SHEET | '
MARKER = 'RHINO_SHEET_TOOL_V04:'
SIZES = {(420, 297): 'A3 landscape', (297, 420): 'A3 portrait',
         (297, 210): 'A4 landscape', (210, 297): 'A4 portrait'}


def frames(doc):
    found = []
    for obj in doc.Objects:
        layer = doc.Layers[obj.Attributes.LayerIndex]
        if layer.Name != FRAME_LAYER:
            continue
        curve = obj.Geometry
        if not isinstance(curve, rg.PolylineCurve) or not curve.IsClosed or curve.PointCount != 5:
            continue
        bb = curve.GetBoundingBox(True)
        if not bb.IsValid or abs(bb.Max.Z - bb.Min.Z) > 0.01:
            continue
        corners = {(round(curve.Point(i).X, 3), round(curve.Point(i).Y, 3)) for i in range(4)}
        expected = {(round(x, 3), round(y, 3)) for x in (bb.Min.X, bb.Max.X)
                    for y in (bb.Min.Y, bb.Max.Y)}
        if corners != expected:
            continue
        try:
            scale = float(obj.Attributes.GetUserString('sheet.scale') or '1')
        except (ValueError, TypeError):
            continue
        if not (0.001 <= scale <= 10000):
            continue
        width, height = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
        options = [(pw, ph, label) for (pw, ph), label in SIZES.items()
                   if abs(width - pw * scale) < max(0.5, scale * 0.5)
                   and abs(height - ph * scale) < max(0.5, scale * 0.5)]
        if len(options) != 1:
            continue
        pw, ph, label = options[0]
        found.append({'id': str(obj.Id), 'bb': bb, 'width': pw, 'height': ph,
                      'label': label, 'scale': scale})
    found.sort(key=lambda s: (-round(s['bb'].Max.Y / 10.0), s['bb'].Min.X))
    return found


def make_layout(doc, title, entry):
    page = doc.Views.AddPageView(title, float(entry['width']), float(entry['height']), False)
    if page is None:
        raise RuntimeError('Failed to add layout ' + title)
    # The marker prevents accidental removal of user-created layouts on reruns.
    page.Description = MARKER + entry['id']
    try:
        detail = page.AddDetailView('Model Top', rg.Point2d(0.0, 0.0),
                                    rg.Point2d(float(entry['width']), float(entry['height'])),
                                    display.DefinedViewportProjection.Top)
        if detail is None:
            raise RuntimeError('Failed to add Detail to ' + title)
        bb = entry['bb']
        cx = (bb.Min.X + bb.Max.X) / 2.0
        cy = (bb.Min.Y + bb.Max.Y) / 2.0
        target = rg.Point3d(cx, cy, 0.0)
        # Top projection points toward -Z; preserve correct X/Y orientation.
        camera = rg.Point3d(cx, cy, max(1000.0, float(entry['scale']) * 1000.0))
        detail.Viewport.SetCameraLocations(target, camera)
        ok = detail.DetailGeometry.SetScale(float(entry['scale']), doc.ModelUnitSystem,
                                            1.0, doc.PageUnitSystem)
        if not ok:
            raise RuntimeError('SetScale failed: ' + title)
        detail.DetailGeometry.IsProjectionLocked = True
        if not detail.CommitChanges():
            raise RuntimeError('Could not commit detail properties: ' + title)
        page.SetPageAsActive()
        return page
    except Exception:
        # No automatic removal of a partially-created page: preserve for inspection.
        raise


def main():
    doc = sc.doc
    if doc.ModelUnitSystem != Rhino.UnitSystem.Millimeters:
        print('STOP: model units must be millimeters.')
        return
    if doc.PageUnitSystem != Rhino.UnitSystem.Millimeters:
        answer = rs.GetString('Layout page units are not mm. Change to mm?', 'No', ['Yes', 'No'])
        if answer != 'Yes':
            return
        doc.PageUnitSystem = Rhino.UnitSystem.Millimeters
    sheets = frames(doc)
    if not sheets:
        print('No valid A3/A4 frames found on SHEET_FRAME.')
        return
    print('Found {} valid frames. Existing model objects will remain untouched.'.format(len(sheets)))
    prior = {p.PageName: p for p in doc.Views.GetPageViews()}
    # Stable IDs in title make remapping reliable even when frame positions change.
    tasks = []
    for n, frame in enumerate(sheets, 1):
        shortid = frame['id'].replace('-', '')[:8]
        title = '{}{} {}'.format(PAGE_PREFIX, shortid, frame['label'])
        existing = prior.get(title)
        tasks.append((title, frame, existing))
    replacements = [t for t in tasks if t[2] is not None and
                    str(t[2].Description or '') == MARKER + t[1]['id']]
    conflicts = [t for t in tasks if t[2] is not None and t not in replacements]
    if conflicts:
        print('STOP: conflicting layout names: {}'.format(', '.join(t[0] for t in conflicts)))
        return
    if replacements:
        print('{} previously generated layouts found.'.format(len(replacements)))
        action = rs.GetString('Existing generated layouts: skip or replace?', 'Skip', ['Skip', 'Replace', 'Cancel'])
        if not action or action == 'Cancel':
            return
        if action == 'Replace':
            approval = rs.GetString('Delete and rebuild {} generated layouts?'.format(len(replacements)),
                                    'No', ['Yes', 'No'])
            if approval != 'Yes':
                return
            # Delete only layouts bearing our marker. Never delete user-created layouts.
            for title, frame, page in replacements:
                if not rs.DeleteLayout(title):
                    print('STOP: failed to remove ' + title)
                    return
            tasks = [(title, frame, None) for title, frame, _ in tasks]
    created = 0
    for title, frame, existing in tasks:
        if existing is not None:
            print('Skipped existing: ' + title)
            continue
        try:
            make_layout(doc, title, frame)
            created += 1
            print('Created {} | {} x {} mm | 1:{}'.format(
                title, frame['width'], frame['height'], frame['scale']))
        except Exception as exc:
            print('ERROR {}: {}'.format(title, exc))
            traceback.print_exc()
            break
    doc.Views.Redraw()
    print('Finished. Created {} new native layouts; source frames remain.'.format(created))
    print('NOTE: layout Detail references model geometry, not a duplicated snapshot.')


if __name__ == '__main__':
    main()
