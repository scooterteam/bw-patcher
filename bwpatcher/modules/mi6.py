#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Mi 6 Module
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

from typing import List, Optional, Tuple

from bwpatcher.modules.leqi_speed import LeqiPaddingSpeedPatcher
from bwpatcher.utils import SignatureException, experimental, find_pattern


class Mi6Patcher(LeqiPaddingSpeedPatcher):
    FIRMWARE_SIZE = 0xA800

    SIG_SPEED_CALC_ANCHOR_V1 = [
        0x98, 0xF8, 0x05, 0x20,
        0x4A, 0x4B,
        0x02, 0xEB, 0x82, 0x02,
        0x52, 0x00,
        0x1A, 0x80,
    ]
    SIG_SPEED_CALC_ANCHOR_V2 = [
        0x9C, 0xF8, 0x05, 0x00,
        0x49, 0x4A,
        0x00, 0xEB, 0x80, 0x00,
        0x40, 0x00,
        0x10, 0x80,
    ]
    SIG_SPEED_CALC_ANCHOR = SIG_SPEED_CALC_ANCHOR_V1
    OUTPUT_PTR_LDR_OFFSET = 4

    SIG_REGION_LIMIT_ANCHOR_V1: List[Optional[int]] = [
        0x82, 0x4B,
        None, None, None, None, None, None,
        0x67, 0xE0, 0xDF, 0xE8, 0x01, 0xF0, 0x10, 0x05, 0x03, 0x03,
        0x03, 0x00, 0xCF, 0x22, 0x01, 0xE0, 0x40, 0xF2, 0x01, 0x12,
        0x1A, 0x80,
    ]
    SIG_REGION_LIMIT_ANCHOR = SIG_REGION_LIMIT_ANCHOR_V1
    STOCK_REGION_LIMIT_GATE = bytes([0x05, 0x29, 0x0B, 0xD2, 0x00, 0xE0])

    REGION_JUMPTABLE_OFFSET = 0x0E
    REGION_JUMPTABLE_LEN = 5
    REGION_JUMPTABLE_STOCK = bytes([0x10, 0x05, 0x03, 0x03, 0x03])
    REGION_JUMPTABLE_PATCH = bytes([0x05] * REGION_JUMPTABLE_LEN)
    REGION_MOVW_IMM_OFFSET_V1 = 0x1A
    REGION_MOVW_IMM_STOCK_V1 = 0x01
    REGION_MOVW_IMM_PATCH = 0x5E

    SIG_REGION_LIMIT_ANCHOR_V2 = [
        0xDC, 0x20, 0x01, 0xE0, 0x40, 0xF2, 0x13, 0x10, 0x38, 0x80,
    ]
    REGION_SKIP_BRANCH_OFFSET_V2 = 2
    REGION_SKIP_BRANCH_STOCK = bytes([0x01, 0xE0])
    REGION_SKIP_BRANCH_PATCH = bytes([0x00, 0xBF])
    REGION_MOVW_IMM_OFFSET_V2 = 6
    REGION_MOVW_IMM_STOCK_V2 = 0x13

    SIG_MOTOR_START: List[Optional[int]] = [
        0x2D, 0x29, 0x3F, 0x78, None, 0x97, 0x03, 0xDD,
        0x01, 0x27, 0x89, 0xF8, 0x03, 0x70,
    ]
    SIG_MOTOR_START_RAMP: List[Optional[int]] = [
        0x96, 0x29, None, None, 0x1E, 0x29,
    ]
    SIG_MOTOR_START_RAMP_SUB = [0xA1, 0xF1, 0x1E, 0x05]

    def __init__(self, data: bytes):
        super().__init__(data)
        self._region_limit_sig_ofs: Optional[int] = None
        self._fw_variant: Optional[str] = None
        self._detect_variant()

    def _detect_variant(self) -> None:
        try:
            find_pattern(self.data, self.SIG_SPEED_CALC_ANCHOR_V1)
            self._fw_variant = "v1"
            self.SIG_SPEED_CALC_ANCHOR = self.SIG_SPEED_CALC_ANCHOR_V1
            return
        except SignatureException:
            pass

        try:
            find_pattern(self.data, self.SIG_SPEED_CALC_ANCHOR_V2)
            self._fw_variant = "v2"
            self.SIG_SPEED_CALC_ANCHOR = self.SIG_SPEED_CALC_ANCHOR_V2
            return
        except SignatureException:
            pass

        self._fw_variant = None
        self.SIG_SPEED_CALC_ANCHOR = self.SIG_SPEED_CALC_ANCHOR_V1

    def _resolve_region_limit_anchor(self) -> Tuple[int, str]:
        if self._region_limit_sig_ofs is not None:
            assert self._fw_variant is not None
            return self._region_limit_sig_ofs, self._fw_variant

        try:
            sig_ofs = find_pattern(self.data, self.SIG_REGION_LIMIT_ANCHOR_V1)
            self._region_limit_sig_ofs = sig_ofs
            return sig_ofs, "v1"
        except SignatureException:
            pass

        try:
            sig_ofs = find_pattern(self.data, self.SIG_REGION_LIMIT_ANCHOR_V2)
            self._region_limit_sig_ofs = sig_ofs
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
                    "region_limit_jumptable",
                    sig_ofs + self.REGION_JUMPTABLE_OFFSET,
                    self.REGION_JUMPTABLE_STOCK,
                    self.REGION_JUMPTABLE_PATCH,
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
        results: List[Tuple[str, str, str, str]] = []
        speed = self._calc_speed(kmh, size=0) & 0xFF

        ofs = find_pattern(self.data, self.SIG_MOTOR_START)
        pre = bytes([self.data[ofs]])
        post = bytes([speed])
        self.data[ofs] = speed
        results.append(("motor_start_speed_enable", hex(ofs), pre.hex(), post.hex()))

        ramp_ofs = find_pattern(self.data, self.SIG_MOTOR_START_RAMP)
        imm_ofs = ramp_ofs + 4
        pre = bytes([self.data[imm_ofs]])
        post = bytes([speed])
        self.data[imm_ofs] = speed
        results.append(("motor_start_speed_ramp", hex(imm_ofs), pre.hex(), post.hex()))

        sub_ofs = find_pattern(self.data, self.SIG_MOTOR_START_RAMP_SUB)
        imm_ofs = sub_ofs + 2
        pre = bytes([self.data[imm_ofs]])
        post = bytes([speed])
        self.data[imm_ofs] = speed
        results.append(("motor_start_speed_ramp_sub", hex(imm_ofs), pre.hex(), post.hex()))

        return results

    def _build_speed_logic_asm(self) -> str:
        assert self._return_address is not None
        assert self._output_ptr is not None
        if self._fw_variant == "v2":
            reload_asm = """
            ldrb.w r0, [ip, #5]
            ldrb.w r3, [ip, #2]
            """
            return self._build_padding_speed_logic_asm(
                reload_asm=reload_asm,
                mode_reg="r3",
                speed_reg="r0",
                ptr_reg="r2",
                return_address=self._return_address,
                output_ptr=self._output_ptr,
            )

        reload_asm = """
        ldrb.w r2, [r8, #5]
        ldrb.w r1, [r8, #2]
        """
        return self._build_padding_speed_logic_asm(
            reload_asm=reload_asm,
            mode_reg="r1",
            speed_reg="r2",
            ptr_reg="r3",
            return_address=self._return_address,
            output_ptr=self._output_ptr,
        )
