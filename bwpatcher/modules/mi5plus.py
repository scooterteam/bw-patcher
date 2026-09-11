#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Xiaomi 5 Plus
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

from typing import Dict, List, Optional, Tuple

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern, SignatureException


class Mi5plusPatcher(CorePatcher):
    NAME = "Xiaomi Electric Scooter 5 Plus"

    MODE_PEDESTRIAN = 1
    MODE_DRIVE = 2
    MODE_SPORT = 3
    MODE_ORDER = ("ped", "drive", "sport")

    SRAM_RIDE_MODE = 0x20000218
    SRAM_UART_MAX_SPEED = 0x20000234

    SIG_UART20_MAX_SPEED_STORE = [
        0xAB, 0x49,
        0x78, 0x7A,
        0x08, 0x80,
    ]
    HIJACK_SIZE = 4
    HIJACK_OFFSET_IN_SIG = 2

    INJECT_SEARCH_START = 0x1C000
    PADDING_SAFETY_MARGIN = 8
    MIN_PADDING_SIZE = 48

    REGION_PREFIX_DE = bytes.fromhex("b7020100")
    REGION_PREFIX_ES = bytes.fromhex("b6020100")

    def __init__(self, data: bytes):
        super().__init__(data)
        if len(self.data) < 0x6000:
            raise ValueError("5 Plus image too short")

        self.patched_speeds: Dict[str, int] = {}
        self._speed_block_patched = False
        self._hijack_offset: Optional[int] = None
        self._inject_offset: Optional[int] = None
        self._return_address: Optional[int] = None

    @classmethod
    def _clamp_kmh(cls, kmh: float) -> int:
        v = int(round(kmh))
        if v < 1 or v > 255:
            raise ValueError(f"km/h must be 1..255 for UART max-speed halfword, got {kmh}")
        return v

    def _find_uart20_max_speed_store(self) -> int:
        return find_pattern(self.data, self.SIG_UART20_MAX_SPEED_STORE)

    def _find_inject_padding(self, min_size: int) -> int:
        zero_sig = [0x00] * min_size
        try:
            pad_ofs = find_pattern(
                self.data, zero_sig, start=self.INJECT_SEARCH_START
            )
        except SignatureException as exc:
            raise Exception(
                f"No {min_size}-byte zero padding after 0x{self.INJECT_SEARCH_START:X}"
            ) from exc

        if pad_ofs & 1:
            pad_ofs += 1
        return pad_ofs

    def _locate_patch_offsets(self) -> None:
        if self._hijack_offset is not None:
            return

        sig_ofs = self._find_uart20_max_speed_store()
        self._hijack_offset = sig_ofs + self.HIJACK_OFFSET_IN_SIG
        self._return_address = self._hijack_offset + self.HIJACK_SIZE

        need = self.MIN_PADDING_SIZE + self.PADDING_SAFETY_MARGIN
        pad_ofs = self._find_inject_padding(need)
        self._inject_offset = pad_ofs + self.PADDING_SAFETY_MARGIN
        if self._inject_offset & 1:
            self._inject_offset += 1

    def _apply_hijack_patch(self) -> Tuple[str, str, str, str]:
        assert self._hijack_offset is not None
        assert self._inject_offset is not None

        stock = self.SIG_UART20_MAX_SPEED_STORE[
            self.HIJACK_OFFSET_IN_SIG : self.HIJACK_OFFSET_IN_SIG + self.HIJACK_SIZE
        ]
        pre = bytes(self.data[self._hijack_offset:self._hijack_offset + self.HIJACK_SIZE])
        if pre != bytes(stock):
            raise Exception(
                f"Hijack site @0x{self._hijack_offset:X}: expected {bytes(stock).hex()}, "
                f"found {pre.hex()}"
            )

        branch = self.assembly(f"b.w {hex(self._inject_offset)}", self._hijack_offset)
        if len(branch) != 4:
            raise Exception(f"expected 4-byte b.w, got {branch.hex()}")
        self.data[self._hijack_offset:self._hijack_offset + 4] = branch
        return ("hijack_uart20_max_speed", hex(self._hijack_offset), pre.hex(), branch.hex())

    def _build_mode_check_asm(self) -> str:
        mode_map = {
            "ped": self.MODE_PEDESTRIAN,
            "drive": self.MODE_DRIVE,
            "sport": self.MODE_SPORT,
        }
        modes = [m for m in self.MODE_ORDER if m in self.patched_speeds]
        asm = ""
        for i, mode in enumerate(modes):
            nxt = (
                f"check_{modes[i + 1]}"
                if i + 1 < len(modes)
                else "default_case"
            )
            asm += f"""
            check_{mode}:
            cmp r0, #{mode_map[mode]}
            bne {nxt}
            movw r0, #{self.patched_speeds[mode]}
            b store
            """
        return asm

    def _build_speed_logic_asm(self) -> str:
        assert self._return_address is not None
        return f"""
        ldr r2, ={hex(self.SRAM_RIDE_MODE)}
        ldrb r0, [r2]
        and r0, r0, #3
        {self._build_mode_check_asm()}
        default_case:
        ldrb r0, [r7, #9]
        store:
        strh r0, [r1]
        b.w {hex(self._return_address)}
        """

    def _verify_inject_site(self, patch_bytes: bytes) -> None:
        assert self._inject_offset is not None
        need = len(patch_bytes) + self.PADDING_SAFETY_MARGIN
        region = self.data[self._inject_offset:self._inject_offset + need]
        if len(region) < need or any(b != 0 for b in region):
            raise Exception(
                f"Inject site @0x{self._inject_offset:X} lacks {need}-byte zero padding "
                f"(patch={len(patch_bytes)} + margin={self.PADDING_SAFETY_MARGIN})"
            )

    def _patch_speed_block(
        self,
        ped_kmh: Optional[float] = None,
        drive_kmh: Optional[float] = None,
        sport_kmh: Optional[float] = None,
    ) -> List[Tuple[str, str, str, str]]:
        if ped_kmh is not None:
            self.patched_speeds["ped"] = self._clamp_kmh(ped_kmh)
        if drive_kmh is not None:
            self.patched_speeds["drive"] = self._clamp_kmh(drive_kmh)
        if sport_kmh is not None:
            self.patched_speeds["sport"] = self._clamp_kmh(sport_kmh)
        if not self.patched_speeds:
            raise ValueError("no speed modes specified")

        results: List[Tuple[str, str, str, str]] = []

        if not self._speed_block_patched:
            self._locate_patch_offsets()
            results.append(self._apply_hijack_patch())

        assert self._inject_offset is not None
        asm = self._build_speed_logic_asm()
        patch_bytes = self.assembly(asm, self._inject_offset)

        if not self._speed_block_patched:
            self._verify_inject_site(patch_bytes)

        pre = self.data[self._inject_offset:self._inject_offset + len(patch_bytes)]
        self.data[self._inject_offset:self._inject_offset + len(patch_bytes)] = patch_bytes

        name = (
            "speed_logic_block"
            if not self._speed_block_patched
            else "speed_constants_updated"
        )
        results.append((name, hex(self._inject_offset), pre.hex(), patch_bytes.hex()))
        self._speed_block_patched = True
        return results

    def speed_limit_ped(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(ped_kmh=kmh)

    def speed_limit_drive(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(drive_kmh=kmh)

    def speed_limit_sport(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(sport_kmh=kmh)

    def remove_speed_limit_sport(self) -> List[Tuple[str, str, str, str]]:
        return self.speed_limit_sport(35.0)

    def region_free(self) -> List[Tuple[str, str, str, str]]:
        res: List[Tuple[str, str, str, str]] = []
        post = b"\x00\x00\x00\x00"

        for label, needle in (
            ("region_free_de_66231", self.REGION_PREFIX_DE),
            ("region_free_es_66230", self.REGION_PREFIX_ES),
        ):
            start = 0
            n = 0
            while True:
                try:
                    ofs = find_pattern(self.data, list(needle), start=start)
                except SignatureException:
                    break
                pre = bytes(self.data[ofs:ofs + 4])
                self.data[ofs:ofs + 4] = post
                res.append((f"{label}_{n}", hex(ofs), pre.hex(), post.hex()))
                n += 1
                start = ofs + 4

        if not res:
            raise SignatureException("no DE/ES region prefix immediates found")
        return res

    def fix_checksum(self, start_ofs=None) -> List[Tuple[str, str, str, str]]:
        return [("fix_checksum", "0x0", "skipped", "5plus_plaintext_full_image")]

    def create_full_image(self) -> List[Tuple[str, str, str, str]]:
        return [("create_full_image", "0x0", "N/A", "already_full_image")]
