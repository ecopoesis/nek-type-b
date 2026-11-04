"""Where each keyboard half's keys are in space. These values are measured from Type A as machined.

Type A's body.py specifies tent 10°, split 25° and slope -10°, but CadQuery's rotation composition and
its non-orthogonal `CoordPlane` produced somewhat different real angles, and the halves are not exact
mirror images (about 1° of yaw apart). The keyboard that was built, and is "perfect", is the one in
body/target/body.step, so the frames below are fitted to that STEP, not computed from the nominal angles.

`scripts/fit_type_a.py` re-derives them by fitting the 4 tapped plate-screw holes per half to swillkb's
plate SVG (exact orthonormal fit, residual < 1e-9). `tests/test_frames.py` checks them against the STEP.

Measured from the frames:
                       right    left
  tent (row drop)      11.89°   12.06°
  slope (toward user)   9.82°    9.78°   front/wrist edge HIGHER than the back
  plan-view row yaw     9.91°  -10.89°

Coordinates are Type A's world frame (mm). z is shifted later so B's desk plane is z = 0.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Frame:
    origin: np.ndarray  # KLE (0, 0), the back-left corner of the key area, on the plate's top face
    ex: np.ndarray  # KLE +x, along the rows (left to right)
    ey: np.ndarray  # KLE +y, down the columns, toward the user

    @property
    def up(self) -> np.ndarray:
        """Plate normal, pointing away from the desk."""
        return np.cross(self.ey, self.ex)

    def point(self, x: float, y: float, z: float = 0.0) -> np.ndarray:
        """KLE-style mm coordinates (y toward the user, z up off the plate top) -> world."""
        return self.origin + x * self.ex + y * self.ey + z * self.up


TYPE_A = {
    "left": Frame(
        origin=np.array([-167.739503228, -4.600015945, 81.147367884]),
        ex=np.array([0.960328037, -0.184743485, 0.208901665]),
        ey=np.array([-0.221680154, -0.960202261, 0.169910349]),
    ),
    "right": Frame(
        origin=np.array([39.209706156, -29.903936987, 109.121016486]),
        ex=np.array([0.963939349, 0.168444288, -0.206027799]),
        ey=np.array([0.204867162, -0.963824376, 0.170505186]),
    ),
}


# Between the halves, Type A's top is a third plane (slope only, no tent). It meets each half's top
# plane along that half's pivot line, 35 mm inside the inner key edge, within 0.15 mm. Measured from
# the STEP (the largest face with this normal).
TYPE_A_CENTER_NORMAL = np.array([0.0, 0.173648178, 0.984807753])  # (0, sin 10°, cos 10°)
TYPE_A_CENTER_POINT = np.array([-1.3818, -155.897, 147.4888])
TYPE_A_PIVOT_INSET = 35.0  # pivot line, inward of each half's inner key edge
