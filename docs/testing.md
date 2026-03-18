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
- [ ] Download all as zip works

>  the download all as zip feature doesnt account for loaded/unloaded palettes. it downloaded the sprite with EVERY palette applied, instead of just the ones that were loaded.

> the selection of palettes is also jank, it doesnt auto-update everytime, we need to click on reprocess. This will be fixed at a later date, when the palettetab's enhanced features are added, but for now we should just make sure the thing auto-updates when we load/unload palettes.

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
> UI it terribly designed right now, not using space. make it make sense. we have 1. normal sprite + normal palette + shiny palette which should produce normal and shiny sprites side by side, with download buttons for each (and a zip with both sprites in /sprites and both palettes in /palettes). 2. a bit better, we have normal sprite + shiny sprite which should produce both normal and shiny palettes. same as previous option, allow for dloading sprites and palettes separately or together as a zip. right now its just a mess of buttons and inputs that dont make sense.
> 
- [] Drop normal + shiny sprite -- produces 2 palettes
> Option 2 (Create palette pair) doesnt work, it errors: {"detail":"Method Not Allowed"}
- [] Palettes are index-aligned (same structure)

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
> right now we dont see what's a folder and how many files we're loading. maybe adda preview that show the first sprite in the folder, and a count of how many sprites are being loaded?
- [x] Add Extract step -- configurable
> it works, but i'd love to see an example of it on the first sprite in the folder, so we can be sure the preset is being applied correctly before running the whole batch.
- [x] Add Tileset step -- preset picker shows saved presets
> same as above, preview!
- [x] Add Apply Palette step -- palette picker shows loaded palettes
> same as above also rename the add step names to match the current thigns we have in the app.
- [x] Run on a folder -- progress shows, zip downloads
> currently errors to: ERROR:root:Pipeline [fe2684b9-e4a7-45b7-b00d-2644416623da] error on OW Sprites Gen4/trchar052.png: ImageManager.__init__() takes 1 positional argument but 2 were given probably due to refactoring stuff we did before. somethign to do with config.yaml being removed.
> we
**Palettes tab**
- [x] Loaded palettes list shows up
- [x] Upload a `.pal` file -- appears in list
- [x] Delete a user palette -- gone from list and disk
- [ ] Browse library -- tree loads
- [ ] Import from library -- appears in user palettes
> this needs an overhaul. we need to be able to have a file explorer essentially.
> CRUD folder operations (Create, remove, rename, delete) in the user palettes.
> CRUD Palette operations (Create, remove, rename, delete) in the user palettes, with a preview of the palette colors when hovering or clicking on a palette in the list. same for the library palettes, we should be able to preview them before importing.
> as said before, we need to be able to edit and reorder palettes, rename, put them in folder n stuff.
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
(base) lox@lox-legion:~/projects/pokeemerald-expansion/graphics/pokemon/abomasnow$
```
>This is for pokeemerald-expansion. The base game (pokeemrald) doesn't have the exact same structure (no mega folder for example).

> we'll see how we plan this refactor, its not gonna be just a palette library. the palette folder tho, needs it's previously mentioned CRUD features, and we need to make sure the palettes are being loaded and applied correctly in the different features across the app.

---

## Smoke test (just open and check no console errors)

- [x] All 7 tabs load without red errors in devtools
- [x] Logo click returns to Extract Palette tab
> We'll add a proper home/dashboard tab later, when everything i s done. this dashboard will have a few showcases of different features and a easy to navigate menu with more explanations of what each feature does and when to use it. for now, the logo just returns us to the extract palette tab, since thats the most basic feature and a good starting point for new users.