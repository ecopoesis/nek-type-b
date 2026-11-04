"""Type B case: valid solids, X1C fit, keys where Type A put them (per section), walls, joint, plates."""

from dataclasses import replace
from functools import lru_cache

import numpy as np
import pytest
from build123d import Vector

from nek.case import build as build_case
from nek.case import floor_z, joint_plane, plate_rect, screw_points, sections
from nek.frames import TYPE_A
from nek.params import ALUMINUM, PRINT, VARIANTS
from nek.plates import plate, section_cutouts
from nek.printability import check


@lru_cache
def parts(variant):
    return build_case(VARIANTS[variant])


def world(sec, x, y, z, p):
    """Section KLE point (mm, z up off the plate top) -> Type B world (desk at z = 0)."""
    q = sec.frame.point(x, y, z)
    return Vector(q[0], q[1], q[2] - floor_z(sections(p), p))


def half_of(variant, sec):
    return parts(variant)[f"{sec.half}_half"]


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_parts_are_single_valid_solids(variant):
    for name, part in parts(variant).items():
        assert part.is_valid, name
        assert len(part.solids()) == 1, name


def test_print_parts_fit_x1c():
    for name, part in parts("print").items():
        fit = check(name, part, PRINT)
        assert fit.fits, str(fit)


def test_piece_names():
    assert set(parts("aluminum")) == {"left_half", "right_half", "wrist"}
    assert set(parts("print")) == {"left_half", "right_half", "wrist_left", "wrist_right"}


def test_sections_cover_every_key_once():
    s = sections(ALUMINUM)
    assert set(s) == {"left", "right", "nav"}
    assert len(s["left"].keys) == 34 and len(s["right"].keys) + len(s["nav"].keys) == 54
    assert all(k.cell_mm[0] >= s["nav"].u0 for k in s["nav"].keys)


def test_nav_block_is_level_and_keeps_slope():
    s = sections(ALUMINUM)
    nav, main = s["nav"].frame, s["right"].frame
    assert nav.ex[2] == pytest.approx(0, abs=1e-9)  # rows level
    assert np.allclose(nav.ey, main.ey)  # columns: same slope as the main keys
    h = ALUMINUM.nav_split_u * 19.05
    assert np.allclose(nav.point(h, 50), main.point(h, 50))  # hinged at the gap, not moved


def test_nav_fold_lowers_the_keyboard():
    flat = floor_z(sections(ALUMINUM), ALUMINUM)
    tented = floor_z(sections(replace(ALUMINUM, nav_flat=False)), ALUMINUM)
    assert flat - tented > 12  # floor rises, so everything above it gets shorter


def test_halves_keep_type_a_angles():
    s = sections(ALUMINUM)
    for name in ("left", "right"):
        assert np.allclose(s[name].frame.ex, TYPE_A[name].ex)
        assert np.allclose(s[name].frame.ey, TYPE_A[name].ey)


def test_gap_closed_to_joint_wall():
    """Each half's cavity sits exactly joint_wall + panel_lip from the joint (the recess takes the lip)."""
    p = ALUMINUM
    s = sections(p)
    j = joint_plane(s, p)
    n = np.array([j.z_dir.X, j.z_dir.Y, j.z_dir.Z])
    o = np.array([j.origin.X, j.origin.Y, j.origin.Z])
    x0, y0, x1, y1 = plate_rect(s["left"], p, p.plate_clearance)
    left = min(n @ (o - s["left"].frame.point(x, y)) for x in (x0, x1) for y in (y0, y1))
    assert left == pytest.approx(p.joint_wall + p.panel_lip, abs=1e-6)
    x0, y0, x1, y1 = plate_rect(s["right"], p, p.plate_clearance)
    right = min(n @ (s["right"].frame.point(x0, y) - o) for y in (y0, y1))
    assert right == pytest.approx(p.joint_wall + p.panel_lip, abs=1e-6)


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("name", ["left", "right", "nav"])
def test_keys_are_open_and_skin_is_solid(variant, name):
    p = VARIANTS[variant]
    sec = sections(p)[name]
    half = half_of(variant, sec)
    for k in sec.keys:
        assert not half.is_inside(world(sec, *k.center_mm, 5.0, p)), k.label
    # just behind the back row: solid skin below the top surface, empty above it
    u = (sec.u0 + sec.u1) / 2
    assert half.is_inside(world(sec, u, -p.wall / 2, p.top_skin - 0.5, p))
    assert not half.is_inside(world(sec, u, -p.wall / 2, p.top_skin + 0.5, p))


