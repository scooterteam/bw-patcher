#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Mi 5 Elite Module
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

from typing import List, Tuple, Optional
from bwpatcher.modules.leqi_speed import LeqiSpeedPatcher
from bwpatcher.utils import find_pattern, SignatureException


class Mi5elitePatcher(LeqiSpeedPatcher):
    FIRMWARE_SIZE = 0x9880

    SIG_SPEED_LIMIT_HIJACK = [
        0x98, 0xf8, 0x05, 0x00, None, 0x49,
        0x00, 0xeb, 0x80, 0x00, 0x40, 0x00, 0x08, 0x80,
    ]

    SIG_SPEED_LIMIT_DST = [
        0xdf, 0xf8, None, 0x81, 0xa8, 0xf8, 0x00, 0x10, None, 0x49, 0x67, 0x45,
    ]

    SIG_MOTOR_START = [
        0x01, 0x80, 0x2D, 0x2B, 0xEF, 0xD3, 0x11, 0x70,
        0x70, 0xBD, 0x14, 0x33, 0x2D, 0x2B, 0x07, 0xD2
    ]

    def __init__(self, data: bytes):
        super().__init__(data)
        self._ldr_patch_offset: Optional[int] = None
        self._default_path_address: Optional[int] = None
        self._patched_path_address: Optional[int] = None
        self._ldr_r0_offset: Optional[int] = None
        self._ldr_r1_offset: Optional[int] = None

    def _locate_patch_offsets(self) -> None:
        try:
            self._ldr_patch_offset = find_pattern(self.data, self.SIG_SPEED_LIMIT_HIJACK)
        except SignatureException:
            raise Exception("Could not find speed limit signature for patching")

        try:
            self._inject_offset = (
                find_pattern(self.data, self.SIG_SPEED_LIMIT_DST) +
                len(self.SIG_SPEED_LIMIT_DST) + 2
            )
        except SignatureException:
            raise Exception("Could not find speed logic destination")

        self._default_path_address = self._ldr_patch_offset + 6
        self._patched_path_address = self._ldr_patch_offset + 12

        mode_data_addr = find_pattern(self.data, [0x8a, 0x01, 0x00, 0x20])
        ldr_r0_pc = (self._ldr_patch_offset + 4) & ~3
        self._ldr_r0_offset = mode_data_addr - ldr_r0_pc

        r1_data_addr = find_pattern(self.data, [0xa4, 0x01, 0x00, 0x20])
        ldr_r1_pc = (self._inject_offset + 4) & ~3
        self._ldr_r1_offset = r1_data_addr - ldr_r1_pc

    def _apply_hijack_patch(self) -> Tuple[str, str, str, str]:
        branch_asm = f"""
        ldr r0, [pc, #{self._ldr_r0_offset}]
        ldrb r0, [r0, #0]
        b {hex(self._inject_offset)}
        """
        branch_bytes = self.assembly(branch_asm, self._ldr_patch_offset)

        if len(branch_bytes) != 6:
            raise Exception(f"Branch patch must be 6 bytes, got {len(branch_bytes)}")

        pre_branch = self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6]
        self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6] = branch_bytes

        return ("branch_patch", hex(self._ldr_patch_offset), pre_branch.hex(), branch_bytes.hex())

    def _build_speed_logic_asm(self) -> str:
        asm_code = f"ldr r1, [pc, #{self._ldr_r1_offset}]\n"
        asm_code += self._build_mode_check_asm(
            "r0", "r0", hex(self._patched_path_address)
        )
        asm_code += f"""
        default_case:
        ldrb.w r0, [r8, #5]
        b {hex(self._default_path_address)}
        """
        return asm_code

    def _speed_limit_fix(self) -> List[Tuple[str, str, str, str]]:
        results = []

        try:
            ofs_sig = find_pattern(self.data, self.SIG_SPEED_LIMIT_DST)
        except SignatureException:
            return results

        ofs = ofs_sig + len(self.SIG_SPEED_LIMIT_DST)
        branch_target = ofs + 130
        branch_asm = f"b {hex(branch_target)}"
        post = self.assembly(branch_asm, ofs)

        pre = self.data[ofs:ofs + len(post)]
        if pre == post:
            return results

        self.data[ofs:ofs + len(post)] = post
        results.append(("speed_limit_fix", hex(ofs), pre.hex(), post.hex()))
        return results

    def motor_start_speed(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        results = []
        ofs_sig = find_pattern(self.data, self.SIG_MOTOR_START)

        speed = self._calc_speed(kmh, size=0)
        speed_hyst = speed // 2

        ofs = ofs_sig + 2
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_1", hex(ofs), pre.hex(), post.hex()))

        ofs = ofs_sig + 10
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed_hyst & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_hysteresis", hex(ofs), pre.hex(), post.hex()))

        ofs = ofs_sig + 12
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_2", hex(ofs), pre.hex(), post.hex()))

        return results
