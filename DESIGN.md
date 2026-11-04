# NEK Type B — Design

Type B keeps Type A's key layout and angles and rebuilds the electronics and case
to be simpler, smaller, thinner and cheaper to machine.

## Fixed constraints (carried from Type A)

Key positions and angles *within each half* are **measured from Type A's machined STEP**
(`body/target/body.step`), not taken from `body/body.py`'s nominal parameters. CadQuery's rotation
composition and its non-orthogonal `CoordPlane` made the real angles differ from the script's
10° / 25° / 10°, and the halves are not exact mirror images. The keyboard that was built is the one
that's "perfect", so B copies it exactly. See `case/nek/frames.py` and `case/scripts/fit_type_a.py`.

Two deliberate changes from Type A (see Halves below): the halves are slid together, and the right
half's media/nav/arrow block is folded level.

| Parameter | Right | Left | Notes |
|---|---|---|---|
| Layout | `right.kbd.json` | `left.kbd.json` | unchanged |
| Tent (drop along the rows) | 11.89° | 12.06° | script said 10° |
| Slope (rise toward the user) | 9.82° | 9.78° | **negative** slope: wrist edge is higher than the back |
| Row yaw in plan view | 9.91° | 10.89° | script said ±12.5° |
| Centre top | slope-only plane | | meets each half's plane 35 mm inside the inner keys |
| Stack | PCB / 1.5 mm 304 SS plate / 0.031" Buna-N gasket / unibody case | | works well, keep (plate now a narrow frame) |
| Bottom | 0.118" clear acrylic access panel | | keep |
| Firmware | QMK | | keep |

## Goals vs Type A

| Type A | Type B |
|---|---|
| Feather + Bluetooth + battery (unused) | Wired only, USB-C native |
| USB-A→C panel-mount dongle | USB-C port on the controller, behind a case-wall pocket |
| 3 PCBs + ribbon cables (left, right, center w/ MCP23017) | 3 PCBs: left, right main, right nav (short link across the fold) |
| ~35 lb solid CNC block, chopped from a 120 mm sweep | Three thin-wall shells |
| 20 mm plate padding + 15 mm case margin per side | 11 mm wall from the key cells; 6.5 mm plate frame |
| Halves 79 mm apart at the inner back keys | 17.1 mm apart (split angle unchanged) |
| Tall feet (20 mm) | Low-profile or no feet |
| Eagle | KiCad |
| CadQuery | build123d (STEP export for CNC) |

## Architecture: three-piece case

```
        [ left half ]  ⟷  [ right half ]       ← magnets + locating pins at the spine
              \                 /
               [   wrist rest   ]              ← magnets, no electrical connection
```

### Halves
- Each half is its own CNC unibody: a thin-wall shell with a gasket-mounted plate and an acrylic bottom.
- **Closer together.** Each half slides straight inward (world x) without changing its angles, until
  the thinnest wall at the left/right joint is `joint_wall` (2 mm, beside the bottom-panel recess; 4 mm
  above it). The inner back keys go from 79 mm apart to 17.1 mm. The halves still splay at Type A's
  angle, so they're 67.9 mm apart at the front row, and the centre wedge is what's left of the gap. The
  joint sits ~7 mm inside the right half's inner keys. The left half carries the wedge.
- **Nav block folded level.** The media, ins/home/pgup, del/end/pgdn and arrow keys (KLE x ≥ 8.75u)
  are a separate section with their own plate, PCB and gasket. It's hinged in the 0.25u gap and rotated
  about the column direction so its rows are level (`nav_tent = 0`). It keeps the 9.8° slope. The
  right half's lowest plate corner was the nav block's outer back corner, so leveling it raises the desk
  plane 13.5 mm and lowers the whole keyboard by that much.
- The desk plane is set by the stack under the lowest plate corner (now the right main keys' outer back
  corner, at the fold): `below_plate` (9.6 mm: switch, PCB, solder) + 3 mm acrylic. Refine
  `below_plate` once the PCB stack is known.

