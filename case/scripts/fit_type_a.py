"""Recover Type A's key frames from its machined STEP (body/target/body.step).

For each half, the 4 tapped plate-screw holes are intersected with the plate pocket ceiling and fitted
to the hole centres in swillkb's plate SVG (an exact orthonormal fit). The hole pattern is a rectangle,
so the fit is ambiguous up to 180°; the orientation with KLE +x running left-to-right (+world x) and
KLE +y running toward the user (-world y) is the physical one. This was confirmed by mapping Type A's
top skin openings against the layout.

    uv run python scripts/fit_type_a.py      # prints the constants used in nek/frames.py
"""

import itertools
import re
from pathlib import Path

import numpy as np
from build123d import GeomType, import_step

ROOT = Path(__file__).resolve().parents[2]
SVG_KEY_ORIGIN = 25.0  # swillkb: 5 mm sheet margin + 20 mm plate padding
HOLES = {"left": [1, 2, 6, 7], "right": [1, 2, 9, 10]}  # plate-screw hole polygons in *_top.svg

V = lambda v: np.array([v.X, v.Y, v.Z])  # noqa: E731


def svg_shapes(name):
    s = (ROOT / "body" / "build_data" / f"{name}.svg").read_text()
    return [
        np.array([list(map(float, p.split(","))) for p in pts.split()])
        for pts in re.findall(r'<polygon points="([^"]+)"', s)
    ]


def main():
    body = import_step(ROOT / "body" / "target" / "body.step").solids()[0]
    planes = [f for f in body.faces() if f.geom_type == GeomType.PLANE]
    holes = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.CYLINDER and abs(f.radius - 2.1) < 0.05 and abs(f.axis_of_rotation.direction.Z) < 0.99
    ]
    for side, idx in HOLES.items():
        # group the tilted holes by axis direction; the side is decided by which way the axis leans in x
        axes = [h for h in holes if (h.axis_of_rotation.direction.X < 0) == (side == "right")]
        d = V(axes[0].axis_of_rotation.direction)
        ceiling = max([f for f in planes if np.allclose(V(f.normal_at()), d, atol=1e-3)], key=lambda f: f.area)
        c = V(ceiling.center())
        pts = []
        for h in axes:
            p0 = V(h.axis_of_rotation.position)
            pts.append(p0 + np.dot(c - p0, d) / np.dot(d, d) * d)

        shapes = svg_shapes(f"{side}_top")
        centres = [((shapes[i][:, 0].min() + shapes[i][:, 0].max()) / 2, (shapes[i][:, 1].min() + shapes[i][:, 1].max()) / 2) for i in idx]
        S = np.array([[x - SVG_KEY_ORIGIN, y - SVG_KEY_ORIGIN, 1.0] for x, y in centres])
        fits = []
        for perm in itertools.permutations(range(4)):
            W = np.array([pts[i] for i in perm])
            M = np.linalg.lstsq(S, W, rcond=None)[0]
            ex, ey, origin = M
            resid = np.linalg.norm(S @ M - W)
            rigid = abs(np.linalg.norm(ex) - 1) < 1e-6 and abs(np.linalg.norm(ey) - 1) < 1e-6 and abs(ex @ ey) < 1e-6
            physical = ex[0] > 0 and ey[1] < 0
            if resid < 1e-6 and rigid and physical:
                fits.append((ex, ey, origin))
        assert len(fits) == 1, f"{side}: {len(fits)} candidate frames"
        ex, ey, origin = fits[0]
        print(f'    "{side}": Frame(')
        print(f"        origin=np.array({np.array2string(origin, precision=9, separator=', ')}),")
        print(f"        ex=np.array({np.array2string(ex, precision=9, separator=', ')}),")
        print(f"        ey=np.array({np.array2string(ey, precision=9, separator=', ')}),")
        print("    ),")


if __name__ == "__main__":
    main()
