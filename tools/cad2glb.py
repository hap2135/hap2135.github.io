#!/usr/bin/env python3
"""Convert an Altium 3D export into a web-ready GLB for the project viewer.

Two input formats, two different things you get:

  .step  File > Export > STEP 3D. Board outline + component bodies, no
         copper. Small files, clean geometry.
  .obj   File > Export > PDF3D, then switch the save dialog's file type to
         OBJ. Tessellated, and it DOES carry copper traces and silkscreen.
         Keep the .mtl file next to the .obj or everything comes out grey.

    pip install cascadio trimesh
    python tools/cad2glb.py board.step assets/models/<slug>.glb
    python tools/cad2glb.py board.obj  assets/models/<slug>.glb
"""
import argparse, pathlib, re, time

ap = argparse.ArgumentParser()
ap.add_argument("src", type=pathlib.Path)
ap.add_argument("dst", type=pathlib.Path)
ap.add_argument("--linear", type=float, default=0.1, help="STEP only: linear deflection")
ap.add_argument("--angular", type=float, default=0.5, help="STEP only: angular deflection")
ap.add_argument("--recolor", action="append", default=[], metavar="NAME=RRGGBB",
                help="override a material colour, e.g. core=0e5c24 (repeatable)")
args = ap.parse_args()

suffix = args.src.suffix.lower()
args.dst.parent.mkdir(parents=True, exist_ok=True)
start = time.time()

if suffix in (".step", ".stp"):
    import cascadio
    cascadio.step_to_glb(str(args.src), str(args.dst),
                         tol_linear=args.linear, tol_angular=args.angular)
elif suffix in (".obj", ".stl", ".ply", ".glb", ".gltf"):
    import io, trimesh
    from trimesh.resolvers import FilePathResolver
    # An .mtl sitting next to the .obj is picked up automatically; without it
    # every surface lands on the same default material.
    if suffix == ".obj" and not any(args.src.parent.glob("*.mtl")):
        print("note: no .mtl beside the .obj — the result will be untextured")
    if suffix == ".obj":
        text = args.src.read_text(encoding="utf-8", errors="ignore")
        # Altium names an object after its designator, so a part called `C\E\`
        # ends its `o` line with a backslash. trimesh treats backslash-newline
        # as a line continuation and swallows the `v` line that follows, which
        # shifts every vertex index after it and blows up mid-load.
        cleaned, hits = re.subn(r"(?m)^([og] .*?)\\+$", r"\1", text)
        if hits:
            print(f"cleaned {hits} trailing backslash(es) off object/group names")
        scene = trimesh.load(io.StringIO(cleaned), file_type="obj",
                             resolver=FilePathResolver(str(args.src)))
    else:
        scene = trimesh.load(str(args.src))
    for rule in args.recolor:
        name, _, hexcode = rule.partition("=")
        rgb = [int(hexcode[i:i + 2], 16) for i in (0, 2, 4)]
        mesh = scene.geometry.get(name)
        if mesh is None:
            print(f"note: no material named {name!r} in this file")
            continue
        # OBJ materials arrive as SimpleMaterial (colour in .diffuse); GLB/STEP
        # ones are PBR (.baseColorFactor). Set whichever the material has, or
        # the change is silently dropped on export.
        material, rgba = mesh.visual.material, rgb + [255]
        applied = False
        for attr in ("diffuse", "baseColorFactor"):
            if hasattr(material, attr):
                setattr(material, attr, rgba)
                applied = True
        if not applied:
            raise SystemExit(f"cannot recolour {name}: unsupported material type")
        print(f"recoloured {name} -> #{hexcode}")
    scene.export(str(args.dst))
else:
    raise SystemExit(f"unsupported input: {suffix}")

mb = args.dst.stat().st_size / 1e6
print(f"{args.dst} - {mb:.1f} MB in {time.time() - start:.0f}s")
if mb > 10:
    print("warning: over 10 MB — for STEP raise --linear/--angular; for OBJ,")
    print("re-export with fewer component models or decimate in Blender")
