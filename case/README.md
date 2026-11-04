# NEK Type B case (build123d)

```bash
cd case
uv run python build.py            # both variants -> out/{aluminum,print}/*.step, *.stl, preview.png
                                  # and switch plates -> out/plates/*_plate.dxf, plates.png
uv run python build.py --variant print --no-export   # just the size / X1C-fit report
uv run pytest                     # geometry checks, including against Type A's STEP
```

| File | What |
|---|---|
| `nek/params.py` | every tunable dimension; `ALUMINUM` and `PRINT` variants |
| `nek/frames.py` | where the keys are in space, measured from Type A (do not edit by hand) |
| `nek/layout.py` | KLE JSON parser (`layouts/*.kbd.json`) |
| `nek/case.py` | the geometry: sections (left, right main, nav), halves, wrist rest, cut planes, cavities, screw holes, pockets |
| `nek/plates.py` | switch plates: Type A's cutouts in a narrow screw frame, exported as DXF |
| `nek/printability.py` | X1C bed-fit check (bottom-down, any rotation about Z) |
| `scripts/fit_type_a.py` | re-derives `frames.py` from `../body/target/body.step` |

Variants differ only in parameters: the print variant splits the wrist rest in two and leaves the spine
and wrist rest solid (infill instead of pockets).

Not modelled yet: magnets / dowels / pogo pins at the joints, USB-C port, controller placement, the
link between the right main and nav PCBs, gaskets, the acrylic panel's screws, edge fillets, feet.