| | Type A gap, nav tented | gap closed, nav tented | **gap closed, nav level** |
|---|---|---|---|
| Tallest point (wrist, centre front) | 115.1 mm | 115.1 mm | **101.5 mm** |
| Right outer-back edge | 20.5 mm | 20.5 mm | **21.7 mm** |
| Left outer-back edge | 38.7 mm | 38.7 mm | **25.0 mm** |
| Overall width | 501.9 mm | 440.0 mm | **441.0 mm** |
| Inner keys apart, back / front row | 78.9 / 129.7 mm | 17.1 / 67.9 mm | **17.1 / 67.9 mm** |
| Aluminum (pocketed) | 3.33 kg | 2.69 kg | **2.49 kg** |

- **Height is still mostly geometry.** ~12° of tent and ~10° of negative slope make the plates rise
  ~54 mm from the fold to the inner front keys, and the wrist rest continues the slope (it must keep
  the key angles). The remaining knobs: `top_skin` (10 mm keycap recess), `below_plate` and
  `wrist_depth`.
- **Plates** are a narrow frame (`case/out/plates/*.dxf`, 1.5 mm 304 stainless): Type A's exact
  switch/stab cutouts (MX with opening notches), a 6.5 mm frame on the back, front and outer edges with
  M2 screws at ≤ 60 mm, 2.5 mm on the spine edge (no screws, so the halves can sit close), and ~2.1 mm
  each side of the fold. Corners are rounded to match the cavity. The screws go up into blind tapped
  holes (M2, 6 mm) in the 10 mm top skin, ~1.7 mm from the keycap openings. Prints use M2
  thread-forming screws.
- **At the fold** the skin between the main and nav keycap openings is a 2.7 mm strip. Both openings'
  fold-side walls lean at the bisector of the two plates (~6° off each), so the strip keeps its width to
  the top surface and the keycaps still clear by ≥ 0.5 mm.
- **Spine joint:** mating faces need locating pins (dowels) as well as magnets, so the angle can't
  shift or drift under typing loads. The joint wall is only 2–4 mm at the back, but the left half's side
  thickens toward the front (the wedge), which is where magnets and pogo pins should go.

### Wrist rest
- Aluminum: **one piece** (planned). The model also supports a **two-piece** variant (left/right, split
  at the centerline with alignment pins and a magnet or screw joint). Prints always use two pieces, and
  the aluminum can use either. The split is a build-time option, not a separate model.
- Pocket for a ~0.5" (12.7 mm) neoprene insert. In the two-piece variant, the neoprene is either one
  piece bridging the seam or two pieces (decide after a test print).
- Its top surface continues Type A's three top planes, so it lines up with the halves exactly.
- The halves/wrist-rest boundary is a vertical cut 9 mm in front of each side's key area, which makes a
  chevron.
- Magnets to both halves. No electronics.

## Electronics

### Controller
- **RP2040 board in a Pro Micro footprint** (Sparkfun Pro Micro RP2040, Elite-Pi, etc.), **socketed** so a
  damaged board is a swap, not a rework. Type A has killed several controllers in daily use.
- One controller per half using QMK split. **Open question:** use controllers on both halves, or put a
  controller only on the USB half and drive the other half's matrix through the joint (needs more pins
  across the joint). The default is a controller per half: it's the standard QMK pattern and needs the
  fewest connections.
- Socket height adds to case thickness. Evaluate low-profile options (Mill-Max low-profile pins and
  sockets) against hotswap pin headers.

### Inter-half link
- Pogo pins at the spine joint: VCC, GND, plus 1–2 data lines (QMK serial half- or full-duplex).
  Probably 4 contacts, plus a spare.
- **One USB-C port, on the right half** (as on Type A). Only the right half's case wall has a port
  opening. The left controller's USB-C is enclosed and powered over the pogo pins. QMK master is fixed
  to the right half (`MASTER_RIGHT`).
- Both halves carry the same controller, so moving the port to the left later is a case and firmware
  change only, with no PCB change.

### ESD / robustness
Type A has a history of dead controllers. Type B adds new exposed paths (pogo contacts) and keeps the
large metal case, so:
- TVS / ESD protection on the pogo-pin lines on both halves.
- Bond the aluminum case to GND, either directly or through a bleed resistor with a parallel cap, via a
  screw contact, so a touch on the case doesn't discharge into the matrix.
