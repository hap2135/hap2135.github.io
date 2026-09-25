#!/usr/bin/env python3
"""Repaint materials inside an existing GLB, in place.

The Altium OBJ export names its materials, but those names don't survive the
conversion to GLB - what's left is a list of materials addressed by index. So
this edits the GLB's JSON chunk directly rather than re-exporting: the mesh
data is untouched, which keeps a 10 MB board from growing or re-tessellating.

    python tools/recolor_glb.py assets/models/<slug>.glb --list
    python tools/recolor_glb.py assets/models/<slug>.glb 35=2e8a3a --metallic 35=0

`--list` prints every material with its colour, metalness and roughness, which
is how you work out which index is which: on both boards the copper is the one
with by far the most surface area, the laminate is second, and the two thin
sheets at the top and bottom of the stack are the board's outer faces.

Both boards wear soldermask green. Mask is translucent, so the copper-backed
areas come back a shade lighter than the bare laminate, and mask over copper
is glossier, which is the whole of what separates the copper material from the
other two - there are no mask openings in the export, so the pads go green
along with everything else.

    python tools/recolor_glb.py assets/models/wireless-battery-management-system.glb \
        35=78ff2f 1=247c1a 0=247c1a \
        --metallic 35=0 --metallic 1=0 --metallic 0=0 \
        --roughness 35=0.6 --roughness 1=0.85 --roughness 0=0.85

    python tools/recolor_glb.py assets/models/wireless-songbird-pir-sensor.glb \
        28=78ff2f 2=247c1a 1=247c1a \
        --metallic 28=0 --metallic 2=0 --metallic 1=0 \
        --roughness 28=0.6 --roughness 2=0.85 --roughness 1=0.85

Those hex codes are LINEAR, not sRGB. glTF's baseColorFactor is linear light
and this script writes the hex straight through, so a code here does not mean
what the same code means in CSS: the linear #247c1a above is the sRGB colour
#8ec46c, noticeably lighter than it reads. The practical consequence is that
halving the hex only drops the apparent brightness by about a quarter - to
halve what the eye sees, scale the channels by 0.5**2.2, roughly 0.22.

Don't work these out by hand. tools/mask-color.html repaints a board live from
an ordinary sRGB colour picker and prints the command with the converted
values, which is how the greens above were chosen.

The light rig in js/viewer.js is calibrated against these greens - raising it
washes them out towards white, so re-measure the flat-on face if you touch it.
"""
import argparse, json, pathlib, struct

ap = argparse.ArgumentParser()
ap.add_argument("glb", type=pathlib.Path)
ap.add_argument("recolor", nargs="*", metavar="INDEX=RRGGBB")
ap.add_argument("--metallic", action="append", default=[], metavar="INDEX=VALUE",
                help="set metallicFactor, e.g. 35=0 (repeatable)")
ap.add_argument("--roughness", action="append", default=[], metavar="INDEX=VALUE")
ap.add_argument("--list", action="store_true", help="print materials and exit")
args = ap.parse_args()

blob = args.glb.read_bytes()
magic, version, _ = struct.unpack("<4sII", blob[:12])
if magic != b"glTF":
    raise SystemExit(f"{args.glb} is not a binary glTF")
json_len, json_tag = struct.unpack("<I4s", blob[12:20])
if json_tag != b"JSON":
    raise SystemExit("first chunk is not JSON")
doc = json.loads(blob[20:20 + json_len])
rest = blob[20 + json_len:]
materials = doc.get("materials", [])

if args.list:
    for i, m in enumerate(materials):
        pbr = m.get("pbrMetallicRoughness", {})
        rgba = pbr.get("baseColorFactor", [1, 1, 1, 1])
        hexcode = "".join(f"{round(c * 255):02x}" for c in rgba[:3])
        # glTF defaults metallicFactor to 1.0 when it's absent, which is why an
        # untouched export can read as shiny metal even for laminate.
        print(f"{i:>3} #{hexcode}  metallic={pbr.get('metallicFactor', 1.0)}"
              f"  roughness={pbr.get('roughnessFactor', 1.0)}")
    raise SystemExit

def pbr_of(index):
    if not 0 <= index < len(materials):
        raise SystemExit(f"no material {index} (file has {len(materials)})")
    return materials[index].setdefault("pbrMetallicRoughness", {})

for rule in args.recolor:
    index, _, hexcode = rule.partition("=")
    pbr = pbr_of(int(index))
    rgba = [int(hexcode[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]
    pbr["baseColorFactor"] = rgba
    print(f"material {index} -> #{hexcode}")

for rules, key in ((args.metallic, "metallicFactor"), (args.roughness, "roughnessFactor")):
    for rule in rules:
        index, _, value = rule.partition("=")
        pbr_of(int(index))[key] = float(value)
        print(f"material {index} -> {key} {value}")

# Chunks are 4-byte aligned; the JSON one pads with spaces.
chunk = json.dumps(doc, separators=(",", ":")).encode()
chunk += b" " * (-len(chunk) % 4)
out = struct.pack("<4sII", magic, version, 12 + 8 + len(chunk) + len(rest))
out += struct.pack("<I4s", len(chunk), b"JSON") + chunk + rest
args.glb.write_bytes(out)
print(f"{args.glb} - {len(out) / 1e6:.1f} MB")
