"""Type B case: valid solids, X1C fit, and keys exactly where Type A put them."""

from functools import lru_cache

import pytest
from build123d import Vector

from nek.case import floor_z, sides
from nek.case import build as build_case
from nek.params import ALUMINUM, PRINT, VARIANTS
from nek.printability import check


@lru_cache
def parts(variant):
    return build_case(VARIANTS[variant])


def world(side_name, x, y, z, p):
    """Type A frame point -> Type B world (desk at z = 0)."""
    q = sides()[side_name].frame.point(x, y, z)
    return Vector(q[0], q[1], q[2] - floor_z(sides(), p))


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


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("side_name", ["left", "right"])
def test_keys_are_open_and_skin_matches_type_a(variant, side_name):
    p = VARIANTS[variant]
    half = parts(variant)[f"{side_name}_half"]
    side = sides()[side_name]
    for k in side.keys:
        assert not half.is_inside(world(side_name, *k.center_mm, 5.0, p)), k.label
    # just outside the key area: solid skin below the top surface, empty above it
    for x, y in [(-p.wall / 2, -p.wall / 2), (side.width + p.wall / 2, side.depth / 2)]:
        if side_name == "left" or x > 0:  # right half's inner edge is the joint, not a wall
            assert half.is_inside(world(side_name, x, y, p.top_skin - 0.5, p)), (x, y)
            assert not half.is_inside(world(side_name, x, y, p.top_skin + 0.5, p)), (x, y)


def test_aluminum_is_lighter_than_print_solid():
    alu = sum(pt.volume for pt in parts("aluminum").values())
    solid = sum(pt.volume for pt in parts("print").values())
    assert alu < 0.5 * solid


def wall_profile(half, points, p):
    """Walk inward along `points` at two heights: (inside at panel mid-height, inside just above panel)."""
    lo, hi = p.panel_thickness / 2, p.panel_thickness + 1.0
    return [(half.is_inside(Vector(q[0], q[1], lo)), half.is_inside(Vector(q[0], q[1], hi))) for q in points]


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("side_name", ["left", "right"])
@pytest.mark.parametrize("wall", ["outer", "back", "front"])
def test_walls_and_panel_recess(variant, side_name, wall):
    """Walking in from each wall: solid wall >= minimum, then a ledge (recess below, solid above), then cavity."""
    p = VARIANTS[variant]
    side = sides()[side_name]
    half = parts(variant)[f"{side_name}_half"]
    step = 0.1
    start = p.wall + 3
    w, d = side.width, side.depth
    if wall == "outer":
        sign = -1 if side_name == "left" else 1
        path = [(w / 2 + sign * (w / 2 + start - i * step), d / 2) for i in range(400)]
    elif wall == "back":
        path = [(w / 2, -start + i * step) for i in range(400)]
    else:
        path = [(w / 2, d + start - i * step) for i in range(400)]
    pts = [side.frame.point(x, y) for x, y in path]
    prof = wall_profile(half, pts, p)
    states = [s for i, s in enumerate(prof) if i == 0 or s != prof[i - 1]]
    assert states[:4] == [(False, False), (True, True), (False, True), (False, False)], states
    solid_beside_recess = prof.count((True, True)) * step
    ledge = prof.count((False, True)) * step
    assert solid_beside_recess >= p.shell - p.panel_lip - 0.2, solid_beside_recess
    assert ledge == pytest.approx(p.panel_lip, abs=0.3)


def test_top_is_lowest_of_three_planes():
    """Between the halves the top follows Type A's centre plane, not the halves' ridge."""
    from nek.frames import TYPE_A_CENTER_NORMAL as n, TYPE_A_CENTER_POINT as c

    z_floor = floor_z(sides(), ALUMINUM)
    x, y = 0.0, -60.0
    z_top = c[2] - (n[0] * (x - c[0]) + n[1] * (y - c[1])) / n[2] - z_floor
    left = parts("aluminum")["left_half"]
    assert left.is_inside(Vector(x, y, z_top - 0.5))
    assert not left.is_inside(Vector(x, y, z_top + 0.5))
