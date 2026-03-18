Based on the codebase, here's what needs testing in order of "most likely to be broken by the cleanup":

---

## Critical (backend changes touched these)

**state.py / config removal**
- [x] App starts without errors (`python main.py`)
- [x] `PaletteManager` loads palettes from `palettes/defaults/` and `palettes/user/`

**Extract Palette**
- [x] Import a sprite, click extract -- gets a palette back
- [x] Transparent color is auto-detected correctly
- [x] Both Oklab and RGB previews render
- [x] Download `.pal` works
- [x] Save to library works (check `palettes/user/` on disk)

**Apply Palette**
- [x] Import a sprite -- all loaded palettes show up
- [x] Best match is highlighted
- [x] Download single result works
- [x] Download all as zip works -- respects current palette selection
- [x] Auto-reprocesses when palette selection changes
- [x] Pipette works to pick bg color from original image

---

## Important (complex features)

**Groups → Group Extract**
- [x] Drop multiple sprites -- grouping by silhouette works
- [x] Palette strip shows correct trimmed colors (no trailing bg dupes)
- [ ] Drag sprite between groups triggers re-extract
> only works when dragging over the group header, should be entire group section
- [ ] Groups persist across re-extracts (should only update palettes, not reset structure)
- [ ] Threshold slider triggers re-extract after first extract
- [ ] Per-group download zip button

**Groups → Variants**
- [x] Drop 3 recolored sprites, set reference -- produces 3 index-aligned palettes
- [x] Palette strip shows correct trimmed colors
- [x] Download zip works
> still flat zip -- needs `/palettes` and `/sprites` folders + manifest

**Shiny → Create Shiny Palette (mode 2)**
- [x] Drop normal + shiny sprite -- produces 2 palettes
- [x] Palettes are index-aligned
> UI overhaul needed -- both modes underuse space, missing download options for sprites

**Shiny → Create Shiny Sprite (mode 1)**
- [x] Drop sprite + normal.pal + shiny.pal -- renders shiny preview correctly
> missing download buttons for sprites and a zip with both

---

## Should work but verify

**Tileset**
- [x] Drop a spritesheet -- tiles appear
- [x] Click tile, click slot -- tile placed correctly
- [x] Save preset -- appears in preset list
- [x] Load preset -- layout restored
- [x] Download PNG -- correct arrangement
> empty slots should be filled with detected bg color, not left transparent

**Pipeline**
- [x] Load folder
- [x] Drop individual files or drag folder
- [x] Add Extract step -- configurable
- [x] Add Tileset step (now labelled "apply preset") -- preset picker shows saved presets
- [x] Add Apply Palette step (now labelled "apply palette") -- palette picker shows loaded palettes
- [x] Run on a folder -- progress shows, zip downloads
- [x] Preview strip appears after dropping a file + adding steps
- [x] Preview updates (debounced) when step config changes
- [x] Preview cards show correct image at each pipeline stage
- [x] Extract card shows palette swatch row beneath image
- [x] Error cards show the error message from the server
- [x] Downloaded zip has `sprites/`, `palettes/`, `manifest.json` structure
- [x] `manifest.json` includes step configs, per-file results, and summary

**Palettes tab**
- [x] Loaded palettes list shows up
- [x] Upload a `.pal` file -- appears in list
- [x] Delete a user palette -- gone from list and disk
- [ ] Browse library -- tree loads
- [ ] Import from library -- appears in user palettes
> full overhaul needed (see backlog)

---

## Re-verify after refactor

- [x] Extract tab: bg picker (auto/default/custom/pipette all work)
- [x] Extract tab: help modal opens and closes (Escape key too)
- [x] Apply palette tab: bg picker + pipette works, palette manager modal opens/closes
- [x] Items tab: bg picker for output transparent works
- [x] Items tab: grid/list toggle works
- [x] Variants: bg picker works, grid/list toggle works
- [x] Shiny: palette picker modal opens, selects, closes
- [x] Tileset: help modal opens, save preset modal opens + saves
- [x] Pipeline: batch step still works end to end (re-verified after preview + zip refactor)

---

## Smoke test

- [x] All 7 tabs load without red errors in devtools
- [x] Logo click returns to Extract Palette tab

---

## Fixes applied

