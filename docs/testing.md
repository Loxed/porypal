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
- [x] Threshold slider triggers re-extract after first extract
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
- [x] Download PNG -- correct arrangement, transparency preserved (no bg fill) — tileset arranger outputs raw transparency, palette handling is upstream's responsibility

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
- [x] Threshold slider triggers re-extract after first extract
- [ ] Per-group download zip button

### Variants
- [x] Zip: organise into `/palettes` and `/sprites` with manifest
- [ ] UI: replace star-as-reference with explicit "set as reference" button

### Shiny
- [ ] Full UI overhaul — both modes need better layout and space usage
- [ ] Mode 1 (apply): download buttons for normal + shiny sprites, zip with `/sprites` + `/palettes`
- [ ] Mode 2 (extract): same download options

### Tileset
- [x] Grid lines: thicker, contrasting color, better hover state
- [x] Download: transparency preserved — no bg color forced on export

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