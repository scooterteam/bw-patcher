#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BW Patcher — header model detection
# Copyright (C) 2024-2026 ScooterTeam
# Licensed under CC BY-NC-SA 4.0

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from bwpatcher.modules import ALL_MODULES

HEADER_LEN = 0x80
LEQI_TAGS = (b"EU1\x00", b"BU1\x00")
MIN_BODY = 0x400

LEQI_PRODUCT = {
    0x0124: "mi5elite",
    0x012E: "mi6",
    0x0157: "mi5plus",
    0x008C: "mi6lite_or_6esstl",
}

LEQI_SIZE = {
    0x9800: "mi5elite",
    0x9880: "mi5elite",
    0xA800: "mi6",
    0xB000: "mi6lite",
    0x8C00: "mi5plus",
    0x6F00: "6esstl",
}

LEQI_FAMILY = {
    0x0101: "mi6",
    0x0201: "mi6lite_or_elite",
    0x0301: "mi5elite",
    0x0300: "mi5plus",
    0x0200: "6esstl",
}

BW_ID = {
    "001500010001": "mi5",
    "001600010001": "mi5max",
    "000700010001": "mi5pro",
    "001000010001": "mi4pro2nd",
    "000600010001": "mi4pro2nd",
    "001320122002": "t2201",
    "001720122010": "ultra4",
    "001820122010": "ultra4",
    "001920122010": "ultra4",
    "000920012001": "mi4lite",
    "001020012001": "mi4lite2",
    "001120012001": "mi4",
    "021622152185": "3lite",
    "021422142185": "3lite",
}

BW_ID_PREFIX4 = {
    "0007": "mi5pro",
    "0015": "mi5",
    "0016": "mi5max",
}

BWPATCHER_MODELS = frozenset(ALL_MODULES)

NON_PATCHER_LABELS = frozenset({
    "3lite", "6esstl", "6pro_or_6max", "mi4lite2", "t2201",
})

MIN_SCORE = 30


@dataclass
class Hit:
    model: str
    score: int
    reasons: List[str] = field(default_factory=list)


@dataclass
class Detection:
    size: int
    family: str
    container: str = "unknown"
    header: Optional[dict] = None
    best: Optional[str] = None
    ok: bool = False
    hits: List[Hit] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    bwpatcher: bool = False
    path: str = "<memory>"

    def to_dict(self):
        return asdict(self)


class ModelDetectionError(ValueError):
    pass


def _add(scores: dict, model: str, pts: int, reason: str) -> None:
    if not model:
        return
    hit = scores.setdefault(model, Hit(model=model, score=0, reasons=[]))
    hit.score += pts
    hit.reasons.append(f"+{pts} {reason}")


def _resolve(model: str, body_size: Optional[int]) -> str:
    if model == "mi6lite_or_6esstl":
        if body_size == 0x6F00:
            return "6esstl"
        if body_size == 0xB000:
            return "mi6lite"
        return model
    if model == "mi6lite_or_elite":
        if body_size in (0x9800, 0x9880):
            return "mi5elite"
        if body_size == 0xB000:
            return "mi6lite"
        return model
    return model


def _hdr(data: bytes) -> bytes:
    return data[:HEADER_LEN] if len(data) >= HEADER_LEN else data


def parse_leqi(hdr: bytes) -> Optional[dict]:
    if len(hdr) < 0x22:
        return None
    tag = hdr[0x0A:0x0E]
    if tag not in LEQI_TAGS:
        return None
    size = struct.unpack_from("<H", hdr, 0x0E)[0]
    if size < MIN_BODY:
        return None
    return {
        "tag": tag[:3].decode("ascii"),
        "body_size": size,
        "family_u16": struct.unpack_from("<H", hdr, 0x02)[0],
        "product_u16": (hdr[0x1C] << 8) | hdr[0x1D],
        "product_tail": hdr[0x1C:0x22].hex(),
        "prefix": hdr[:10].hex(),
        "eu2": hdr.find(b"EU2\x00") >= 0,
    }


