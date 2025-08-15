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

from bwpatcher.core_lks32 import LKS32Patcher
from bwpatcher.utils import find_pattern


class Mi4litePatcher(LKS32Patcher):
    def __init__(self, data):
        super().__init__(data)
        self.sig_branch_src = [0x27, 0x4b, 0xd7, 0x18, 0x0a, 0x22, 0x3b, 0x00]
        self.sig_branch_dst = [0x11, 0x48, 0x00, 0x21, 0x01, 0x70, 0x02, 0x22]

    def speed_limit_drive(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_dst, "speed_limit_fix", dst_offset=0)]
        sig = [0xCA, 0x24, 0x04, 0x80, None, 0x4D]

        ofs = find_pattern(self.data, sig)
        ofs_dst = find_pattern(self.data, self.sig_branch_src, start=ofs) + len(self.sig_branch_src) + 2

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_drive_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"ldr r4,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_drive", hex(ofs), pre.hex(), post.hex()))
        return ret

    def speed_limit_sport(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_dst, "speed_limit_fix", dst_offset=0)]
        sig = [0xfc, 0x23, 0x43, 0x80, 0x32, 0x23, 0x83, 0x81]

        ofs = find_pattern(self.data, sig)
        ofs_dst = find_pattern(self.data, self.sig_branch_src, start=ofs) + len(self.sig_branch_src) + 6

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_sport_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"ldr r3,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_sport", hex(ofs), pre.hex(), post.hex()))
        return ret

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)