def _walk(half, sec, p, start, direction):
    """Walk from `start` (KLE mm) along `direction`, sampling just below and just above the panel."""
    lo, hi = p.panel_thickness / 2, p.panel_thickness + 1.0
    step = 0.1
    prof = []
    for i in range(int((p.wall + 6) / step)):
        x, y = np.array(start) + i * step * np.array(direction)
        q = sec.frame.point(x, y)
        prof.append((half.is_inside(Vector(q[0], q[1], lo)), half.is_inside(Vector(q[0], q[1], hi))))
    return prof, step


WALLS = [("left", "outer"), ("left", "back"), ("left", "front"), ("right", "back"), ("right", "front"),
         ("nav", "outer"), ("nav", "back"), ("nav", "front")]


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("name,wall", WALLS)
def test_walls_and_panel_recess(variant, name, wall):
    """Walking in from each wall: outside, solid wall, ledge (recess below, solid above), cavity."""
    p = VARIANTS[variant]
    sec = sections(p)[name]
    half = half_of(variant, sec)
    u_mid, d = (sec.u0 + sec.u1) / 2, sec.depth
    start, direction = {
        ("outer", "left"): ((sec.u0 - p.wall - 3, d / 2), (1, 0)),
        ("outer", "nav"): ((sec.u1 + p.wall + 3, d / 2), (-1, 0)),
        ("back", name): ((u_mid, -p.wall - 3), (0, 1)),
        ("front", name): ((u_mid, d + p.wall + 3), (0, -1)),
    }[(wall, name if wall == "outer" else name)]
    prof, step = _walk(half, sec, p, start, direction)
    states = [s for i, s in enumerate(prof) if i == 0 or s != prof[i - 1]]
    assert states[:4] == [(False, False), (True, True), (False, True), (False, False)], states
    assert prof.count((True, True)) * step >= p.shell - p.panel_lip - 0.3
    assert prof.count((False, True)) * step == pytest.approx(p.panel_lip, abs=0.4)


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_plate_screws_have_tapped_holes(variant):
    p = VARIANTS[variant]
    for sec in sections(p).values():
        half = half_of(variant, sec)
        for u, v in screw_points(sec, p):
            assert not half.is_inside(world(sec, u, v, p.tap_depth - 1, p)), (sec.name, u, v)
            assert half.is_inside(world(sec, u + p.tap_hole_d, v, p.tap_depth - 1, p)), (sec.name, u, v)
            assert half.is_inside(world(sec, u, v, p.tap_depth + 1, p)), (sec.name, u, v)  # blind


@pytest.mark.parametrize("name", ["left", "right", "nav"])
def test_plates(name):
    p = ALUMINUM
    sec = sections(p)[name]
    face = plate(sec, p)
    assert face.is_valid
    assert len(section_cutouts(sec)) == len(sec.keys)
    assert len(face.inner_wires()) == len(sec.keys) + len(screw_points(sec, p))
    # every screw hole sits in the frame, clear of the plate edge and every cutout
    x0, y0, x1, y1 = plate_rect(sec, p)
    r = p.plate_hole_d / 2
    for u, v in screw_points(sec, p):
        assert x0 + r + 1 <= u <= x1 - r - 1 and y0 + r + 1 <= v <= y1 - r - 1
        for q in section_cutouts(sec):
            assert np.min(np.hypot(q[:, 0] - u, q[:, 1] - v)) > r + 1


