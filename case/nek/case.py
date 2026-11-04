"""Type B case geometry: two keyboard halves and a wrist rest (one or two pieces).

Construction, in Type A's world frame:
  1. The footprint is each side's outline (key area + walls + wrist rest, out to that side's pivot line)
     plus the quadrilateral between the pivot lines, extruded vertically, so outer walls are vertical
     (3-axis machinable, prints without overhangs).
  2. The top is the lowest of Type A's three top planes (left, centre, right), which is exactly how
     Type A's top surface works out.
  3. The body is cut into pieces by vertical planes: the left/right joint and each side's front cut
     between the half and the wrist rest.
  4. Each half gets keycap openings through the top skin, a plate/PCB cavity open to the bottom, and
     a recess for the acrylic bottom panel. The wrist rest gets neoprene pockets.
  5. Everything is shifted so the desk is z = 0.
"""

from dataclasses import dataclass
from functools import reduce

import numpy as np
from build123d import (
    Axis,
    Box,
    Face,
    Keep,
    Kind,
    Location,
    Part,
    Plane,
    Pos,
    Rectangle,
    Sketch,
    Vector,
    Wire,
    extrude,
    fillet,
    offset,
    split,
)

from .frames import TYPE_A, TYPE_A_CENTER_NORMAL, TYPE_A_CENTER_POINT, TYPE_A_PIVOT_INSET, Frame
from .layout import Key, extent_mm, load
from .params import Params

BIG = 1000.0
SIDES = ("left", "right")


@dataclass
class Side:
    name: str
    frame: Frame
    keys: list[Key]
    width: float
    depth: float

    @property
    def outer_is_left(self) -> bool:
        return self.name == "left"


def sides() -> dict[str, Side]:
    out = {}
    for name in SIDES:
        keys = load(name)
        w, d = extent_mm(keys)
        out[name] = Side(name, TYPE_A[name], keys, w, d)
    return out


# ---------------------------------------------------------------------------------------------
# 2D helpers. Sketches are drawn in a side's plane coordinates: u = KLE x, v = -KLE y.


def plane(side: Side, z: float) -> Plane:
    """The plane parallel to the plate, z mm above the plate's top face."""
    f = side.frame
    return Plane(origin=Vector(*f.point(0, 0, z)), x_dir=Vector(*f.ex), z_dir=Vector(*f.up))


def kle_rect(x0: float, y0: float, x1: float, y1: float) -> Sketch:
    return Pos((x0 + x1) / 2, -(y0 + y1) / 2) * Rectangle(x1 - x0, y1 - y0)


def rounded(sk: Sketch, r: float, where) -> Sketch:
    """Fillet the sketch vertices selected by where(Vector) -> bool."""
    verts = [v for v in sk.vertices() if where(Vector(v))]
    return fillet(verts, r) if verts else sk


def close_corners(sk: Sketch, grow: float, r: float) -> Sketch:
    """Grow by `grow`, rounding convex corners and giving concave corners at least radius r."""
    return offset(offset(sk, grow + r, kind=Kind.ARC), -r, kind=Kind.ARC)


def keycap_opening(side: Side, p: Params) -> Sketch:
    cells = reduce(lambda a, b: a + b, [kle_rect(*k.cell_mm) for k in side.keys])
    return close_corners(cells, p.keycap_clearance, p.tool_r)


def plate_rect(side: Side, p: Params, extra: float = 0.0) -> tuple[float, float, float, float]:
    m = p.plate_margin + extra
    return (-m, -m, side.width + m, side.depth + m)


def pivot_u(side: Side) -> float:
    """KLE x of the side's pivot line, where its top plane meets the centre plane."""
    return side.width + TYPE_A_PIVOT_INSET if side.outer_is_left else -TYPE_A_PIVOT_INSET


def outline(side: Side, p: Params) -> Sketch:
    """One side's outline: key area + walls + wrist rest, from the outer wall in to the pivot line."""
    w, d = side.width, side.depth
    front = d + p.wrist_depth
    outer_u = -p.wall if side.outer_is_left else w + p.wall
    inner_u = pivot_u(side) + (1.0 if side.outer_is_left else -1.0)  # overlap the centre prism
    sk = kle_rect(min(outer_u, inner_u), -p.wall, max(outer_u, inner_u), front)
    sk = rounded(sk, p.corner_r, lambda v: abs(v.X - outer_u) < 1e-6 and abs(v.Y - p.wall) < 1e-6)
    return rounded(sk, p.wrist_corner_r, lambda v: abs(v.X - outer_u) < 1e-6 and abs(v.Y + front) < 1e-6)


