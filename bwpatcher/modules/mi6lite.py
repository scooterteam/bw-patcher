#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Mi 6 Lite Module
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

from typing import List, Optional, Tuple

from bwpatcher.modules.leqi_speed import LeqiPaddingSpeedPatcher
from bwpatcher.utils import SignatureException, experimental, find_pattern


class Mi6litePatcher(LeqiPaddingSpeedPatcher):
    FIRMWARE_SIZE = 0xB000

    SIG_SPEED_CALC_ANCHOR = [
        0x48, 0x79, 0x54, 0x49,
        0x00, 0xEB, 0x80, 0x00,
        0x40, 0x00,
        0x08, 0x80,
    ]
    OUTPUT_PTR_LDR_OFFSET = 2

    SIG_REGION_LIMIT_ANCHOR_V1: List[Optional[int]] = [
        0x67, 0x4F,
        None, None, None, None, None, None,
        0xD1, 0x18, 0x0B, 0xD0, 0x01, 0x29, 0x0C, 0xD1, 0x06, 0xE0,
        0x01, 0x28, 0x04, 0xD0, 0xA0, 0xF5, 0x80, 0x71, 0x1F, 0x39,
        0x05, 0xD1, 0x01, 0xE0, 0xCF, 0x21, 0x01, 0xE0, 0x40, 0xF2,
        0x01, 0x11, 0x39, 0x80,
    ]
    SIG_REGION_LIMIT_ANCHOR = SIG_REGION_LIMIT_ANCHOR_V1

    REGION_CMP_BEQ_OFFSET = 4
    REGION_SKIP_BRANCH_OFFSET_V1 = 0x22
    REGION_MOVW_IMM_OFFSET_V1 = 0x26

    REGION_CMP_BEQ_STOCK = bytes([0x0C, 0xD0])
    REGION_CMP_BEQ_PATCH = bytes([0x0C, 0xE0])
    REGION_SKIP_BRANCH_STOCK = bytes([0x01, 0xE0])
    REGION_SKIP_BRANCH_PATCH = bytes([0x00, 0xBF])
    REGION_MOVW_IMM_STOCK_V1 = 0x01
    REGION_MOVW_IMM_PATCH = 0x5E

    SIG_REGION_LIMIT_ANCHOR_V2 = [
        0xDC, 0x21, 0x01, 0xE0, 0x40, 0xF2, 0x13, 0x11, 0x11, 0x80,
    ]
    REGION_SKIP_BRANCH_OFFSET_V2 = 2
    REGION_MOVW_IMM_OFFSET_V2 = 6
    REGION_MOVW_IMM_STOCK_V2 = 0x13

    SIG_MOTOR_START = [
        0x01, 0x80, 0x2D, 0x2D, 0xEF, 0xD3, 0x11, 0x70,
        0xF0, 0xBD, 0x1E, 0x2D, 0x07, 0xD2,
    ]

    def __init__(self, data: bytes):
        super().__init__(data)
        self._region_limit_sig_ofs: Optional[int] = None
        self._region_variant: Optional[str] = None

    def _resolve_region_limit_anchor(self) -> Tuple[int, str]:
        if self._region_limit_sig_ofs is not None:
            assert self._region_variant is not None
            return self._region_limit_sig_ofs, self._region_variant

        try:
            sig_ofs = find_pattern(self.data, self.SIG_REGION_LIMIT_ANCHOR_V1)
            self._region_limit_sig_ofs = sig_ofs
            self._region_variant = "v1"
            return sig_ofs, "v1"
        except SignatureException:
            pass

        try:
            sig_ofs = find_pattern(self.data, self.SIG_REGION_LIMIT_ANCHOR_V2)
            self._region_limit_sig_ofs = sig_ofs
            self._region_variant = "v2"
            return sig_ofs, "v2"
        except SignatureException:
            raise SignatureException("region limit anchor")

    def _patch_site(
        self,
        name: str,
        offset: int,
        stock: bytes,
        post: bytes,
    ) -> Optional[Tuple[str, str, str, str]]:
        pre = bytes(self.data[offset:offset + len(post)])
        if pre == post:
            return None
        if pre != stock:
            raise Exception(
                f"Region limit patch @0x{offset:X}: expected {stock.hex()}, found {pre.hex()}"
            )
        self.data[offset:offset + len(post)] = post
        return (name, hex(offset), pre.hex(), post.hex())

    def _apply_region_limit(self) -> List[Tuple[str, str, str, str]]:
        try:
            sig_ofs, variant = self._resolve_region_limit_anchor()
        except SignatureException:
            return []

        if variant == "v1":
            sites = [
                (
                    "region_limit_bypass",
                    sig_ofs + self.REGION_CMP_BEQ_OFFSET,
                    self.REGION_CMP_BEQ_STOCK,
                    self.REGION_CMP_BEQ_PATCH,
                ),
                (
                    "region_limit_nop",
                    sig_ofs + self.REGION_SKIP_BRANCH_OFFSET_V1,
                    self.REGION_SKIP_BRANCH_STOCK,
                    self.REGION_SKIP_BRANCH_PATCH,
                ),
                (
                    "region_limit_movw",
                    sig_ofs + self.REGION_MOVW_IMM_OFFSET_V1,
                    bytes([self.REGION_MOVW_IMM_STOCK_V1]),
                    bytes([self.REGION_MOVW_IMM_PATCH]),
                ),
            ]
        else:
            sites = [
                (
                    "region_limit_nop",
                    sig_ofs + self.REGION_SKIP_BRANCH_OFFSET_V2,
                    self.REGION_SKIP_BRANCH_STOCK,
                    self.REGION_SKIP_BRANCH_PATCH,
                ),
                (
                    "region_limit_movw",
                    sig_ofs + self.REGION_MOVW_IMM_OFFSET_V2,
                    bytes([self.REGION_MOVW_IMM_STOCK_V2]),
                    bytes([self.REGION_MOVW_IMM_PATCH]),
                ),
            ]

        results: List[Tuple[str, str, str, str]] = []
        for name, offset, stock, post in sites:
            patch = self._patch_site(name, offset, stock, post)
            if patch is not None:
                results.append(patch)
        return results

    def _speed_limit_fix(self) -> List[Tuple[str, str, str, str]]:
        return self._apply_region_limit()

    @experimental
    def motor_start_speed(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        results = []
        ofs_sig = find_pattern(self.data, self.SIG_MOTOR_START)

        speed = self._calc_speed(kmh, size=0) & 0xFF
        acquire = max(1, speed // 2) & 0xFF

        ofs = ofs_sig + 2
        pre = bytes([self.data[ofs]])
        post = bytes([speed])
        self.data[ofs] = speed
        results.append(("motor_start_speed_threshold", hex(ofs), pre.hex(), post.hex()))

        ofs = ofs_sig + 10
        pre = bytes([self.data[ofs]])
        post = bytes([acquire])
        self.data[ofs] = acquire
        results.append(("motor_start_speed_acquire", hex(ofs), pre.hex(), post.hex()))

        return results

    def _build_speed_logic_asm(self) -> str:
        assert self._return_address is not None
        assert self._output_ptr is not None
        reload_asm = """
        ldrb r0, [r1, #5]
        ldrb r2, [r1, #2]
        """
        return self._build_padding_speed_logic_asm(
            reload_asm=reload_asm,
            mode_reg="r2",
            speed_reg="r0",
            ptr_reg="r1",
            return_address=self._return_address,
            output_ptr=self._output_ptr,
        )
