"""Check the measured half frames against Type A's machined body (body/target/body.step).

Each key's centre, 5 mm above the plate (inside the 10 mm top skin), must be inside a keycap opening.
A point just past each corner of the key area, at the same height, must be solid aluminum.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from build123d import Vector, import_step

from nek.frames import TYPE_A
from nek.layout import extent_mm, load

TYPE_A_STEP = Path(__file__).resolve().parents[2] / "body" / "target" / "body.step"


@lru_cache
def type_a():
    return import_step(TYPE_A_STEP).solids()[0]


def solid_at(p) -> bool:
    return type_a().is_inside(Vector(*p))


@pytest.mark.parametrize("side", ["left", "right"])
def test_frames_are_orthonormal(side):
    f = TYPE_A[side]
    assert np.linalg.norm(f.ex) == pytest.approx(1)
    assert np.linalg.norm(f.ey) == pytest.approx(1)
    assert np.dot(f.ex, f.ey) == pytest.approx(0, abs=1e-9)
    assert f.up[2] > 0.9


@pytest.mark.parametrize("side", ["left", "right"])
def test_key_centres_are_in_type_a_openings(side):
    f = TYPE_A[side]
    blocked = [k.label for k in load(side) if solid_at(f.point(*k.center_mm, 5.0))]
    assert blocked == []


@pytest.mark.parametrize("side", ["left", "right"])
def test_skin_outside_key_area_is_solid(side):
    f = TYPE_A[side]
    w, d = extent_mm(load(side))
    m = 5.0  # into Type A's 20 mm plate padding, which is under the top skin
    for x, y in [(-m, -m), (w + m, -m), (-m, d + m), (w + m, d + m)]:
        assert solid_at(f.point(x, y, 5.0)), (x, y)


@pytest.mark.parametrize("side", ["left", "right"])
def test_top_surface_is_10mm_above_plate(side):
    f = TYPE_A[side]
    w, d = extent_mm(load(side))
    p = (w / 2, d + 10)  # in the padding in front of the keys
    assert solid_at(f.point(*p, 9.5))
    assert not solid_at(f.point(*p, 10.5))