def parse_bw_packaged(hdr: bytes) -> Optional[dict]:
    if len(hdr) < 0x2E:
        return None
    if hdr[0x0A:0x0E] in LEQI_TAGS:
        return None
    if hdr[0] == 2 and hdr[1] == 0 and hdr[2] == 0 and hdr[3] == 0:
        return None
    ver = hdr[0x12:0x16]
    ident = hdr[0x22:0x2E]
    if not ver.isdigit():
        return None
    if not all(48 <= b <= 57 for b in ident):
        return None
    return {
        "type": "packaged",
        "class_u16": struct.unpack_from("<H", hdr, 0)[0],
        "geom_u16": struct.unpack_from("<H", hdr, 2)[0],
        "size_class": struct.unpack_from("<H", hdr, 8)[0],
        "crc_u16": struct.unpack_from("<H", hdr, 0x0A)[0],
        "ver": ver.decode("ascii"),
        "id": ident.decode("ascii"),
        "prefix": hdr[:0x12].hex(),
    }


def parse_raw_markers(hdr: bytes) -> List[str]:
    tags = []
    for needle in (
        b"LKS32MC071CBT8FFP",
        b"LKS32MC071CBT8FF",
        b"LKS32MC081",
        b"SZMC-ES-ZM-0283M",
        b"SUNWODA",
        b"DEPRD5C",
        b"DEPRA3ES",
    ):
        if needle in hdr:
            i = hdr.find(needle)
            end = i + len(needle)
            while end < len(hdr) and 32 <= hdr[end] < 127:
                end += 1
            tags.append(hdr[i:end].decode("ascii", errors="replace"))
    return tags


def detect_bytes(data: bytes, path: str = "<memory>") -> Detection:
    det = Detection(path=path, size=len(data), family="unknown")
    scores: dict[str, Hit] = {}
    hdr = _hdr(data)

    leqi = parse_leqi(hdr)
    if leqi:
        det.family = "leqi"
        det.container = "eu1"
        det.header = {
            **leqi,
            "body_size": f"0x{leqi['body_size']:X}",
            "family_u16": f"0x{leqi['family_u16']:04X}",
            "product_u16": f"0x{leqi['product_u16']:04X}",
        }
        size = leqi["body_size"]

        alias = LEQI_PRODUCT.get(leqi["product_u16"])
        if alias:
            resolved = _resolve(alias, size)
            if "_or_" in resolved:
                for part in resolved.split("_or_"):
                    _add(scores, part, 20, f"product@0x1C=0x{leqi['product_u16']:04X} (ambiguous)")
            else:
                _add(scores, resolved, 50, f"product@0x1C=0x{leqi['product_u16']:04X}")

        sm = LEQI_SIZE.get(size)
        if sm:
            _add(scores, sm, 40, f"size@0x0E=0x{size:X}")

        fam_alias = LEQI_FAMILY.get(leqi["family_u16"])
        if fam_alias:
            fam = _resolve(fam_alias, size)
            if "_or_" in fam:
                for part in fam.split("_or_"):
                    _add(scores, part, 15, f"family@0x02=0x{leqi['family_u16']:04X} (ambiguous)")
            else:
                _add(scores, fam, 30, f"family@0x02=0x{leqi['family_u16']:04X}")

        if leqi["eu2"]:
            _add(scores, "mi6", 15, "EU2 tag in header")

        _finalize(det, scores)
        return det

    if len(hdr) >= 4 and hdr[0] == 2 and hdr[1] == 0 and hdr[2] == 0 and hdr[3] == 0:
        det.family = "brightway"
        det.container = "type2_map"
        det.header = {"type": "type2_map", "prefix": hdr[:0x10].hex()}
        _add(scores, "6pro_or_6max", 40, "Brightway type-2 map header")
        det.notes.append("Brightway type-2 map (6pro/6max/cross) — no bwpatcher module yet")
        _finalize(det, scores)
        return det

    bw = parse_bw_packaged(hdr)
    if bw:
        det.family = "brightway"
        det.container = "packaged"
        det.header = bw
        ident = bw["id"]
        if ident in BW_ID:
            _add(scores, BW_ID[ident], 50, f"id@0x22={ident}")
        else:
            p4 = ident[:4]
            if p4 in BW_ID_PREFIX4:
                _add(scores, BW_ID_PREFIX4[p4], 25, f"id@0x22 prefix {p4}…")
            det.notes.append(f"unknown id@0x22={ident}")

        _finalize(det, scores)
        return det

    markers = parse_raw_markers(hdr)
    if markers:
        det.family = "brightway"
        det.container = "raw"
        det.header = {"type": "raw_dump", "markers": markers}
        joined = " ".join(markers)
        if "LKS32MC071CBT8FFP" in joined:
            _add(scores, "mi5max", 40, "header LKS32MC071CBT8FFP")
        elif "LKS32MC071CBT8FF" in joined:
            _add(scores, "mi5", 35, "header LKS32MC071CBT8FF")
        if "LKS32MC081" in joined:
            _add(scores, "mi4", 15, "header LKS32MC081 (also ultra4)")
            _add(scores, "ultra4", 15, "header LKS32MC081 (also mi4)")
            det.notes.append("LKS32MC081 in header is ambiguous (mi4/Scooter 42 vs ultra4)")
        if "SZMC-ES-ZM-0283M" in joined:
            _add(scores, "mi4pro2nd", 15, "header SZMC-ES-ZM-0283M (also mi5pro)")
            _add(scores, "mi5pro", 15, "header SZMC-ES-ZM-0283M (also mi4pro2nd)")
            det.notes.append("SZMC-ES-ZM-0283M in header is ambiguous (mi4pro2nd vs mi5pro)")
        if "SUNWODA" in joined:
            _add(scores, "mi4lite", 20, "header SUNWODA")
        _finalize(det, scores)
        return det

    det.notes.append("no recognizable header in [0x00, 0x80)")
    return det


