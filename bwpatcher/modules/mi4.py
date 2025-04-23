#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# You are free to:
# - Share — copy and redistribute the material in any medium or format
# - Adapt — remix, transform, and build upon the material
#
# Under the following terms:
# - Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
# - NonCommercial — You may not use the material for commercial purposes.
# - ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
#

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern


class Mi4Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    def dashboard_max_speed(self, speed: float):
        assert 1.0 <= speed <= 29.6, "Speed must be between 1.0 and 29.6km/h"
        speed = int(speed/2*10)
        sig = [0x01, 0x46, 0xF3, 0x39, 0x11, 0x29, 0x00, 0xD2, 0xFF, 0x20]
        ofs = find_pattern(self.data, sig)

        if_asm = f"""
        MOVS R1, #{speed}
        LSLS R1,R1,#0x1
        CMP R1,R0
        BCS 10
        MOVS R0, R1
        """
        post_if = self.assembly(if_asm)
        assert len(post_if) == 10, "wrong length of post bytes"
        pre = self.data[ofs:ofs+len(post_if)]
        self.data[ofs:ofs+len(post_if)] = post_if
        return [("dashboard_max_speed", hex(ofs), pre.hex(), post_if.hex())]

    def speed_limit_drive(self, kmh: float):
        assert 1.0 <= kmh <= 25.5, "Speed must be between 1.0 and 25.5km/h"
        speed = int(kmh*10)
        sig = [0xCA, 0x24, 0x04, 0x80, None, 0x4D, 0xB9, 0x21, 0xC5, 0x80]
        ofs = find_pattern(self.data, sig)

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f'MOVS R4, #{speed}')
        self.data[ofs:ofs+2] = post
        return [("speed_limit_drive", hex(ofs), pre.hex(), post.hex())]

    def remove_speed_limit_sport(self):
        sig = [0x5B, 0x68, 0x22, 0x4F, 0xDF, 0x19, 0x98, 0x23]
        ofs = find_pattern(self.data, sig)
        patch_asm = """
        NOP
        ldr r7, [pc, #0x88]
        NOP
        movs r3, #0x98
        NOP
        beq #0x16
        NOP; NOP
        cmp r7, #2
        bne #0x4a
        b #0x2a
        NOP
        movs r3, #0xff
        adds r3, #0xcd
        NOP; NOP; NOP; NOP
        movs r0, #0xa
        NOP
        """
        post = self.assembly(patch_asm)
        assert len(post) == 40, "wrong length of post bytes"
        pre = self.data[ofs:ofs+len(post)]
        self.data[ofs:ofs+len(post)] = post
        return [("sport_no_limit", hex(ofs), pre.hex(), post.hex())]
