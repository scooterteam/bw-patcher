#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI wrapper for header-only model detection.

  poetry run python scripts/detect_model.py firmware.bin
  poetry run python -m bwpatcher detect firmware.bin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from bwpatcher.detect import detect_bytes, format_detection


def iter_bins(paths: Iterable[Path]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".bin":
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.bin")))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    files = iter_bins(args.paths)
    if not files:
        print("no .bin files found", file=sys.stderr)
        return 2

    results = []
    for f in files:
        try:
            data = f.read_bytes()
        except OSError as e:
            print(f"{f}: {e}", file=sys.stderr)
            continue
        det = detect_bytes(data, str(f))
        results.append(det)
        if not args.json:
            print(format_detection(det))
            print()

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
