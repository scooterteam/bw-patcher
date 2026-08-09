#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#

from bwpatcher.core_lks32 import LKS32Patcher
from bwpatcher.utils import find_pattern


class Mi3litePatcher(LKS32Patcher):
    """Patcher for the Mi 3 Lite LKS32 firmware layout."""

    # Match the comparison immediately before the region-specific branch.
    SIG_SPEED_LIMIT_FIX = [0xd3, 0x1b, 0xba, 0x42, None, 0xd0]

    # Each speed is stored as a byte in the mode configuration builder.
    SIG_SPORT_SPEED = [0xfc, 0x21, 0x01, 0x80]
    SIG_DRIVE_SPEED = [0x14, 0x23, 0x01, 0x46, 0x20, 0x31, 0x8b, 0x72]
    SIG_PED_SPEED = [0x0f, 0x26, 0xce, 0x72]

    def __init__(self, data):
        super().__init__(data)
        self._speed_limit_fixed = False

    def _speed_limit_fix(self):
        if self._speed_limit_fixed:
            return []

        sig_ofs = find_pattern(self.data, self.SIG_SPEED_LIMIT_FIX)
        ofs = sig_ofs + 4
        pre = self.data[ofs:ofs + 2]
        branch_offset = self.data[ofs]
        if branch_offset & 0x80:
            branch_offset -= 0x100
        branch_offset <<= 1
        target = ofs + 4 + branch_offset
        post = self.assembly(f"b {target - ofs}")
        assert len(post) == 2, "Wrong length of speed-limit branch"
        if pre != post:
            self.data[ofs:ofs + 2] = post
            self._speed_limit_fixed = True
            return [("speed_limit_fix", hex(ofs), pre.hex(), post.hex())]
        self._speed_limit_fixed = True
        return []

    def _patch_byte_speed(self, signature, register, kmh, name):
        speed = round(kmh * 10)
        if not 0 <= speed <= 0xff:
            raise ValueError("Mi 3 Lite speed must be between 0.0 and 25.5 km/h")

        ofs = find_pattern(self.data, signature)
        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"movs {register}, #{speed}")
        assert len(post) == 2, "Wrong length of speed instruction"
        self.data[ofs:ofs + 2] = post
        return [(name, hex(ofs), pre.hex(), post.hex())]

    def speed_limit_sport(self, kmh: float):
        ret = self._speed_limit_fix()
        ret.extend(self._patch_byte_speed(
            self.SIG_SPORT_SPEED, "r1", kmh, "speed_limit_sport"
        ))
        return ret

    def speed_limit_drive(self, kmh: float):
        ret = self._speed_limit_fix()
        ret.extend(self._patch_byte_speed(
            self.SIG_DRIVE_SPEED, "r3", kmh, "speed_limit_drive"
        ))
        return ret

    def speed_limit_ped(self, kmh: float):
        ret = self._speed_limit_fix()
        ret.extend(self._patch_byte_speed(
            self.SIG_PED_SPEED, "r6", kmh, "speed_limit_ped"
        ))
        return ret