def test_top_follows_centre_plane_between_halves():
    """In front of the keys, between the halves' pivot lines, the top is Type A's centre plane."""
    from nek.frames import TYPE_A_CENTER_NORMAL as n, TYPE_A_CENTER_POINT as c

    p = ALUMINUM
    s = sections(p)
    z_floor = floor_z(s, p)
    l, r = s["left"], s["right"]
    v = l.depth + p.wrist_depth - 15
    x, y = ((l.frame.point(l.u1 + 35, v) + r.frame.point(-35, v)) / 2)[:2]
    z_top = c[2] - (n[0] * (x - c[0]) + n[1] * (y - c[1])) / n[2] - z_floor
    wrist = parts("aluminum")["wrist"]
    assert wrist.is_inside(Vector(x, y, z_top - 0.5))
    assert not wrist.is_inside(Vector(x, y, z_top + 0.5))


def test_aluminum_is_lighter_than_print_solid():
    alu = sum(pt.volume for pt in parts("aluminum").values())
    solid = sum(pt.volume for pt in parts("print").values())
    assert alu < 0.5 * solid


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("name", ["left", "right", "nav"])
def test_plate_fits_its_cavity(variant, name):
    """Every point of the plate outline, at mid-thickness, is in open space (no metal in the way)."""
    p = VARIANTS[variant]
    sec = sections(p)[name]
    half = half_of(variant, sec)
    face = plate(sec, p)
    for e in face.outer_wire().edges():
        for q in e.positions([i / 8 for i in range(9)]):
            assert not half.is_inside(world(sec, q.X, -q.Y, -0.75, p)), (name, q.X, -q.Y)


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_joint_wall(variant):
    """Across the left/right joint, at the panel recess and above it, both halves keep >= joint_wall."""
    p = VARIANTS[variant]
    s = sections(p)
    j = joint_plane(s, p)
    n = np.array([j.z_dir.X, j.z_dir.Y, j.z_dir.Z])
    o = np.array([j.origin.X, j.origin.Y, j.origin.Z])
    along = np.cross([0, 0, 1.0], n)
    r = s["right"]
    for v in np.linspace(-p.plate_margin, r.depth + p.plate_margin, 7):  # along the right half's keys
        base = o + along * (along @ (r.frame.point(0, v) - o))
        for z in (p.panel_thickness / 2, p.panel_thickness + 2, 15.0):
            for name, sign in (("left_half", -1), ("right_half", 1)):
                half = parts(variant)[name]
                solid = [half.is_inside(Vector(*(base + sign * t * n)[:2], z)) for t in np.arange(0.05, 6, 0.05)]
                if not solid[0]:
                    continue  # above the top surface here
                wall = (solid.index(False) if False in solid else len(solid)) * 0.05
                assert wall >= p.joint_wall - 0.1, (name, v, z, wall)


def test_skin_strip_at_fold():
    """The skin between the main and nav keycap openings is >= 2 mm wide all the way up."""
    p = ALUMINUM
    s = sections(p)
    half = parts("aluminum")["right_half"]
    r = s["right"]
    hinge = p.nav_split_u * 19.05
    for row_y in (19.05 * 1.75, 19.05 * 2.75):  # across rows that have keys on both sides
        for z in (1.0, 5.0, 9.5):
            us = np.arange(hinge - 4, hinge + 4, 0.05)
            solid = [half.is_inside(world(r, u, row_y, z, p)) for u in us]
            assert sum(solid) * 0.05 >= 2.0, (row_y, z, sum(solid) * 0.05)


@pytest.mark.parametrize("name", ["right", "nav"])
def test_fold_walls_clear_keycaps(name):
    """The leaning walls at the fold stay clear of an MX keycap envelope (18.2 mm base, 6.5 mm above the
    plate, ~1 mm inward taper per 3.5 mm rise) by at least 0.5 mm."""
    p = ALUMINUM
    sec = sections(p)[name]
    half = parts("aluminum")["right_half"]
    hinge = p.nav_split_u * 19.05
    side = [k for k in sec.keys if abs((k.cell_mm[2] if name == "right" else k.cell_mm[0]) - hinge) < 3]
    assert side
    for k in side:
        x0, y0, x1, y1 = k.cell_mm
        cy = (y0 + y1) / 2
        for z, inset in ((6.5, 0.425), (p.top_skin, 0.425 + 1.0)):
            edge = (x1 - inset) if name == "right" else (x0 + inset)
            probe = edge + (0.5 if name == "right" else -0.5)
            assert not half.is_inside(world(sec, probe, cy, z, p)), (k.label, z)