def _finalize(det: Detection, scores: dict) -> None:
    for k in list(scores):
        if k.startswith("mi6lite_or_") or k.endswith("_or_elite") or k.endswith("_or_6esstl"):
            del scores[k]

    hits = sorted(scores.values(), key=lambda h: h.score, reverse=True)
    det.hits = hits
    if not hits:
        return

    top = hits[0]
    tied = [h for h in hits if h.score == top.score]
    if len(tied) > 1:
        det.notes.append("tied: " + ", ".join(f"{h.model}={h.score}" for h in tied))
        return

    det.best = top.model
    det.bwpatcher = top.model in BWPATCHER_MODELS
    if (
        top.score >= MIN_SCORE
        and det.bwpatcher
        and top.model not in NON_PATCHER_LABELS
    ):
        det.ok = True
    elif top.model not in BWPATCHER_MODELS:
        det.notes.append(f"{top.model} is not a bwpatcher module")


def detect_model(data: bytes, *, require_patchable: bool = True) -> str:
    det = detect_bytes(data)
    if not det.ok or not det.best:
        raise ModelDetectionError(
            "could not identify model from header"
            + (f" ({'; '.join(det.notes)})" if det.notes else "")
        )
    if require_patchable and not det.bwpatcher:
        raise ModelDetectionError(
            f"detected {det.best} but it is not a supported bwpatcher model"
        )
    return det.best


def format_detection(det: Detection) -> str:
    lines = [f"{det.path}", f"  size={det.size}  family={det.family}  container={det.container}"]
    if det.header:
        lines.append(f"  header: {det.header}")
    label = det.best or "unknown"
    status = "ok" if det.ok else "not detected"
    lines.append(f"  => {label}  [{status}]")
    for h in det.hits[:5]:
        lines.append(f"     {h.model:14s} score={h.score:3d}  " + "; ".join(h.reasons[:4]))
    for n in det.notes:
        lines.append(f"  note: {n}")
    return "\n".join(lines)
