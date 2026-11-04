"""Does each part fit the printer bed, printed bottom-down? Rotation about Z is allowed."""

from dataclasses import dataclass

import numpy as np

from .params import Params


@dataclass(frozen=True)
class Fit:
    name: str
    fits: bool
    angle: float  # rotation about Z giving the best fit, degrees
    size: tuple[float, float, float]  # bed-plane x, y and height at that angle
    spare: float  # smallest remaining margin to the usable bed edge (negative = overhang)

    def __str__(self) -> str:
        x, y, z = self.size
        status = "fits" if self.fits else "DOES NOT FIT"
        return f"{self.name:12s} {status:12s} {x:6.1f} x {y:6.1f} x {z:6.1f} mm @ {self.angle:5.1f}°  spare {self.spare:6.1f} mm"


def _hull(points: np.ndarray) -> np.ndarray:
    pts = sorted(set(map(tuple, np.round(points, 4))))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def check(name: str, part, p: Params) -> Fit:
    deflection = 0.1
    verts, _ = part.tessellate(deflection, 0.2)
    v = np.array([[q.X, q.Y, q.Z] for q in verts])
    hull = _hull(v[:, :2])
    height = v[:, 2].max() - v[:, 2].min()
    usable = p.bed - 2 * p.bed_margin
    best = None
    for deg in np.arange(0.0, 180.0, 0.25):
        a = np.radians(deg)
        r = hull @ np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        x, y = np.ptp(r[:, 0]), np.ptp(r[:, 1])
        # the hull can sit up to `deflection` inside a curved edge, on both sides
        spare = min(usable - x, usable - y, p.bed - p.bed_margin - height) - 2 * deflection
        if best is None or spare > best[0]:
            best = (spare, deg, x, y)
    spare, deg, x, y = best
    return Fit(name, spare >= 0, float(deg), (float(x), float(y), float(height)), float(spare))