def center_outline(s: dict[str, Side], p: Params) -> list[np.ndarray]:
    """Quadrilateral between the two pivot lines, from the back wall to the wrist rest front."""
    l, r = s["left"], s["right"]
    z = 0.0  # same plane the side outlines are drawn on, so the prisms line up in plan
    return [
        l.frame.point(pivot_u(l), -p.wall, z),
        r.frame.point(pivot_u(r), -p.wall, z),
        r.frame.point(pivot_u(r), r.depth + p.wrist_depth, z),
        l.frame.point(pivot_u(l), l.depth + p.wrist_depth, z),
    ]


# ---------------------------------------------------------------------------------------------
# Planes that cut the body into pieces. All are vertical, so mating faces are machinable from above.


def vertical_plane(point: np.ndarray, along: np.ndarray, toward: np.ndarray) -> Plane:
    """Vertical plane containing `point` and horizontal direction `along`; normal points toward `toward`."""
    n = np.cross(along, [0.0, 0.0, 1.0])
    n[2] = 0.0
    n /= np.linalg.norm(n)
    if np.dot(n, toward) < 0:
        n = -n
    return Plane(origin=Vector(*point), z_dir=Vector(*n))


def joint_plane(s: dict[str, Side], p: Params) -> Plane:
    """Left/right joint: vertical, through the right frame's line u = -joint_offset. Normal points right."""
    f = s["right"].frame
    return vertical_plane(f.point(-p.joint_offset, 0), f.ey, f.ex)


def front_cut_plane(side: Side, p: Params) -> Plane:
    """Half / wrist-rest boundary for one side. Normal points to the back (toward the half)."""
    f = side.frame
    return vertical_plane(f.point(0, side.depth + p.wall), f.ex, -f.ey)


def keep(solid, pl: Plane, side: Keep):
    return split(solid, bisect_by=pl, keep=side)


# ---------------------------------------------------------------------------------------------


def floor_z(s: dict[str, Side], p: Params) -> float:
    """Desk height in Type A's frame: low enough for the stack under the lowest plate corner."""
    zs = []
    for side in s.values():
        x0, y0, x1, y1 = plate_rect(side, p)
        zs += [side.frame.point(x, y)[2] for x in (x0, x1) for y in (y0, y1)]
    return min(zs) - p.below_plate - p.panel_thickness


def whole_body(s: dict[str, Side], p: Params, z_floor: float) -> Part:
    """Vertical prism of the full footprint, under the lowest of the three top planes (as Type A)."""
    # Outlines are drawn on the plate plane, like the cavity, so wall thicknesses are true where it
    # matters (beside the plate and the bottom panel). The top edge is then offset by up to ~2.7 mm
    # (top_skin x the plate normal's horizontal lean), which only shifts the visible margin slightly.
    prisms = [extrude(plane(side, 0) * outline(side, p), amount=BIG, dir=(0, 0, 1), both=True) for side in s.values()]
    prisms.append(extrude(footprint(center_outline(s, p), z_floor - 1), amount=BIG, dir=(0, 0, 1)))
    body = reduce(lambda a, b: a + b, prisms)
    body = keep(body, Plane(origin=(0, 0, z_floor), z_dir=(0, 0, 1)), Keep.TOP)
    tops = [(side.frame.point(0, 0, p.top_skin), side.frame.up) for side in s.values()]
    tops.append((TYPE_A_CENTER_POINT, TYPE_A_CENTER_NORMAL))
    for point, normal in tops:
        body = keep(body, Plane(origin=Vector(*point), z_dir=Vector(*normal)), Keep.BOTTOM)
    return body


def footprint(points: list[np.ndarray], z: float) -> Face:
    """Horizontal face at height z from 3D points projected straight down (convex polygon)."""
    return Face(Wire.make_polygon([Vector(q[0], q[1], z) for q in points], close=True))


