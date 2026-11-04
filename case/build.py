"""Build the Type B case.

    uv run python build.py                      # both variants -> out/<variant>/*.step, *.stl, preview.png
    uv run python build.py --variant print      # one variant
    uv run python build.py --no-export          # report only

The print variant fails the build if any part does not fit the X1C bed.
"""

import argparse
import sys
from pathlib import Path

from build123d import export_step, export_stl

from nek.case import build
from nek.params import VARIANTS
from nek.printability import check
from nek.render import render

OUT = Path(__file__).resolve().parent / "out"
ALUMINUM_KG_PER_MM3 = 2.70e-6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    ok = True
    for variant in args.variant or sorted(VARIANTS):
        p = VARIANTS[variant]
        parts = build(p)
        print(f"\n== {variant}")
        total = 0.0
        for name, part in parts.items():
            if not part.is_valid:
                print(f"  {name}: INVALID SOLID")
                ok = False
            bb = part.bounding_box()
            kg = part.volume * ALUMINUM_KG_PER_MM3
            total += kg
            print(f"  {name:12s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm  {kg:5.2f} kg if aluminum")
        print(f"  {'total':12s} {total:5.2f} kg if aluminum")

        if variant == "print":
            print("  X1C fit (bottom-down, best rotation):")
            for name, part in parts.items():
                fit = check(name, part, p)
                print(f"    {fit}")
                ok &= fit.fits

        if not args.no_export:
            d = OUT / variant
            d.mkdir(parents=True, exist_ok=True)
            for name, part in parts.items():
                export_step(part, d / f"{name}.step")
                export_stl(part, d / f"{name}.stl", tolerance=0.05, angular_tolerance=0.2)
            if not args.no_render:
                render(parts, d / "preview.png", title=f"NEK Type B — {variant}")
            print(f"  wrote {d}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
