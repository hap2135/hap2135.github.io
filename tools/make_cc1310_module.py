#!/usr/bin/env python3
"""Build a STEP model of the CC1310-TC-005 wireless module.

EasyEDA will not export a component's STEP on its own, so this reproduces the
module from its published bounding box (16.08 x 21.15 x 1.62 mm) and photos of
the part: blue PCB with castellated edges, the CC1310 QFN, two crystals, the
U.FL antenna connector and the surrounding passives.

Component placement is eyeballed from a photo of the module with its shield
can removed and is meant to look right, not to be a manufacturing reference.
The castellation pitch IS exact: adjacent pads are separated by 0.27 mm.

Origin is at the centre of the footprint with z=0 on the underside, which is
what Altium's Place > 3D Body expects, so it drops straight onto the pads.

    pip install cadquery
    python tools/make_cc1310_module.py out.step [--shield]
"""
import sys
import cadquery as cq

X, Y, Z = 16.08, 21.15, 1.62
PCB_T = 0.80
HEADROOM = Z - PCB_T                  # everything must fit under 1.62 mm

PAD_R = 0.40                          # castellation radius
PAD_GAP = 0.27                        # substrate between adjacent pads
PAD_PITCH = 2 * PAD_R + PAD_GAP

BLUE   = cq.Color(0.09, 0.22, 0.42)
GOLD   = cq.Color(0.85, 0.70, 0.28)
BLACK  = cq.Color(0.13, 0.13, 0.14)
METAL  = cq.Color(0.72, 0.73, 0.75)
MLCC   = cq.Color(0.78, 0.72, 0.60)
CERAM  = cq.Color(0.76, 0.66, 0.40)
PLASTIC = cq.Color(0.82, 0.80, 0.76)

# ---------------------------------------------------------------- PCB body --
pcb = cq.Workplane("XY").box(X, Y, PCB_T, centered=(True, True, False))

def run(n, centre=0.0):
    """n pad centres on PAD_PITCH, centred about `centre`."""
    span = (n - 1) * PAD_PITCH
    return [centre - span / 2 + i * PAD_PITCH for i in range(n)]

left_ys = run(12, -1.0)
right_ys = run(12, -1.0)
bottom_xs = run(6, 0.0)

notches = [(-X / 2, y) for y in left_ys]
notches += [(X / 2, y) for y in right_ys]
notches += [(x, -Y / 2) for x in bottom_xs]

for nx, ny in notches:
    pcb = pcb.cut(
        cq.Workplane("XY").moveTo(nx, ny).circle(PAD_R).extrude(PCB_T)
    )

# Gold plating on the top face beside each notch, as in the photo.
plating = None
for nx, ny in notches:
    vertical = abs(abs(nx) - X / 2) < 1e-6
    w, h = (1.1, 2 * PAD_R) if vertical else (2 * PAD_R, 1.1)
    # Offset by exactly half the pad so its outer edge lands on the board
    # edge rather than overhanging it.
    px = nx - (w / 2) * (1 if nx > 0 else -1) if vertical else nx
    py = ny if vertical else ny + h / 2
    pad = (
        cq.Workplane("XY", origin=(0, 0, PCB_T - 0.04))
        .moveTo(px, py).rect(w, h).extrude(0.05)
    )
    plating = pad if plating is None else plating.union(pad)

# ------------------------------------------------------------- components --
# Pixel coordinates read off the reference photo, and the calibration that
# maps them into millimetres on the footprint.
PX_CENTRE = (412, 622)
MM_PER_PX = (0.02532, 0.02005)

def at_px(px, py):
    return ((px - PX_CENTRE[0]) * MM_PER_PX[0],
            (PX_CENTRE[1] - py) * MM_PER_PX[1])

def chip(px, py, w, d, t, colour):
    x, y = at_px(px, py)
    solid = (
        cq.Workplane("XY", origin=(0, 0, PCB_T))
        .moveTo(x, y).rect(w, d).extrude(min(t, HEADROOM))
    )
    return solid, colour

parts = []

# CC1310 QFN, the crystals and the two large parts on the left.
parts.append(("cc1310", *chip(432, 750, 5.0, 5.0, 0.55, BLACK)))
parts.append(("xtal_24mhz", *chip(640, 600, 2.5, 3.2, 0.60, CERAM)))
parts.append(("xtal_small", *chip(345, 545, 2.2, 1.3, 0.50, METAL)))
parts.append(("cap_bulk", *chip(232, 855, 1.9, 2.6, 0.70, BLACK)))
parts.append(("ind_large", *chip(300, 1000, 3.2, 1.0, 0.60, METAL)))

