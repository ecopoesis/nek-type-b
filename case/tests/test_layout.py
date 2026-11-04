"""Check the KLE parser against swillkb's switch plates from Type A."""

import re
from pathlib import Path

import pytest

from nek.layout import extent_mm, load, load_type_a

BUILD_DATA = Path(__file__).resolve().parents[2] / "body" / "build_data"
SVG_KEY_ORIGIN = 25.0  # swillkb: 5 mm sheet margin + 20 mm plate padding


def switch_cutout_centers(side: str) -> list[tuple[float, float]]:
    svg = (BUILD_DATA / f"{side}_switch.svg").read_text()
    centers = []
    for pts in re.findall(r'<polygon points="([^"]+)"', svg):
        xy = [tuple(map(float, p.split(","))) for p in pts.split()]
        xs, ys = zip(*xy)
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if abs(w - 15.6) < 0.2 and abs(h - 14) < 0.2:  # MX cutout (swillkb "opening" type)
            centers.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2))
    return centers


@pytest.mark.parametrize("side,width,depth", [("left", 7, 6.25), ("right", 11.75, 6.25)])
def test_extent(side, width, depth):
    w, d = extent_mm(load_type_a(side))
    assert w == pytest.approx(width * 19.05)
    assert d == pytest.approx(depth * 19.05)


@pytest.mark.parametrize("side", ["left", "right"])
def test_every_switch_cutout_matches_a_key(side):
    keys = load_type_a(side)
    centers = switch_cutout_centers(side)
    assert len(centers) > 30
    for cx, cy in centers:
        nearest = min(
            keys,
            key=lambda k: (k.center_mm[0] + SVG_KEY_ORIGIN - cx) ** 2
            + (k.center_mm[1] + SVG_KEY_ORIGIN - cy) ** 2,
        )
        kx, ky = nearest.center_mm
        assert kx + SVG_KEY_ORIGIN == pytest.approx(cx, abs=0.05)
        assert ky + SVG_KEY_ORIGIN == pytest.approx(cy, abs=0.05)


@pytest.mark.parametrize("side", ["left", "right"])
def test_type_b_moves_only_the_f_row_back(side):
    """Type B = Type A with the F-row 0.07u further back (F-row gap 0.25u -> 0.32u = 6.1 mm)."""
    a, b = load_type_a(side), load(side)
    assert [(k.x, k.w, k.h, k.label) for k in a] == [(k.x, k.w, k.h, k.label) for k in b]
    for ka, kb in zip(a, b):
        assert kb.y == pytest.approx(ka.y - (0.07 if ka.y == 0 else 0.0))
