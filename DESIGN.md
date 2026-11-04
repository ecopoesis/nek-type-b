# NEK Type B — Design

Type B keeps Type A's key layout and angles and rebuilds the electronics and case
to be simpler, smaller, thinner and cheaper to machine.

## Fixed constraints (carried from Type A)

These are not up for change. Key positions and angles are **measured from Type A's machined STEP**
(`body/target/body.step`), not taken from `body/body.py`'s nominal parameters. CadQuery's rotation
composition and its non-orthogonal `CoordPlane` made the real angles differ from the script's
10° / 25° / 10°, and the halves are not exact mirror images. The keyboard that was built is the one
that's "perfect", so B copies it exactly. See `case/nek/frames.py` and `case/scripts/fit_type_a.py`.

| Parameter | Right | Left | Notes |
|---|---|---|---|
| Layout | `right.kbd.json` | `left.kbd.json` | unchanged |
| Tent (drop along the rows) | 11.89° | 12.06° | script said 10° |
| Slope (rise toward the user) | 9.82° | 9.78° | **negative** slope: wrist edge is higher than the back |
| Row yaw in plan view | 9.91° | 10.89° | script said ±12.5° |
| Centre top | slope-only plane | | meets each half's plane 35 mm inside the inner keys |
| Stack | PCB / 1.5 mm 304 SS plate / 0.031" Buna-N gasket / unibody case | | works well, keep |
| Bottom | 0.118" clear acrylic access panel | | keep |
| Firmware | QMK | | keep |

## Goals vs Type A

| Type A | Type B |
|---|---|
| Feather + Bluetooth + battery (unused) | Wired only, USB-C native |
| USB-A→C panel-mount dongle | USB-C port on the controller, behind a case-wall pocket |
| 3 PCBs + ribbon cables (left, right, center w/ MCP23017) | 2 PCBs, one per half |
| ~35 lb solid CNC block, chopped from a 120 mm sweep | Three thin-wall shells |
| 20 mm plate padding + 15 mm case margin per side | 9 mm wall from the key cells |
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
- The desk plane is set by the stack under the lowest plate corner (the right half's outer back corner):
  `below_plate` (9.6 mm: switch, PCB, solder) + 3 mm acrylic. That is 5 mm higher than Type A's floor,
  so B is 5 mm thinner everywhere. Refine `below_plate` once the PCB stack is known.
- **Height is mostly geometry, not material.** With ~12° of tent and ~10° of negative slope, the plates
  rise ~66 mm from the right outer back corner to the inner front corners. The wrist rest continues the
  slope, so the centre front is the highest point (~113 mm, vs ~112 mm on Type A). The remaining knobs:
  `top_skin` (10 mm keycap recess), `below_plate`, `wrist_depth`, or giving the wrist rest a
  lower/flatter top (it's a separate piece now, so it doesn't have to continue the key planes).
- **Spine joint:** it isn't on the centreline. It sits 17 mm inside the right half's inner key edge, a
  position chosen so both halves fit the X1C (left 7.8 mm spare, right 5.5 mm). The left half carries
  the whole spine. The mating faces need locating pins (dowels) as well as magnets, so the angle can't
  shift or drift under typing loads.

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
| Left half (incl. spine) | 242.0 × 203.3 × 99.8 mm | 7.8 mm |
| Right half | 244.3 × 144.0 × 95.6 mm | 5.5 mm |
| Wrist rest, left | 229.3 × 230.0 × 113.8 mm | 19.8 mm |
| Wrist rest, right | 213.6 × 214.0 × 110.6 mm | 35.8 mm |

My first estimate here forgot the spine: the gap between the halves' inner keys is fixed at ~70 mm,
so a centreline joint makes the right half ~268 mm wide. Moving the joint toward the right keys fixed it.

The aluminum set is about 3.5 kg (7.6 lb) across three pieces, pocketed from below, vs ~12.5 kg for
Type A's body.

Rules:
- **Hard size limit:** both halves are within ~5–8 mm of the usable bed, so wall width and anything added
  to the outer walls are limited by the printer, not only by looks. `build.py` checks every printed part
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
