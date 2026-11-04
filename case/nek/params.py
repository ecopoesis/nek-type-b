"""All tunable dimensions for the Type B case, in millimetres.

Key positions and angles are not here: they are fixed by Type A and live in frames.py.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Params:
    # --- Case ---
    wall: float = 9.0  # key cell edge -> outer case surface (sides, back, front of halves)
    joint_offset: float = 17.0  # left/right joint, inward from the right inner key edge; balances X1C fit
    top_skin: float = 10.0  # plate top -> case top surface (keycap recess depth, Type A value)
    keycap_clearance: float = 1.0  # keycap opening grows past the 19.05 mm cells (Type A value)
    tool_r: float = 1.5  # minimum inside-corner radius (3 mm end mill)
    plate_margin: float = 3.0  # plate extends past the key cells
    plate_clearance: float = 0.5  # cavity grows past the plate
    below_plate: float = 9.6  # plate top -> top of bottom panel, at the plate's lowest corner
    panel_thickness: float = 3.0  # 0.118" acrylic
    panel_lip: float = 2.5  # bottom panel overlaps the cavity by this much
    corner_r: float = 5.0  # outer back corners
    cavity_corner_r: float = 3.0  # vertical corners of the plate cavity
    hollow_spine: bool = True  # hollow the solid block between the halves from below

    # Aluminum is pocketed from below to save weight. Prints stay solid (infill does the same job, and
    # an open underside would leave large unsupported roofs).

    # --- Wrist rest ---
    wrist_depth: float = 97.0  # key area front edge -> wrist rest front edge (Type A value)
    wrist_corner_r: float = 90.0  # outer front corners (Type A value)
    wrist_pieces: int = 1  # 1 or 2; prints always use 2
    neoprene_thickness: float = 12.7  # 0.5"
    neoprene_proud: float = 3.0  # how far the neoprene sits above the aluminum
    pad_rim: float = 6.0  # aluminum rim around the neoprene pocket
    pad_corner_r: float = 8.0
    hollow_wrist: bool = True
    wrist_shell: float = 4.0  # wall thickness of the hollowed wrist rest
    wrist_roof: float = 3.0  # material under the neoprene pocket floor

    # --- Printer (Bambu X1C) ---
    bed: float = 256.0
    bed_margin: float = 3.0

    @property
    def shell(self) -> float:
        """Wall thickness where a half is hollowed: the hollow lines up with the plate cavity."""
        return self.wall - self.plate_margin - self.plate_clearance

    @property
    def pocket_depth(self) -> float:
        return self.neoprene_thickness - self.neoprene_proud


ALUMINUM = Params()
PRINT = replace(ALUMINUM, wrist_pieces=2, hollow_spine=False, hollow_wrist=False)

VARIANTS = {"aluminum": ALUMINUM, "print": PRINT}
