## Critical (backend changes touched these)

**state.py / config removal**
- [x] App starts without errors (`python main.py`)
- [x] `PaletteManager` loads palettes from `palettes/defaults/` and `palettes/user/`

**Extract Palette**
- [x] Import a sprite, click extract -- gets a palette back
- [x] Transparent color is auto-detected correctly
- [x] Both Oklab and RGB previews render
- [x] Export dropdown opens on both oklab and rgb results
- [x] Download `.pal` works (from export dropdown)
- [x] Rename input in dropdown changes the saved filename
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
- [x] Drag sprite between groups triggers re-extract
- [x] Re-extract button preserves current group structure, only updates palettes
- [x] Threshold slider triggers re-extract after first extract
- [x] Per-group download zip button
- [x] Search/filter bar with wildcard support

**Groups → Variants (extract mode)**
- [x] Drop 3 recolored sprites, set reference -- produces 3 index-aligned palettes
- [x] Palette strip shows correct trimmed colors
- [x] Download zip works
- [x] Zip organised into `/palettes` and `/sprites` with manifest
- [x] Export dropdown on each result card (download .pal + save to library)

**Groups → Variants (apply mode)**
- [x] Drop a base sprite, pick N palettes, set ref -- renders N recolored sprites
- [x] Download all as zip works

**Shiny → Create Palette Pair (mode 2)**
- [x] Drop normal + shiny sprite -- produces 2 palettes
- [x] Palettes are index-aligned
- [x] Download zip works -- includes `/palettes` and `/sprites` with manifest
- [x] Export dropdown on normal palette result
- [x] Export dropdown on shiny palette result (saved with `_shiny` suffix)

**Shiny → Create Shiny Sprite (mode 1)**
- [x] Drop sprite, pick normal + shiny palette from loaded palettes or import .pal directly
- [x] Renders shiny preview correctly
- [x] Download zip works -- includes `/sprites` and `/palettes` with manifest

---

## Should work but verify

**Tileset**
- [x] Drop a spritesheet -- tiles appear
- [x] Click tile, click slot -- tile placed correctly
- [x] Save preset -- appears in preset list
- [x] Load preset -- layout restored
- [x] Download PNG -- correct arrangement, transparency preserved

**Pipeline**
- [x] Load folder
- [x] Drop individual files or drag folder
- [x] Add Extract step -- configurable
- [x] Add Tileset step -- preset picker shows saved presets
- [x] Add Apply Palette step -- palette picker shows loaded palettes
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
- [x] Browse library -- tree loads
- [x] Import from library -- appears in user palettes

---

## Re-verify after refactor

- [x] Extract tab: bg picker (auto/default/custom/pipette all work)
- [x] Extract tab: help modal opens and closes (Escape key too)
- [x] Extract tab: export dropdown (download + save to library)
- [x] Apply palette tab: bg picker + pipette works, palette manager modal opens/closes
- [x] Items tab: bg picker for output transparent works
- [x] Items tab: grid/list toggle works
- [x] Variants: bg picker works, grid/list toggle works
- [x] Variants: export dropdown on result cards works
- [x] Shiny: palette picker modal opens, selects, closes, import .pal works
- [x] Shiny: export dropdown on extract matched results
- [x] Tileset: help modal opens, save preset modal opens + saves
- [x] Pipeline: batch step still works end to end

---

## Library drawer (new in v3.1)