PASSIVES = [
    (352, 212, 1.6, 0.9, METAL), (400, 228, 1.0, 0.6, METAL),
    (468, 243, 1.2, 0.7, BLACK), (556, 272, 1.2, 0.7, BLACK),
    (590, 212, 0.9, 0.5, METAL), (366, 318, 1.6, 0.9, METAL),
    (430, 400, 1.0, 0.6, BLACK), (470, 398, 1.0, 0.6, BLACK),
    (516, 400, 1.0, 0.6, BLACK), (575, 388, 1.2, 0.7, METAL),
    (610, 478, 1.2, 0.7, METAL), (505, 482, 1.0, 0.6, BLACK),
    (462, 470, 1.0, 0.6, BLACK),
    (216, 372, 0.9, 0.7, METAL), (252, 372, 0.9, 0.7, METAL),
    (216, 420, 0.9, 0.7, METAL), (252, 420, 0.9, 0.7, METAL),
    (216, 468, 0.9, 0.7, METAL), (252, 468, 0.9, 0.7, METAL),
    (216, 556, 0.9, 0.7, METAL), (252, 556, 0.9, 0.7, METAL),
    (214, 600, 0.9, 0.7, METAL), (232, 700, 1.2, 0.8, MLCC),
    (243, 745, 1.6, 1.0, MLCC),
    (622, 700, 1.2, 0.7, BLACK), (622, 762, 1.2, 0.7, BLACK),
    (622, 822, 1.2, 0.7, BLACK), (640, 940, 1.2, 0.7, BLACK),
    (432, 990, 1.0, 1.2, METAL), (474, 990, 1.0, 1.2, METAL),
    (516, 990, 1.0, 1.2, METAL), (592, 985, 1.2, 0.7, BLACK),
    (628, 950, 1.0, 0.6, BLACK),
]
for i, (px, py, w, d, colour) in enumerate(PASSIVES):
    parts.append((f"passive_{i:02d}", *chip(px, py, w, d, 0.35, colour)))

# ------------------------------------------------------- U.FL / IPEX jack --
ufl_x, ufl_y = at_px(240, 210)
UFL_W = 2.4
BASE_T, SHELL_T = 0.22, HEADROOM - 0.22
SHELL_OD, SHELL_ID = 1.05, 0.82

def at(z):
    return cq.Workplane("XY", origin=(0, 0, PCB_T + z)).moveTo(ufl_x, ufl_y)

ufl_base = at(0).rect(UFL_W, UFL_W).extrude(BASE_T)
tabs = None
for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    tab = (
        cq.Workplane("XY", origin=(0, 0, PCB_T))
        .moveTo(ufl_x + dx * (UFL_W / 2 + 0.2), ufl_y + dy * (UFL_W / 2 - 0.25))
        .rect(0.6, 0.5).extrude(0.10)
    )
    tabs = tab if tabs is None else tabs.union(tab)
shell = at(BASE_T).circle(SHELL_OD).circle(SHELL_ID).extrude(SHELL_T)
pin = at(BASE_T).circle(0.20).extrude(SHELL_T - 0.14)

# ------------------------------------------------------------------ build --
assembly = cq.Assembly(name="CC1310-TC-005")
assembly.add(pcb, name="pcb", color=BLUE)
assembly.add(plating, name="pads", color=GOLD)
for name, solid, colour in parts:
    assembly.add(solid, name=name, color=colour)
assembly.add(ufl_base, name="ufl_base", color=PLASTIC)
assembly.add(tabs, name="ufl_tabs", color=GOLD)
assembly.add(shell, name="ufl_shell", color=GOLD)
assembly.add(pin, name="ufl_pin", color=GOLD)

if "--shield" in sys.argv:
    L, R, B, T = 1.6, 1.3, 1.3, 0.6
    can_w, can_h = X - L - R, Y - T - B
    can = (
        cq.Workplane("XY", origin=(0, 0, PCB_T))
        .moveTo(-X / 2 + L + can_w / 2, -Y / 2 + B + can_h / 2)
        .rect(can_w, can_h).extrude(HEADROOM)
    )
    can = can.cut(
        cq.Workplane("XY", origin=(0, 0, PCB_T))
        .moveTo(-X / 2 + L + 3.0, Y / 2 - T - 2.5)
        .rect(6.0, 5.0).extrude(HEADROOM)
    )
    assembly.add(can, name="shield", color=cq.Color(0.93, 0.93, 0.93))

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = args[0] if args else "CC1310-TC-005.step"
assembly.export(out)

bb = assembly.toCompound().BoundingBox()
print(f"wrote {out}")
print(f"bounding box : {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
print(f"castellations: {len(notches)}  pitch {PAD_PITCH:.2f} mm  gap {PAD_GAP} mm")
print(f"components   : {len(parts)}")
