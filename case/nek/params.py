"""All tunable dimensions for the Type B case, in millimetres and degrees.

Key positions and angles within each half are fixed by Type A and live in frames.py.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Params:
    # --- Layout changes from Type A ---
    nav_flat: bool = True  # split the media/nav/arrow block off the right half onto its own plate
    nav_tent: float = 0.0  # tent of that block (0 = rows level); Type A is 11.89°
    nav_split_u: float = 8.625  # KLE units: centre of the 0.25u gap between the main keys and the block
    close_gap: bool = True  # slide the halves together until the joint walls reach joint_wall

    # --- Plate (steel), screwed up into the case's top skin ---
    # Screws sit in a row along the F-row gap (widened to 6.1 mm in the Type B layouts so the skin
    # strip takes an M2 tap), beside the up arrow, and along a front frame below the bottom row. The
    # back, outer and spine edges have no screws, so their frame is minimal.
    plate_margin: float = 2.5  # frame past the key cells on the back, outer and spine edges
    plate_margin_front: float = 6.5  # front frame, holds a row of screws
    plate_hinge_clearance: float = 0.5  # gap between the main and nav plates at the fold
    plate_clearance: float = 0.5  # cavity grows past the plate
    screw_inset: float = 3.5  # front screw centres, below the key cells (keeps the tap ~1.7 mm from the opening)
    screw_spacing: float = 60.0  # maximum distance between plate screws along an edge
    plate_hole_d: float = 2.4  # M2 clearance hole in the plate
    tap_hole_d: float = 1.6  # M2 tap drill in aluminum
    tap_depth: float = 6.0  # blind tapped hole into the 10 mm skin

    # --- Case ---
    side_wall: float = 4.0  # case wall outside the plate cavity
    joint_wall: float = 2.0  # thinnest wall at the left/right joint (beside the bottom-panel recess)
    top_skin: float = 10.0  # plate top -> case top surface (keycap recess depth, Type A value)
    keycap_clearance: float = 1.0  # keycap opening grows past the 19.05 mm cells (Type A value)
    tool_r: float = 1.5  # minimum inside-corner radius (3 mm end mill)
    # Stack under the plate (sets the desk plane at the lowest PCB corner). Choc v2 is also plate
    # mounted, so only switch_plate_to_pcb (and plate_thickness) should change if we switch.
    switch_plate_to_pcb: float = 5.0  # MX: plate top -> PCB top
    plate_thickness: float = 1.5  # 304 stainless
    pcb_thickness: float = 1.2  # thinner than the usual 1.6
    under_pcb: float = 1.0  # flush-trimmed pins + solder; no hot-swap sockets; diodes on top
    panel_clearance: float = 0.5
    pcb_margin: float = 1.0  # PCB extends past the key cells (less at the nav fold)
    panel_thickness: float = 2.0  # acrylic
    panel_lip: float = 2.0  # bottom panel overlaps the cavity by this much
    corner_r: float = 5.0  # outer back corners
    cavity_corner_r: float = 3.0  # vertical corners of the plate cavity; plate corners match (minus clearance)
    hollow_spine: bool = True  # pocket the solid block between the halves from below

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
    def wall(self) -> float:
        """Key-cell edge -> outer case surface on the back and outer sides."""
        return self.plate_margin + self.plate_clearance + self.side_wall

    @property
    def wall_front(self) -> float:
        """Key-cell edge -> front of the half (where the wrist rest starts)."""
        return self.plate_margin_front + self.plate_clearance + self.side_wall

    @property
    def below_plate(self) -> float:
        """Plate top -> top of the bottom panel, under the PCB."""
        return self.switch_plate_to_pcb + self.pcb_thickness + self.under_pcb + self.panel_clearance

    @property
    def shell(self) -> float:
        return self.side_wall

    @property
    def pocket_depth(self) -> float:
        return self.neoprene_thickness - self.neoprene_proud


ALUMINUM = Params()
PRINT = replace(ALUMINUM, wrist_pieces=2, hollow_spine=False, hollow_wrist=False, tap_hole_d=1.8)  # M2 thread-forming

VARIANTS = {"aluminum": ALUMINUM, "print": PRINT}
