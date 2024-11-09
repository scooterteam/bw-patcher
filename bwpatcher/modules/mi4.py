#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024 ScooterTeam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
        post_if = bytes(self.ks.asm(if_asm)[0])
        assert len(post_if) == 10, "wrong length of post bytes"
        pre = self.data[ofs:ofs+len(post_if)]
        self.data[ofs:ofs+len(post_if)] = post_if
        return [("dashboard_max_speed", hex(ofs), pre.hex(), post_if.hex())]

    def speed_limit_drive(self, kmh: float):
        assert 1.0 <= kmh <= 25.5, "Speed must be between 1.0 and 25.5km/h"
        speed = int(kmh*10)
        sig = [0x2C, 0x49, 0x41, 0x84, 0x49, 0x10, 0x01, 0x84]
        ofs = find_pattern(self.data, sig) + 0xC

        pre = self.data[ofs:ofs+2]
        post = bytes(self.assembly(f'MOVS R4, #{speed}')[0])
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
        post = bytes(self.ks.asm(patch_asm)[0])
        assert len(post) == 40, "wrong length of post bytes"
        pre = self.data[ofs:ofs+len(post)]
        self.data[ofs:ofs+len(post)] = post
        return [("sport_no_limit", hex(ofs), pre.hex(), post.hex())]