def bottom_faces(part: Part, z_floor: float) -> list[Face]:
    return [f for f in part.faces() if f.normal_at().Z < -0.999 and abs(f.center().Z - z_floor) < 1e-6]


def underside_pocket(part: Part, z_floor: float, wall: float, drop: Vector) -> tuple[Part, list[Face]]:
    """Region to pocket out from below: footprint inset by `wall`, up to the top surface moved by `drop`.

    Returns the pocket and its footprint faces (for the bottom panel recess).
    """
    base = [offset(f, -wall, kind=Kind.ARC) for f in bottom_faces(part, z_floor)]
    base = [f for b in base for f in b.faces()]
    prism = extrude(base, amount=BIG, dir=(0, 0, 1))
    return prism & (Location(drop) * part), base


def half_features(side: Side, p: Params, z_floor: float, half: Part) -> Part:
    """Everything cut out of a half: keycap openings, cavity (plate + spine), bottom panel recess."""
    up = Vector(*side.frame.up)
    opening = extrude(plane(side, p.top_skin + 1) * keycap_opening(side, p), amount=p.top_skin + 2, dir=-up)

    x0, y0, x1, y1 = plate_rect(side, p, p.plate_clearance)
    cavity_sk = rounded(kle_rect(x0, y0, x1, y1), p.cavity_corner_r, lambda v: True)
    cavity = extrude(plane(side, 0) * cavity_sk, amount=BIG, dir=(0, 0, -1))
    corners = [side.frame.point(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    footprints = [footprint(corners, z_floor)]

    if p.hollow_spine:
        pocket, base = underside_pocket(half, z_floor, p.shell, up * -p.top_skin)
        cavity = cavity + pocket
        footprints += base

    lip = [f for fp in footprints for f in offset(fp, p.panel_lip, kind=Kind.ARC).faces()]
    recess = extrude(lip, amount=p.panel_thickness, dir=(0, 0, 1))
    return opening + cavity + recess


def hollow_wrist(part: Part, p: Params, z_floor: float) -> Part:
    if not p.hollow_wrist:
        return part
    min_cos = min(side.frame.up[2] for side in sides().values())  # steepest top plane
    roof = (p.pocket_depth + p.wrist_roof) / min_cos  # vertical depth that covers the pocket + roof
    pocket, _ = underside_pocket(part, z_floor, p.wrist_shell, Vector(0, 0, -roof))
    return part - pocket


def neoprene_pocket(side: Side, p: Params) -> Part:
    w, d = side.width, side.depth
    back = d + p.wall + p.pad_rim
    front = d + p.wrist_depth - p.pad_rim
    pad = rounded(kle_rect(0, back, w, front), p.pad_corner_r, lambda v: True)
    pad = pad & offset(outline(side, p), -p.pad_rim, kind=Kind.ARC)
    return extrude(plane(side, p.top_skin + 1) * pad, amount=p.pocket_depth + 1, dir=Vector(*-side.frame.up))


def build(p: Params) -> dict[str, Part]:
    s = sides()
    joint = joint_plane(s, p)
    z_floor = floor_z(s, p)

    whole = whole_body(s, p, z_floor)
    fronts = [front_cut_plane(side, p) for side in s.values()]
    back = reduce(lambda body, pl: keep(body, pl, Keep.TOP), fronts, whole)
    wrist = whole - back

    right_half = keep(back, joint, Keep.TOP)
    left_half = keep(back, joint, Keep.BOTTOM)
    left_half -= half_features(s["left"], p, z_floor, left_half)
    right_half -= half_features(s["right"], p, z_floor, right_half)

    pockets = neoprene_pocket(s["left"], p) + neoprene_pocket(s["right"], p)
    if p.wrist_pieces == 1:
        wrists = {"wrist": wrist}
    elif p.wrist_pieces == 2:
        wrists = {
            "wrist_left": keep(wrist, joint, Keep.BOTTOM),
            "wrist_right": keep(wrist, joint, Keep.TOP),
        }
    else:
        raise ValueError("wrist_pieces must be 1 or 2")
    wrists = {n: hollow_wrist(w, p, z_floor) - pockets for n, w in wrists.items()}

    parts = {"left_half": left_half, "right_half": right_half, **wrists}
    to_desk = Location((0, 0, -z_floor))
    return {name: to_desk * part for name, part in parts.items()}
