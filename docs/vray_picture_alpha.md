# V-Ray Picture PNG alpha (Rhino 8)

**Target:** Rhino 8 on Windows, Chaos V-Ray 7.40.02. **Status: experimental / Rhino + V-Ray live validation pending.**

## What it does
Clones a **manually verified** V-Ray Generic material for each selected Rhino Picture; replaces the template Bitmap image with that object's original PNG; assigns the clone without editing geometry, UVs, object transforms, or mapping channels. Each Picture gets its own material. It does not call `vrayMtlFromRhino`, edit undocumented V-Ray parameters, or create a valid alpha shader from scratch.

## Setup
1. Back up the 3DM file.
2. In V-Ray Asset Editor create **Generic**; assign a transparent PNG to Diffuse Bitmap; set Opacity to **Diffuse Texture Alpha** (or equivalent UI control). Set Bitmap placement to use the Picture's existing UV channel, normally channel 1.
3. Apply this Generic to one test Picture and **verify actual V-Ray rendering** shows transparent areas correctly. This becomes your **template object**. Do not use a template with other image file nodes / multiple image paths.
4. Open `scripts/vray_picture_alpha.py` in Rhino 8 ScriptEditor (Python 3), run. Select template Picture, then select target Picture objects.
5. Read the prepared/skipped diagnostics; approve only after checking. Render sample target objects in V-Ray.

## Limits / stop conditions
- Script only changes render material assignment; original materials remain in document, and UV data is left untouched.
- Target must have a discoverable unique source PNG in its Rhino RenderMaterial tree or conventional material bitmap. Images stored as embedded-only textures, named differently by plugin, or resolved via a layer material may be skipped.
- The V-Ray template bitmap must expose writable `RenderContent.Filename`; otherwise targets fail closed.
- Shared template Bitmap's UV offsets/repeat settings are duplicated. If targets have different texture placement overrides inside materials (not in object UV), output may differ.
- Alpha behavior is **inherited from the verified template**, not programmatically inferred or asserted.
- Existing V-Ray materials on targets will be overwritten after confirmation; use duplicated objects or document backups.
- No live Rhino/V-Ray runtime is available to test this code here. Python syntax review is not a V-Ray rendering test.

## Validation checklist
- [ ] PNG's transparent pixels show the objects behind them in V-Ray
- [ ] Cropping, orientation and aspect ratio match pre-conversion Rhino Picture
- [ ] Different PNGs stay independent
- [ ] No UV/mapping/geometry is changed
- [ ] Reopen the saved 3DM and re-render
