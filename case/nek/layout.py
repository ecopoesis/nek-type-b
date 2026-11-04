"""Parse keyboard-layout-editor.com JSON into key cells.

Only the subset used by the NEK layouts is supported: x/y offsets and w/h sizes.
Rotation (r/rx/ry) is rejected rather than silently ignored.
"""

import json
from dataclasses import dataclass
from pathlib import Path

U = 19.05  # mm per key unit

LAYOUT_DIR = Path(__file__).resolve().parent.parent / "layouts"


@dataclass(frozen=True)
class Key:
    x: float  # units, from the layout's left edge
    y: float  # units, from the layout's top edge, increasing toward the user
    w: float
    h: float
    label: str

    @property
    def cell_mm(self) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) of the 1u-pitch cell in mm, y down."""
        return (self.x * U, self.y * U, (self.x + self.w) * U, (self.y + self.h) * U)

    @property
    def center_mm(self) -> tuple[float, float]:
        return ((self.x + self.w / 2) * U, (self.y + self.h / 2) * U)


def parse_kle(rows: list) -> list[Key]:
    keys: list[Key] = []
    y = 0.0
    for row in rows:
        if isinstance(row, dict):  # keyboard metadata
            continue
        x = 0.0
        w = h = 1.0
        for item in row:
            if isinstance(item, dict):
                if {"r", "rx", "ry"} & item.keys():
                    raise ValueError("rotated keys are not supported")
                x += item.get("x", 0.0)
                y += item.get("y", 0.0)
                w = item.get("w", w)
                h = item.get("h", h)
            else:
                keys.append(Key(x, y, w, h, item))
                x += w
                w = h = 1.0
        y += 1.0
    return keys


def load(side: str) -> list[Key]:
    return parse_kle(json.loads((LAYOUT_DIR / f"{side}.kbd.json").read_text()))


def extent_mm(keys: list[Key]) -> tuple[float, float]:
    """(width, depth) of the key area in mm. Layouts start at 0,0."""
    return (max(k.cell_mm[2] for k in keys), max(k.cell_mm[3] for k in keys))
