#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

"""
CLI:

  python -m bwpatcher auto infile.bin outfile.bin patches
  python -m bwpatcher mi6 infile.bin outfile.bin patches
  python -m bwpatcher detect infile.bin [more.bin ...] [--json]
"""

import argparse
import json
import sys
from pathlib import Path

from bwpatcher.detect import (
    ModelDetectionError,
    detect_bytes,
    detect_model,
    format_detection,
)
from bwpatcher.modules import ALL_MODULES
from bwpatcher.utils import patch_map, patch_firmware, ExperimentalPatchError


def _cmd_detect(argv: list) -> int:
    parser = argparse.ArgumentParser(prog="bwpatcher detect")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = []
    for path in args.files:
        try:
            data = path.read_bytes()
        except OSError as e:
            print(f"{path}: {e}", file=sys.stderr)
            continue
        det = detect_bytes(data, str(path))
        results.append(det)
        if not args.json:
            print(format_detection(det))
            print()
    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    return 0


def _cmd_patch(argv: list) -> int:
    parser = argparse.ArgumentParser(prog="bwpatcher")
    parser.add_argument(
        "model",
        type=str.lower,
        choices=["auto", *ALL_MODULES],
        help="Scooter model, or 'auto' to detect from header",
    )
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument(
        "patches",
        type=str,
        help="Comma-separated patches. Choose from: " + ", ".join(patch_map.keys()),
    )
    parser.add_argument(
        "--experimental",
        action="store_true",
        help="Allow experimental patches",
    )
    args = parser.parse_args(argv)

    with open(args.infile, "rb") as fh:
        data = fh.read()

    model = args.model
    if model == "auto":
        try:
            model = detect_model(data)
        except ModelDetectionError as e:
            print(f"auto-detect failed: {e}", file=sys.stderr)
            print(format_detection(detect_bytes(data, args.infile)), file=sys.stderr)
            return 1
        print(f"Detected model: {model}")

    try:
        output_data = patch_firmware(
            model,
            data,
            args.patches.split(","),
            web=False,
            allow_experimental=args.experimental,
        )
    except ExperimentalPatchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    with open(args.outfile, "wb") as fh:
        fh.write(output_data)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "detect":
        return _cmd_detect(argv[1:])
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Models:", ", ".join(["auto", *ALL_MODULES]))
        print("Patches:", ", ".join(patch_map.keys()))
        return 0
    return _cmd_patch(argv)


if __name__ == "__main__":
    raise SystemExit(main())
