# EE Portfolio

Static electrical-engineering portfolio. No build step, no dependencies — plain
HTML, CSS, and ES modules. Three.js is pulled from a CDN only on pages that
show a 3D model.

## Run it locally

ES modules and `fetch` do not work over `file://`, so open it through a server:

```bash
python -m http.server 8000
# then visit http://localhost:8000
```

## Adding a project

1. Add an entry to `data/projects.json` (copy an existing one).
2. Create `projects/<slug>.html` by copying an existing detail page and
   changing only `data-slug` in the `<body>` tag — everything else is filled
   in from the JSON at runtime.
3. Drop images into `assets/img/<slug>/` and the model into
   `assets/models/<slug>.glb`.
4. Run `python check.py` to confirm nothing is mis-pathed, then push.

## CAD → web

The viewer takes `.glb` (preferred — small, keeps colors) or `.stl`.

**From Altium:** open the PCB, press `3` to check the 3D view, then
File ▸ Export ▸ STEP 3D. Components only appear if their footprints have
linked 3D models.

STEP carries the board outline and component bodies but **no copper**. For
traces and silkscreen, export File ▸ Export ▸ PDF3D and change the save
dialog's file type to **OBJ** — keep the `.mtl` written beside it.

Either input converts with the same tool, no FreeCAD or Blender required:

```bash
pip install cascadio trimesh
python tools/cad2glb.py board.step assets/models/<slug>.glb   # no copper
python tools/cad2glb.py board.obj  assets/models/<slug>.glb   # with copper
```

Altium exports the substrate as a black `core` material. `--recolor` fixes
that, and works on any material name the exporter writes:

```bash
python tools/cad2glb.py board.obj assets/models/<slug>.glb --recolor core=0a3d18
```

A 14 MB populated-board STEP converts to a 2.3 MB GLB in about 10 seconds,
keeping per-component materials. Pass `--linear`/`--angular` to trade detail
for file size; keep the result under ~10 MB.

Components only appear if their footprints have a 3D Body. In a .PcbLib use
Tools ▸ Manage 3D Bodies for Current Component; on a board, Tools ▸ Manage
3D Bodies for Components on Board finds the ones still missing.

## Deploy

Pushed to GitHub with Pages enabled on `main` / root. All paths are relative,
so the site works both at `you.github.io` and `you.github.io/<repo>`.
