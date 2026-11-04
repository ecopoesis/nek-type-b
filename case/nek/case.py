"""Type B case geometry: two keyboard halves and a wrist rest (one or two pieces).

The keys are grouped into *sections*, each with its own plate, PCB and plane:
  left    the whole left half (Type A's left frame)
  right   the right half's main keys (Type A's right frame)
  nav     the media / nav / arrow block, folded level about the 0.25u gap (optional, `nav_flat`)
Each half is slid sideways toward the centre (`close_gap`) without changing its angles.

Construction, in Type A's world frame:
  1. Footprint: each section's outline (keys + walls + wrist rest) is drawn on its plate plane and
     extruded vertically, plus the region between the halves' pivot lines. Outer walls are vertical
     (3-axis machinable, prints without overhangs).
  2. Top: left, centre and right-main form one surface: the lowest of their three planes (as Type A).
     The nav block is a separate prism under its own plane, joined at the fold.
  3. The body is cut into pieces by vertical planes: the left/right joint and each side's front cut
     between the half and the wrist rest.
  4. Each section gets keycap openings through the top skin, a plate/PCB cavity open to the bottom,
     tapped holes for the plate screws, and a recess for the acrylic bottom panel. The left half's
     spine and the wrist rest are pocketed from below (aluminum). The wrist rest gets neoprene pockets.
  5. Everything is shifted so the desk is z = 0.
"""

import math
from dataclasses import dataclass
from functools import reduce

