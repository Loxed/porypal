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
> (not exactly but close to working, a ui overhaul will come from palette management later on so dont touch for now)

---

## Important (complex features)

**Groups → Group Extract**
> i have a hard time with this group extract feature. whats the point of it? we should maybe label it as a way to validate data (lets say we're making pokeball designs, and some element of a sprite is inconsistent accross different pokeballs, like the shadow or the highlight, we pintpoint the inconsistency?)

- [x] Drop multiple sprites -- grouping by silhouette works
- [ ] Drag sprite between groups triggers re-extract

> not quite. it works, but only if you drag the sprite above what seems to be the group header (some drop area that's not the entire group section container, which it should be).
> when grouping stuff, it needs to be persistent. redoing the extract sprites shouldnt reset the groups, it should just update the palettes within each group. currently it resets everything, which is really bad for workflow.

- [ ] Download zip contains correct palettes + manifest
> this works, but we should have a download group as zip button for each unique group if we want too. rather than every shape/group
> changing threshold doesnt auto extract again, it should (after the first time)

**Groups → Variants**
- [x] Drop 3 recolored sprites, set reference -- produces 3 index-aligned palettes
> works, but we want to overhaul the current ui. right now we click on a star to set reference (which seems like a favourite feature), which is confusing. we should have a clear button for setting reference.
- [x] Download zip works.
> propose a /palettes and /sprites folder within the zip, so its more organised. currently its just a flat zip with all the palettes, no resampled sprites, and no manifest.

**Shiny → Create Shiny Palette**
> UI is terribly designed right now, not using space. make it make sense. we have 1. normal sprite + normal palette + shiny palette which should produce normal and shiny sprites side by side, with download buttons for each (and a zip with both sprites in /sprites and both palettes in /palettes). 2. a bit better, we have normal sprite + shiny sprite which should produce both normal and shiny palettes. same as previous option, allow for dloading sprites and palettes separately or together as a zip. right now its just a mess of buttons and inputs that dont make sense.

- [x] Drop normal + shiny sprite -- produces 2 palettes
- [x] Palettes are index-aligned (same structure)

**Shiny → Create Shiny Sprite**
- [x] Drop sprite + normal.pal + shiny.pal -- renders shiny preview correctly
> works but doesnt show download options for sprites or a zip with both.

---

## Should work but verify

**Tileset**
- [x] Drop a spritesheet -- tiles appear
> cant see tiles' grid easily. make it thicker and have a contrasting color to the sprite, maybe inverted from the sprite's palette or something. same for the hover state, make it more visible.
- [x] Click tile, click slot -- tile placed correctly
- [x] Save preset -- appears in preset list
- [x] Load preset -- layout restored
- [x] Download PNG -- correct arrangement
> lets detect the bg color like we do everywhere else and apply it to empty slots in the downloaded png, so its ready for insertion right away. currently it just downloads the tiles with any spacing, but the empty slots are png transparent, whereas the bg around the tiles is another color which needs to be detected the same way we detect it in other features and applied to the empty slots in the downloaded png.

**Pipeline**
- [x] Load folder
> works on windows, gotta check on linux/mac
> right now we dont see what's a folder and how many files we're loading. maybe add a preview that shows the first sprite in the folder, and a count of how many sprites are being loaded?
- [x] Add Extract step -- configurable
> it works, but i'd love to see an example of it on the first sprite in the folder, so we can be sure the preset is being applied correctly before running the whole batch.
- [x] Add Tileset step -- preset picker shows saved presets
> same as above, preview!
- [x] Add Apply Palette step -- palette picker shows loaded palettes
> same as above. also rename the add step names to match the current things we have in the app.
- [x] Run on a folder -- progress shows, zip downloads

**Palettes tab**
- [x] Loaded palettes list shows up
- [x] Upload a `.pal` file -- appears in list
- [x] Delete a user palette -- gone from list and disk
- [ ] Browse library -- tree loads
- [ ] Import from library -- appears in user palettes
> this needs an overhaul. we need to be able to have a file explorer essentially.
> CRUD folder operations (Create, remove, rename, delete) in the user palettes.
> CRUD Palette operations (Create, remove, rename, delete) in the user palettes, with a preview of the palette colors when hovering or clicking on a palette in the list. same for the library palettes, we should be able to preview them before importing.
> as said before, we need to be able to edit and reorder palettes, rename, put them in folders n stuff.
> browse library is empty rn and i dont really like the way it is. i think i'll keep the structure like emerald/ and firered/ but we'll rename the palette library to porypal_library. essentially, it should have folders like pokemon/ that contain abomasnow/ with the different sprites and palettes it has.

> Heres what a pokemon file looks like:
```
(base) lox@lox-legion:~/projects/pokeemerald-expansion/graphics/pokemon/abomasnow$ tree
.
├── anim_front.png
├── anim_frontf.png
├── back.png
├── footprint.png
├── icon.png
├── mega
│   ├── back.png
│   ├── front.png
│   ├── icon.png
│   ├── normal.pal
│   ├── overworld.png
│   ├── overworld_normal.pal
│   ├── overworld_shiny.pal
│   └── shiny.pal
├── normal.pal
├── overworld.png
├── overworld_normal.pal
├── overworld_shiny.pal
├── overworldf.png
└── shiny.pal

2 directories, 19 files
```
> This is for pokeemerald-expansion. The base game (pokeemerald) doesn't have the exact same structure (no mega folder for example).

> we'll see how we plan this refactor, its not gonna be just a palette library. the palette folder tho, needs its previously mentioned CRUD features, and we need to make sure the palettes are being loaded and applied correctly in the different features across the app.

---

## Smoke test (just open and check no console errors)

- [x] All 7 tabs load without red errors in devtools
- [x] Logo click returns to Extract Palette tab
> We'll add a proper home/dashboard tab later, when everything is done. this dashboard will have a few showcases of different features and a easy to navigate menu with more explanations of what each feature does and when to use it. for now, the logo just returns us to the extract palette tab, since thats the most basic feature and a good starting point for new users.

---

## Fixes applied

| # | File | Change |
|---|------|--------|
| 1 | `server/api/pipeline.py` | `ImageManager({})` → `ImageManager()` in `_run_convert_step` |
| 2 | `server/app.py` | Added `shiny` to imports + `app.include_router(shiny.router)` |
| 3 | `server/api/convert.py` | `download_all_converted` now accepts + filters by `palette_names` |
| 4 | `frontend/src/tabs/ConvertTab.jsx` | `handleDownloadAll` sends `results.map(r => r.palette_name)` instead of `selectedPalettes` |
| 5 | `frontend/src/tabs/ConvertTab.jsx` | `useEffect` on `selectedPalettes` auto-reprocesses when selection changes |

---

## Backlog (not bugs, future work)

- [ ] Group drag-and-drop: accept drop on entire group section, not just header
- [ ] Groups: persist across re-extracts (update palettes only, don't reset structure)
- [ ] Groups: threshold slider triggers re-extract after first extract
- [ ] Groups: per-group download zip button
- [ ] Variants zip: organise into `/palettes` and `/sprites` with manifest
- [ ] Variants UI: replace star-as-reference with explicit "set as reference" button
- [ ] Shiny UI overhaul (both modes underuse space, missing download options)
- [ ] Shiny zip: `/sprites` and `/palettes` folders
- [ ] Tileset: thicker grid lines with contrasting color, better hover state
- [ ] Tileset download: detect + fill empty slots with bg color
- [ ] Pipeline: show first-sprite preview per step
- [ ] Pipeline: rename step labels to match app tab names
- [ ] Palettes tab: full CRUD (folders, rename, reorder, edit colors)
- [ ] Palettes tab: palette library overhaul → `porypal_library/`, pokeemerald structure
- [ ] Dashboard/home tab