| # | File | Change |
|---|------|--------|
| 1 | `server/api/pipeline.py` | `ImageManager({})` → `ImageManager()` in `_run_convert_step` |
| 2 | `server/app.py` | Added `shiny` to imports + `app.include_router(shiny.router)` |
| 3 | `server/api/convert.py` | `download_all_converted` filters by `palette_names` |
| 4 | `frontend/src/tabs/ConvertTab.jsx` | `handleDownloadAll` sends `results.map(r => r.palette_name)` |
| 5 | `frontend/src/tabs/ConvertTab.jsx` | `useEffect` on `selectedPalettes` auto-reprocesses |
| 6 | `frontend/src/components/BgColorPicker.jsx` + `.css` | New component — extracted from 4 tabs |
| 7 | `frontend/src/tabs/ExtractTab.jsx` + `.css` | Use `BgColorPicker` |
| 8 | `frontend/src/tabs/ConvertTab.jsx` | Use `BgColorPicker` + pipette |
| 9 | `frontend/src/tabs/ItemsTab.jsx` | Use `BgColorPicker` |
| 10 | `frontend/src/components/VariantsPanel.jsx` | Use `BgColorPicker`, fix missing icon imports |
| 11 | `frontend/src/components/Modal.jsx` + `.css` | New component — single modal shell, Escape key |
| 12 | `frontend/src/tabs/ExtractTab.jsx` + `.css` | Use `Modal` |
| 13 | `frontend/src/tabs/TilesetTab.jsx` | Use `Modal` for `HelpModal` and `SaveModal` |
| 14 | `frontend/src/tabs/ShinyTab.jsx` | Use `Modal` for `PalettePickerModal` |
| 15 | `frontend/src/tabs/ConvertTab.jsx` | Use `Modal` for `PaletteModal` |
| 16 | `frontend/src/components/ViewToggle.jsx` + `.css` | New component — extracted from 3 places |
| 17 | `frontend/src/tabs/ConvertTab.jsx` + `.css` | Use `ViewToggle` |
| 18 | `frontend/src/tabs/ItemsTab.jsx` + `.css` | Use `ViewToggle` |
| 19 | `frontend/src/components/VariantsPanel.jsx` | Use `ViewToggle` |
| 20 | `frontend/src/App.css` | `btn-primary-sm`, `.spinning`, `@keyframes spin`, `.pick-hint` as globals |
| 21 | `frontend/src/tabs/BatchTab.css` | Remove `btn-primary-sm`, `spinning` |
| 22 | `frontend/src/tabs/ConvertTab.css` | Remove `spinning`, `view-toggle`/`view-btn` |
| 23 | `frontend/src/tabs/ItemsTab.css` | Remove `spinning`, `view-toggle`/`view-btn` |
| 24 | `frontend/src/tabs/TilesetTab.css` | Remove `btn-primary-sm`, modal shell styles |
| 25 | `frontend/src/tabs/ExtractTab.css` | Remove `pick-hint` (now global) |
| 26 | `server/api/items.py` | `_trim_palette` helper — strips trailing bg dupes from `colors` array and `.pal` output |
| 27 | `frontend/src/tabs/BatchTab.jsx` | Drag+drop + individual file pick + folder pick; step labels renamed |
| 28 | `server/api/pipeline.py` | New `POST /api/pipeline/preview` endpoint — dry-run on first file, per-step base64 frames |
| 29 | `server/api/pipeline.py` | `_execute_job` now writes `sprites/` + `palettes/` zip structure + rich `manifest.json` |
| 30 | `frontend/src/tabs/BatchTab.jsx` | `PreviewStrip` + `PreviewCard` components; debounced preview fetch on config change |
| 31 | `frontend/src/tabs/BatchTab.css` | Preview strip styles — scrollable, step-colour accent bars, palette swatch row |
| 32 | `frontend/src/tabs/BatchTab.jsx` | Extract step's preview card shows palette swatches; error cards show server error message |
---

## Refactor queue

- [x] `BgColorPicker` component
- [x] `Modal` shell component
- [x] `ViewToggle` component
- [x] Consolidate shared CSS into `App.css`

---

## Backlog (future work, roughly prioritised)

### Groups
- [ ] Drag target should be entire group section, not just header
- [ ] Re-extract should preserve group structure, only update palettes
- [ ] Threshold slider triggers re-extract after first extract
- [ ] Per-group download zip button

### Variants
- [ ] Zip: organise into `/palettes` and `/sprites` with manifest
- [ ] UI: replace star-as-reference with explicit "set as reference" button

### Shiny
- [ ] Full UI overhaul — both modes need better layout and space usage
- [ ] Mode 1 (apply): download buttons for normal + shiny sprites, zip with `/sprites` + `/palettes`
- [ ] Mode 2 (extract): same download options

### Tileset
- [ ] Grid lines: thicker, contrasting color, better hover state
- [ ] Download: detect bg color + fill empty slots before export

### Pipeline
- [x] Show first-sprite preview per step so you can verify config before running
- [x] When downloading zip, include a manifest with details of each step and output files
- [x] In zip, have a `/palettes` and `/sprites` folder instead of everything flat

### Palettes tab
- [ ] Full CRUD: create/rename/delete folders, rename/reorder/edit palette colors
- [ ] Palette library overhaul → `porypal_library/` with pokeemerald folder structure
- [ ] Preview palette colors on hover before importing from library

### General
- [ ] Dashboard/home tab with feature overview