import numpy as np
from build123d import (
    Circle,
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

from .frames import TYPE_A, TYPE_A_CENTER_NORMAL, TYPE_A_CENTER_POINT, TYPE_A_PIVOT_INSET, Frame, folded, shifted
from .layout import U, Key, extent_mm, load
from .params import Params

BIG = 1000.0
OVERLAP = 10.0  # prisms overlap their neighbours by this much before being clipped

# Extra plate screws inside the key field (KLE mm), besides the F-row gap row and the front row:
# the empty space either side of the up arrow.
IN_FIELD_SCREWS = {
    "left": [],
    "right": [],
    "nav": [(9.25 * U, 4.0 * U), (11.25 * U, 4.0 * U)],
}


@dataclass
class Section:
    name: str  # "left", "right" or "nav"
    half: str  # which case half it lives in: "left" or "right"
    frame: Frame
    keys: list[Key]
    u0: float  # KLE x extent of the key cells, mm
    u1: float
    depth: float
    edge0: str  # what the u0 edge faces: "outer", "spine" or "hinge"
    edge1: str  # same for the u1 edge

    @property
    def top(self) -> float:
        """KLE y of the back edge of the key cells (the F-row sits slightly behind y = 0)."""
        return min(k.cell_mm[1] for k in self.keys)

    @property
    def gap_v(self) -> float:
        """KLE y of the centre of the gap between the F-row and the number row."""
        frow = [k for k in self.keys if k.cell_mm[1] < self.top + 0.5 * U]
        rest = [k for k in self.keys if k not in frow]
        return (max(k.cell_mm[3] for k in frow) + min(k.cell_mm[1] for k in rest)) / 2


def _margin(kind: str, p: Params) -> float:
    if kind in ("outer", "spine"):
        return p.plate_margin
    return (0.25 * U - p.plate_hinge_clearance) / 2  # half the 0.25u gap, less clearance


def plate_rect(sec: Section, p: Params, extra: float = 0.0) -> tuple[float, float, float, float]:
    return (
        sec.u0 - _margin(sec.edge0, p) - extra,
        sec.top - p.plate_margin - extra,
        sec.u1 + _margin(sec.edge1, p) + extra,
        sec.depth + p.plate_margin_front + extra,
    )


def pcb_rect(sec: Section, p: Params) -> tuple[float, float, float, float]:
    m0, m1 = (min(p.pcb_margin, _margin(e, p)) for e in (sec.edge0, sec.edge1))
    return (sec.u0 - m0, sec.top - p.pcb_margin, sec.u1 + m1, sec.depth + p.pcb_margin)


def _raw_sections(p: Params, frames: dict[str, Frame]) -> list[Section]:
    left = load("left")
    wl, dl = extent_mm(left)
    out = [Section("left", "left", frames["left"], left, 0.0, wl, dl, "outer", "spine")]
    right = load("right")
    wr, dr = extent_mm(right)
    if not p.nav_flat:
        return out + [Section("right", "right", frames["right"], right, 0.0, wr, dr, "spine", "outer")]
    split_mm = p.nav_split_u * U
    main = [k for k in right if k.cell_mm[2] <= split_mm]
    nav = [k for k in right if k.cell_mm[0] >= split_mm]
    assert len(main) + len(nav) == len(right), "a key straddles nav_split_u"
    nav_frame = folded(frames["right"], split_mm, p.nav_tent)
    return out + [
        Section("right", "right", frames["right"], main, 0.0, max(k.cell_mm[2] for k in main), dr, "spine", "hinge"),
        Section("nav", "right", nav_frame, nav, min(k.cell_mm[0] for k in nav), wr, dr, "hinge", "outer"),
    ]


def sections(p: Params) -> dict[str, Section]:
    """All sections, with the halves slid together if `close_gap`."""
    frames = dict(TYPE_A)
    if p.close_gap:
        secs = {s.name: s for s in _raw_sections(p, frames)}
        jp, jn = _joint(secs["right"], p)
        x0, y0, x1, y1 = plate_rect(secs["left"], p, p.plate_clearance)
        corners = [secs["left"].frame.point(x, y) for x in (x0, x1) for y in (y0, y1)]
        # left panel recess -> joint, horizontal (the recess is the cavity footprint grown by panel_lip)
        dist = min(np.dot(jn, jp - c) for c in corners) - p.panel_lip
        dx = max(0.0, (dist - p.joint_wall) / (2 * jn[0]))
        frames = {"left": shifted(TYPE_A["left"], dx), "right": shifted(TYPE_A["right"], -dx)}
    return {s.name: s for s in _raw_sections(p, frames)}


# ---------------------------------------------------------------------------------------------
# 2D helpers. Sketches are drawn in a section's plane coordinates: u = KLE x, v = -KLE y.


def plane(sec: Section, z: float) -> Plane:
    """The plane parallel to the section's plate, z mm above the plate's top face."""
    f = sec.frame
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


def keycap_opening(sec: Section, p: Params) -> Sketch:
    cells = reduce(lambda a, b: a + b, [kle_rect(*k.cell_mm) for k in sec.keys])
    return close_corners(cells, p.keycap_clearance, p.tool_r)


def pivot_u(sec: Section) -> float:
    """KLE x of a half's pivot line, where its top plane meets the centre plane."""
    return sec.u1 + TYPE_A_PIVOT_INSET if sec.half == "left" else -TYPE_A_PIVOT_INSET


def hinge_u(p: Params) -> float:
    return p.nav_split_u * U


def half_extent(sec: Section, p: Params) -> tuple[float, float]:
    """KLE x range of the whole half this section belongs to: outer wall to past the pivot line.

    Sections of the same half share KLE coordinates (the nav frame is folded, not moved), so every
    section of a half draws the same outline and is then clipped at the fold. That keeps the wrist
    rest's big outer corner continuous across the fold."""
    if sec.half == "left":
        return sec.u0 - p.wall, pivot_u(sec) + OVERLAP
    right_width, _ = extent_mm(load("right"))
    return pivot_u(sec) - OVERLAP, right_width + p.wall


def outline(sec: Section, p: Params) -> Sketch:
    """The outline of the section's half: keys + walls + wrist rest, overlapping the centre."""
    a, b = half_extent(sec, p)
    outer = a if sec.half == "left" else b
    front = sec.depth + p.wrist_depth
    back = sec.top - p.wall
    sk = kle_rect(a, back, b, front)
    sk = rounded(sk, p.corner_r, lambda v: abs(v.X - outer) < 1e-6 and abs(v.Y + back) < 1e-6)
    return rounded(sk, p.wrist_corner_r, lambda v: abs(v.X - outer) < 1e-6 and abs(v.Y + front) < 1e-6)


# ---------------------------------------------------------------------------------------------
# Planes. Cut planes are all vertical, so mating faces are machinable from above.


def vertical_plane(point: np.ndarray, along: np.ndarray, toward: np.ndarray) -> Plane:
    """Vertical plane containing `point` and horizontal direction `along`; normal points toward `toward`."""
    n = np.cross(along, [0.0, 0.0, 1.0])
    n[2] = 0.0
    n /= np.linalg.norm(n)
    if np.dot(n, toward) < 0:
        n = -n
    return Plane(origin=Vector(*point), z_dir=Vector(*n))


def _joint(right: Section, p: Params) -> tuple[np.ndarray, np.ndarray]:
    """Point on, and horizontal normal (pointing right) of, the left/right joint plane."""
    f = right.frame
    n = np.cross(f.ey, [0.0, 0.0, 1.0])
    n[2] = 0.0
    n /= np.linalg.norm(n)
    n *= np.sign(n @ f.ex)
    # joint_wall is measured horizontally (the joint face is vertical); the plate frame is tilted
    cavity_u = right.u0 - p.plate_margin - p.plate_clearance
    u = cavity_u - (p.joint_wall + p.panel_lip) / (n @ f.ex)  # thinnest point is beside the panel recess
    return f.point(u, 0), n


def joint_plane(s: dict[str, Section], p: Params) -> Plane:
    point, normal = _joint(s["right"], p)
    return Plane(origin=Vector(*point), z_dir=Vector(*normal))


def front_cut_plane(sec: Section, p: Params) -> Plane:
    """Half / wrist-rest boundary for one half. Normal points to the back (toward the half)."""
    f = sec.frame
    return vertical_plane(f.point(0, sec.depth + p.wall_front), f.ex, -f.ey)


def top_plane(sec: Section, p: Params) -> Plane:
    return Plane(origin=Vector(*sec.frame.point(0, 0, p.top_skin)), z_dir=Vector(*sec.frame.up))


def hinge_plane(s: dict[str, Section], p: Params) -> Plane:
    """Vertical plane through the line where the main and nav top surfaces meet. Normal points outward."""
    a, b = s["right"].frame, s["nav"].frame
    na, nb = a.up, b.up
    pa, pb = a.point(0, 0, p.top_skin), b.point(0, 0, p.top_skin)
    d = np.cross(na, nb)
    if np.linalg.norm(d) < 1e-3:
        raise ValueError("nav block is not folded (nav_tent equals the main tent); set nav_flat=False")
    on_both = np.linalg.solve(np.array([na, nb, d]), [na @ pa, nb @ pb, d @ a.point(hinge_u(p), 0)])
    return vertical_plane(on_both, d, a.ex)


def keep(solid, pl: Plane, side: Keep):
    return split(solid, bisect_by=pl, keep=side)


def keep_below(solid, pl: Plane):
    return keep(solid, pl, Keep.BOTTOM)


# ---------------------------------------------------------------------------------------------


def floor_z(s: dict[str, Section], p: Params) -> float:
    """Desk height in Type A's frame: room for the switch/PCB stack under the lowest PCB corner, and
    for the plate itself under the lowest plate corner."""
    zs = []
    for sec in s.values():
        x0, y0, x1, y1 = pcb_rect(sec, p)
        zs += [sec.frame.point(x, y)[2] - p.below_plate for x in (x0, x1) for y in (y0, y1)]
        x0, y0, x1, y1 = plate_rect(sec, p)
        zs += [sec.frame.point(x, y)[2] - p.plate_thickness - p.panel_clearance for x in (x0, x1) for y in (y0, y1)]
    return min(zs) - p.panel_thickness


def footprint(points: list[np.ndarray], z: float) -> Face:
    """Horizontal face at height z from 3D points projected straight down (convex polygon)."""
    return Face(Wire.make_polygon([Vector(q[0], q[1], z) for q in points], close=True))


def _xy_line_intersection(p0, d0, p1, d1) -> tuple[float, float]:
    """Parameters (t0, t1) where p0 + t0 d0 and p1 + t1 d1 meet in plan view."""
    A = np.array([[d0[0], -d1[0]], [d0[1], -d1[1]]])
    return tuple(np.linalg.solve(A, (p1 - p0)[:2]))


def center_region(s: dict[str, Section], p: Params, z_floor: float) -> Part | None:
    """Prism between the two halves' pivot lines (where the centre plane is the top)."""
    l, r = s["left"], s["right"]
    front = l.depth + p.wrist_depth
    lb, lf = l.frame.point(pivot_u(l), l.top - p.wall), l.frame.point(pivot_u(l), front)
    rb, rf = r.frame.point(pivot_u(r), r.top - p.wall), r.frame.point(pivot_u(r), front)
    t, _ = _xy_line_intersection(rb, rf - rb, lb, lf - lb)
    if t >= 1:  # pivot lines cross in front of the wrist rest: no centre region
        return None
    pts = [rb + t * (rf - rb), rf, lf] if t > 0 else [lb, rb, rf, lf]
    return extrude(footprint(pts, z_floor - 1), amount=BIG, dir=(0, 0, 1))


def center_front_plane(s: dict[str, Section], p: Params) -> Plane:
    """Straight front edge across the centre, as on Type A. Normal points to the back."""
    l, r = s["left"], s["right"]
    pl = l.frame.point(pivot_u(l), l.depth + p.wrist_depth)
    pr = r.frame.point(pivot_u(r), r.depth + p.wrist_depth)
    return vertical_plane((pl + pr) / 2, pr - pl, np.array([0.0, 1.0, 0.0]))


def whole_body(s: dict[str, Section], p: Params, z_floor: float) -> Part:
    def prism(sec):
        body = extrude(plane(sec, 0) * outline(sec, p), amount=BIG, dir=(0, 0, 1), both=True)
        return keep(body, Plane(origin=(0, 0, z_floor), z_dir=(0, 0, 1)), Keep.TOP)

    main = [prism(s["left"]), prism(s["right"])]
    if "nav" in s:
        hinge = hinge_plane(s, p)
        main[1] = keep(main[1], hinge, Keep.BOTTOM)
    centre = center_region(s, p, z_floor)
    if centre is not None:
        main.append(keep(centre, Plane(origin=(0, 0, z_floor), z_dir=(0, 0, 1)), Keep.TOP))
    body = reduce(lambda a, b: a + b, main)
    for pl in [top_plane(s["left"], p), top_plane(s["right"], p)]:
        body = keep_below(body, pl)
    centre_top = Plane(origin=Vector(*TYPE_A_CENTER_POINT), z_dir=Vector(*TYPE_A_CENTER_NORMAL))
    body = keep_below(body, centre_top)
    if "nav" in s:
        nav = keep_below(keep(prism(s["nav"]), hinge, Keep.TOP), top_plane(s["nav"], p))
        body = body + nav
    return keep(body, center_front_plane(s, p), Keep.TOP)


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


def _spaced(a: float, b: float, spacing: float) -> list[float]:
    n = max(1, math.ceil(abs(b - a) / spacing))
    return [a + (b - a) * i / n for i in range(n + 1)]


def gap_screw_points(sec: Section, p: Params) -> list[tuple[float, float]]:
    """A row of screws along the widened gap between the F-row and the number row."""
    return [(u, sec.gap_v) for u in _spaced(sec.u0 + 4, sec.u1 - 4, p.screw_spacing)]


def screw_points(sec: Section, p: Params) -> list[tuple[float, float]]:
    """Plate screw centres in KLE mm: rows along the F-row gap and the front frame, plus extras."""
    front = [(u, sec.depth + p.screw_inset) for u in _spaced(sec.u0 + 2, sec.u1 - 2, p.screw_spacing)]
    front += gap_screw_points(sec, p)
    extra = IN_FIELD_SCREWS[sec.name]
    if sec.name == "right" and sec.edge1 == "outer":  # nav block not split off: its screws are ours
        extra = extra + IN_FIELD_SCREWS["nav"]
    return front + list(extra)


def opening_direction(s: dict[str, Section], sec: Section) -> np.ndarray:
    """Direction the keycap opening's walls run. Normally the plate normal. Either side of the nav fold,
    both openings use the bisector of the two normals, so the strip of skin between them keeps its width
    instead of tapering to a knife edge (each wall leans ~6° off its keys, still clear of the keycaps)."""
    if sec.half == "right" and "nav" in s:
        d = s["right"].frame.up + s["nav"].frame.up
        return d / np.linalg.norm(d)
    return sec.frame.up


def section_features(s: dict[str, Section], sec: Section, p: Params, z_floor: float) -> tuple[Part, list[Face]]:
    """Keycap opening, plate cavity and tapped screw holes for one section; plus the cavity footprint."""
    up = Vector(*sec.frame.up)
    d = Vector(*opening_direction(s, sec))
    # anchored at the plate (where the keycaps sit) and run up through the skin along d
    height = (p.top_skin + 2) / d.dot(up)
    opening = extrude(plane(sec, -1) * keycap_opening(sec, p), amount=height, dir=d)

    x0, y0, x1, y1 = plate_rect(sec, p, p.plate_clearance)
    cavity_sk = rounded(kle_rect(x0, y0, x1, y1), p.cavity_corner_r, lambda v: True)
    cavity = extrude(plane(sec, 0) * cavity_sk, amount=BIG, dir=(0, 0, -1))
    corners = [sec.frame.point(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]

    holes = reduce(lambda a, b: a + b, [Pos(u, -v) * Circle(p.tap_hole_d / 2) for u, v in screw_points(sec, p)])
    taps = extrude(plane(sec, -1) * holes, amount=p.tap_depth + 1, dir=up)
    return opening + cavity + taps, [footprint(corners, z_floor)]


def half_features(s: dict[str, Section], half_name: str, p: Params, z_floor: float, half: Part) -> Part:
    cuts, footprints = [], []
    for sec in s.values():
        if sec.half == half_name:
            c, fp = section_features(s, sec, p, z_floor)
            cuts.append(c)
            footprints += fp
    if half_name == "left" and p.hollow_spine:
        pocket, base = underside_pocket(half, z_floor, p.shell, Vector(*s["left"].frame.up) * -p.top_skin)
        cuts.append(pocket)
        footprints += base
    lip = [f for fp in footprints for f in offset(fp, p.panel_lip, kind=Kind.ARC).faces()]
    cuts.append(extrude(lip, amount=p.panel_thickness, dir=(0, 0, 1)))
    return reduce(lambda a, b: a + b, cuts)


def hollow_wrist(part: Part, s: dict[str, Section], p: Params, z_floor: float) -> Part:
    if not p.hollow_wrist:
        return part
    min_cos = min(sec.frame.up[2] for sec in s.values())  # steepest top plane
    roof = (p.pocket_depth + p.wrist_roof) / min_cos  # vertical depth that covers the pocket + roof
    pocket, _ = underside_pocket(part, z_floor, p.wrist_shell, Vector(0, 0, -roof))
    return part - pocket


def neoprene_pocket(sec: Section, p: Params) -> Part:
    """Pad in front of a section's keys (the main keys only on the right)."""
    back = sec.depth + p.wall_front + p.pad_rim
    front = sec.depth + p.wrist_depth - p.pad_rim
    pad = rounded(kle_rect(sec.u0, back, sec.u1, front), p.pad_corner_r, lambda v: True)
    pad = pad & offset(outline(sec, p), -p.pad_rim, kind=Kind.ARC)
    return extrude(plane(sec, p.top_skin + 1) * pad, amount=p.pocket_depth + 1, dir=Vector(*-sec.frame.up))


def build(p: Params) -> dict[str, Part]:
    s = sections(p)
    joint = joint_plane(s, p)
    z_floor = floor_z(s, p)

    whole = whole_body(s, p, z_floor)
    back = keep(keep(whole, front_cut_plane(s["left"], p), Keep.TOP), front_cut_plane(s["right"], p), Keep.TOP)
    wrist = whole - back

    left_half = keep(back, joint, Keep.BOTTOM)
    right_half = keep(back, joint, Keep.TOP)
    left_half -= half_features(s, "left", p, z_floor, left_half)
    right_half -= half_features(s, "right", p, z_floor, right_half)

    pockets = neoprene_pocket(s["left"], p) + neoprene_pocket(s["right"], p)
    if p.wrist_pieces == 1:
        wrists = {"wrist": wrist}
    elif p.wrist_pieces == 2:
        wrists = {"wrist_left": keep(wrist, joint, Keep.BOTTOM), "wrist_right": keep(wrist, joint, Keep.TOP)}
    else:
        raise ValueError("wrist_pieces must be 1 or 2")
    wrists = {n: hollow_wrist(w, s, p, z_floor) - pockets for n, w in wrists.items()}

    parts = {"left_half": left_half, "right_half": right_half, **wrists}
    to_desk = Location((0, 0, -z_floor))
    return {name: to_desk * part for name, part in parts.items()}
