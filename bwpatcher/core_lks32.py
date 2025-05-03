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


class LKS32MC07Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    def speed_limit_drive(self, kmh: float):
        assert 1.0 <= kmh <= 25.5, "Speed must be between 1.0 and 25.5km/h"
        speed = int(kmh*10)
        sig = [None, 0x49, 0x41, 0x82, 0xcb, 0x25, 0x05, 0x80]
        ofs = find_pattern(self.data, sig) + 4

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f'movs r5, #{speed}')
        self.data[ofs:ofs+2] = post
        return [("speed_limit_drive", hex(ofs), pre.hex(), post.hex())]

    def _remove_speed_limit_sport(self):
        sig = [0xfd, 0x21, 0x41, 0x80, None, 0x49, 0x81, 0x61]
        ofs = find_pattern(self.data, sig)
        pre = self.data[ofs:ofs+2]
        # sport limit := drive limit * 2
        post = self.assembly("lsls r1,r5,#0x1")
        self.data[ofs:ofs+2] = post
        return [("remove_sls", hex(ofs), pre.hex(), post.hex())]

    def _remove_speed_limit_sport_fix(self):
        sig = [None, 0x3a, 0x91, 0x42, None, 0xd0]
        sig_dst = [0xf5, 0x31, 0x41, 0x81, 0x70, 0xbd]

        ofs = find_pattern(self.data, sig) + 4
        ofs_dst = find_pattern(self.data, sig_dst) + 4

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"b {ofs_dst-ofs}")
        self.data[ofs:ofs+2] = post
        return [("remove_sls_fix", hex(ofs), pre.hex(), post.hex())]

    def remove_speed_limit_sport(self):
        res = [
            self._remove_speed_limit_sport(),
            self._remove_speed_limit_sport_fix(),
        ]

        return res