- Series resistors on the inter-half data lines.
- Keep the USB-C shield connection intact (the controller boards handle USB-C themselves).

## Printability (Bambu X1C)

Every part must be printable on an X1C (256 × 256 × 256 mm build volume) so the full keyboard can be
prototyped and used in plastic before it is machined in aluminum.

Current build (`cd case && uv run python build.py`), printed bottom-down at the best rotation:

| Part | Footprint × height | Spare to usable bed (250 mm) |
|---|---|---|
| Left half (incl. centre wedge) | 194.4 × 194.2 × 86.9 mm | 55.4 mm |
| Right half (main + nav) | 238.1 × 148.5 × 81.6 mm | 11.7 mm |
| Wrist rest, left | 190.9 × 190.4 × 101.5 mm | 58.9 mm |
| Wrist rest, right | 207.2 × 207.0 × 96.2 mm | 42.6 mm |

The right half is the tight one: its keys are 224 mm wide.

The aluminum set is about 2.5 kg (5.5 lb) across three pieces, pocketed from below, vs ~12.5 kg for
Type A's body.

Rules:
- **Hard size limit:** the right half is within ~12 mm of the usable bed, so its wall width and anything
  added to its outer walls are limited by the printer, not only by looks. `build.py` checks every printed part
  (rotating to find the best fit) and fails if one doesn't fit.
- **Wrist rest:** prints use the two-piece variant (see Wrist rest above). Each piece must fit the bed.
- **One geometry for both:** printed and machined parts come from the same model. Printer-specific
  differences are build-time parameters:
  - Threads: heat-set inserts (print) instead of tapped holes (aluminum). Hole diameter is a parameter.
  - Magnets: press-fit pockets with a print tolerance offset (print) vs. glued pockets (aluminum).
  - Tolerance and clearance offsets for the plate, gasket, acrylic and pogo-pin bores.
- **Print orientation:** each half prints bottom-down. The floor/acrylic opening and the top switch
  opening shouldn't need support beyond simple bridges. Avoid overhangs steeper than 45° in the
  inner cavity, or add chamfers there.
- Avoid features that can only be machined (deep thin slots, undercuts that need support) unless they
  are optional or done differently in the print version.

## Toolchain

- **CAD:** build123d (Python) in `case/`. Produces STEP for CNC and STL for test prints. Key positions
  come from the `kbd.json` layouts directly (no swillkb step). See `case/README.md`.
- **PCB:** KiCad. Redraw rather than convert the Eagle files, since the circuit changes anyway (no
  MCP23017, no Feather). Consider generating the matrix placement from the `kbd.json` files.
- **Firmware:** QMK, a new keyboard definition for the RP2040 split.
- **Prototyping:** 3D-print the case pieces (PLA/PETG) on the X1C (see Printability) from the same STEP files before paying for
  aluminum, mainly to check the spine joint, the wrist-rest height match and pogo-pin alignment.

## Research list

- [ ] Magnets: size and grade (N52 discs?), pull force needed for the spine and the wrist rest,
      pocket depth vs. wall thickness, glued or press-fit.
- [ ] Pogo pins: spring-loaded pin and flat-target pairs (e.g. Mill-Max 0906/0907 series), stroke,
      current rating, magnetic pogo connectors as an all-in-one alternative.
- [ ] Locating pins: dowel size and fit for aluminum.
- [ ] Neoprene: 0.5" sheet (density/durometer, fabric-covered or bare), suppliers who water-jet or
      die-cut to a DXF, adhesive or press-fit into the pocket.
- [ ] Controller socket stack height options.
- [ ] CNC vendors and pricing for three smaller parts vs. Type A's single block.
- [ ] Feet: low-profile options that don't add height.

## Repo plan

- `body/` (CadQuery) and `eagle/` from Type A stay in git history for reference. Type B work goes in new
  directories (`case/` for build123d, `pcb/` for KiCad, `firmware/` for QMK).
- Keep `body/build_data/*.kbd.json` and the plate/switch DXF/SVGs. Regenerate the plate outlines with
  tighter padding.
