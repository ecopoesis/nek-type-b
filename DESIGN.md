# NEK Type B — Design

Type B keeps Type A's key layout and angles and rebuilds the electronics and case
to be simpler, smaller, thinner and cheaper to machine.

## Fixed constraints (carried from Type A)

These are not up for change. Values come from `body/body.py` and the
`*.kbd.json` layouts.

| Parameter | Value | Notes |
|---|---|---|
| Layout | `left.kbd.json`, `right.kbd.json` | unchanged |
| Tent | 10° | outer edges raised |
| Split | 25° | total angle between halves (±12.5° about Z) |
| Slope | 10° **negative** | front/wrist edge is higher than the back |
| Rotation order | tent (Y) + split (Z), then slope (X) | about the pivot where the halves meet at the back |
| Stack | PCB / 1.5 mm 304 SS plate / 0.031" Buna-N gasket / unibody case | works well, keep |
| Bottom | 0.118" clear acrylic access panel | keep |
| Firmware | QMK | keep |

## Goals vs Type A

| Type A | Type B |
|---|---|
| Feather + Bluetooth + battery (unused) | Wired only, USB-C native |
| USB-A→C panel-mount dongle | USB-C port on the controller, behind a case-wall pocket |
| 3 PCBs + ribbon cables (left, right, center w/ MCP23017) | 2 PCBs, one per half |
| ~35 lb solid CNC block, chopped from a 120 mm sweep | Three thin-wall shells |
| 20 mm plate padding + 15 mm case margin per side | ~6–8 mm wall from keycap edge |
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
- Since the slope is negative, removing the wrist rest from each half shortens the tilted plane and lowers
  the tall front edge by about `wrist × sin(10°)` ≈ 11 mm.
- The low (back) edge should be as thin as the stack allows. Target: switch + PCB + controller clearance
  + floor + acrylic. Measure this precisely once the PCB stack is known.
- **Spine joint:** the halves meet at the fixed 25°. The mating faces need locating pins (dowels) as well
  as magnets, so the angle can't shift or drift under typing loads.

### Wrist rest
- Aluminum: **one piece** (planned). The model also supports a **two-piece** variant (left/right, split
  at the centerline with alignment pins and a magnet or screw joint). Prints always use two pieces, and
  the aluminum can use either. The split is a build-time option, not a separate model.
- Pocket for a ~0.5" (12.7 mm) neoprene insert. In the two-piece variant, the neoprene is either one
  piece bridging the seam or two pieces (decide after a test print).
- Its top surface must line up with the keyboard halves' front edge (match the tent and slope there, or
  use a deliberate small step).
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

| Part | Key area | Est. outline (7 mm walls) | Status |
|---|---|---|---|
| Right half | 223.8 × 119 mm (11.75u × 6.25u) | ~238 × 133 mm | fits, ~18 mm spare in X |
| Left half | 133.4 × 119 mm (7u × 6.25u) | ~147 × 133 mm | fits |
| Wrist rest | spans both halves | ~400+ mm | **must split** |

Rules:
- **Hard size limit:** the right half's footprint, including spine-joint features and magnet bosses, must
  stay ≤ 250 mm in the bed plane. That leaves about 6 mm per side for walls and fillets beyond the
  current estimate, so wall width is constrained by the printer, not only by looks. The build123d code
  should assert each part's bounding box against the bed size so violations fail the build.
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

- **CAD:** build123d (Python). Produces STEP for CNC and STL for test prints. Port the geometry
  (rotations, plate outlines from the swillkb SVG/DXF) from `body/body.py`, but not its approach of
  sweeping and chopping a block.
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
