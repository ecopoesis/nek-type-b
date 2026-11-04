"""Steel switch plates, one per section, as 2D faces for laser cutting (DXF).

Switch and stabilizer cutouts are copied exactly from Type A's swillkb plates (body/build_data/*_switch.svg),
which use MX cutouts with opening notches. Only the outline changes: a narrow frame with M2 screw holes
replaces Type A's 20 mm padding.

Coordinates: KLE mm with y flipped (x right, y up), origin at the section's KLE (0, 0).
"""

import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from build123d import Circle, ExportDXF, Face, Pos, Unit, Vector, Wire

from .case import Section, kle_rect, plate_rect, rounded, screw_points
from .params import Params

BUILD_DATA = Path(__file__).resolve().parents[2] / "body" / "build_data"
SVG_KEY_ORIGIN = 25.0  # swillkb: 5 mm sheet margin + 20 mm plate padding


@lru_cache
def type_a_cutouts(side: str) -> tuple[np.ndarray, ...]:
    """Switch/stab cutout polygons from Type A's plate, in KLE mm (x right, y down)."""
    svg = (BUILD_DATA / f"{side}_switch.svg").read_text()
    polys = [
        np.array([list(map(float, pt.split(","))) for pt in pts.split()]) - SVG_KEY_ORIGIN
        for pts in re.findall(r'<polygon points="([^"]+)"', svg)
    ]
    polys.sort(key=lambda q: -np.ptp(q[:, 0]) * np.ptp(q[:, 1]))
    plate_outline, rest = polys[0], polys[1:]
    return tuple(q for q in rest if not (np.ptp(q[:, 0]) < 7 and np.ptp(q[:, 1]) < 7))  # drop 6 mm holes


def _face(points: np.ndarray) -> Face:
    return Face(Wire.make_polygon([Vector(x, -y) for x, y in points], close=True))


def section_cutouts(sec: Section) -> list[np.ndarray]:
    side = "left" if sec.half == "left" else "right"
    return [q for q in type_a_cutouts(side) if sec.u0 <= q[:, 0].mean() <= sec.u1]


def plate(sec: Section, p: Params) -> Face:
    # corners rounded to fit the cavity's rounded corners
    face = rounded(kle_rect(*plate_rect(sec, p)), plate_corner_r(p), lambda v: True).faces()[0]
    for q in section_cutouts(sec):
        face -= _face(q)
    for u, v in screw_points(sec, p):
        face -= Pos(u, -v) * Circle(p.plate_hole_d / 2)
    return face


def plate_corner_r(p: Params) -> float:
    return max(0.5, p.cavity_corner_r - p.plate_clearance)


def export_dxf(face: Face, path: Path) -> None:
    dxf = ExportDXF(unit=Unit.MM)
    dxf.add_layer("plate")
    dxf.add_shape(face, layer="plate")
    dxf.write(path)
