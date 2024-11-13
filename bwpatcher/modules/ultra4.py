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


class Ultra4Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    def dashboard_max_speed(self, speed: float):
        assert 1.0 <= speed <= 29.6, "Speed must be between 1.0 and 29.6km/h"
        speed = int(speed/2*10)

        sig = [0x3b, 0x49, 0x0a, 0x88, 0x08, 0x3a, 0x90, 0x42, 0x04, 0xdd]
        ofs = find_pattern(self.data, sig)
        if_asm = f"""
        MOVS R1,#{speed}
        LSLS R1,R1,#0x1
        CMP R0,R1
        BLE #0xe
        MOV R0,R1
        NOP; NOP; NOP; NOP; NOP;
        """
        post_if = self.assembly(if_asm)
        assert len(post_if) == 20, "wrong length of post bytes"
        pre = self.data[ofs:ofs+len(post_if)]
        self.data[ofs:ofs+len(post_if)] = post_if
        return [("dashboard_max_speed", hex(ofs), pre.hex(), post_if.hex())]