**Project loading**
- [ ] Paste a path (Linux, Windows `C:\`, WSL `/mnt/c/`) -- scan works
- [ ] Auto-descends into `/graphics` if project root is given
- [ ] Recent paths saved in localStorage -- clicking one auto-scans
- [ ] Remove a recent path -- disappears from list
- [ ] Folder search bar filters the folder list in the scan step
- [ ] Smart folders (`pokemon/`, `items/`, `trainers/`) pre-selected
- [ ] Other folders shown separately, none pre-selected
- [ ] Load project -- persists after closing and reopening the drawer
- [ ] Remove a loaded project -- disappears from drawer

**Drawer: palette_library/ section**
- [ ] Shows `porypal/palette_library/` label and path
- [ ] Sub-folders expand on click, start closed
- [ ] Sprites and palettes matched by stem name shown as pairs
- [ ] Unmatched sprites shown separately (dimmed)
- [ ] Unmatched palettes shown separately
- [ ] Search filters open folders, does not hide closed folders

**Drawer: loaded project sections**
- [ ] Each project shown as its own labelled section with root path
- [ ] Trash icon removes the project
- [ ] `pokemon/` folder opens as paginated PokemonCards
- [ ] `items/` folder opens as paginated LibraryItemCards
- [ ] `trainers/` folder opens as TrainerCard view
- [ ] Other folders open as GenericFolderCard (sprite+palette pairs)
- [ ] Search filters within open folders

**PokemonCard**
- [ ] Card expands on click -- loads front/back/icon sprites
- [ ] Normal and shiny previews rendered correctly
- [ ] Download .pal works for each palette row
- [ ] Import to Porypal works -- palette appears in palettes/user/

**ItemsCard (library)**
- [ ] Item sprite shown next to palette strip
- [ ] Generate palette button (wand) appears when no palette exists
- [ ] Generate creates a .pal on disk and updates the row in place
- [ ] Download .pal works
- [ ] Import to Porypal works

**TrainerCard**
- [ ] Front pic shown for each trainer
- [ ] Back pic shown in reserved slot (dashed placeholder if missing)
- [ ] Palette strip shown when palette exists
- [ ] "no palette" label shown when palette missing
- [ ] Generate palette button (wand) appears when no palette exists
- [ ] Generate creates palette and updates row in place
- [ ] Download .pal works
- [ ] Import to Porypal works
- [ ] Unmatched palettes shown below divider
- [ ] Search filters trainer rows

---

## Smoke test

- [x] All 7 tabs load without red errors in devtools
- [x] Logo click returns to Extract Palette tab

---

## Refactor queue

- [x] `BgColorPicker` component
- [x] `Modal` shell component
- [x] `ViewToggle` component
- [x] `ExportDropdown` component (extract + download .pal + save to library)
- [x] Consolidate shared CSS into `App.css`

---

## Backlog (future work, roughly prioritised)

### Groups
- [x] Drag target should be entire group section, not just header
- [x] Re-extract should preserve group structure, only update palettes
- [x] Threshold slider triggers re-extract after first extract
- [x] Per-group download zip button
- [x] Search/filter feature with wildcard support

### Variants
- [x] Zip: organise into `/palettes` and `/sprites` with manifest
- [x] UI: set-ref button + ref badge replacing star
- [x] Export dropdown on each result card

### Shiny
- [x] Mode 1 (apply): pick from loaded palettes or import .pal directly; download zip with `/sprites` + `/palettes` + manifest
- [x] Mode 2 (extract): download zip with `/sprites` + `/palettes` + manifest
- [x] Mode 2: export dropdown on each extracted palette

### Tileset
- [x] Grid lines: thicker, contrasting color, better hover state
- [x] Download: transparency preserved -- no bg color forced on export

### Pipeline
- [x] Show first-sprite preview per step so you can verify config before running
- [x] When downloading zip, include a manifest with details of each step and output files
- [x] In zip, have a `/palettes` and `/sprites` folder instead of everything flat

### Palettes tab
- [x] Full CRUD: create/rename/delete folders, rename/reorder/edit palette colors
- [x] Palette library overhaul → `palette_library/` with any folder structure
- [x] Smart views for `pokemon/`, `items/`, `trainers/` in library drawer
- [x] Load decomp project by path -- browse graphics folder directly
- [x] Generate missing palettes from sprites in-place (items + trainers)

### General
- [ ] Dashboard/home tab with feature overview