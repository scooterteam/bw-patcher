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


class Mi5Patcher(LKS32Patcher):
    def __init__(self, data):
        super().__init__(data)
        self.sig_branch_src = [0x59, 0x68, None, 0x4A, None, 0x3A, 0x91, 0x42]
        self.sig_branch_src_dst = [0xF5, 0x31, 0x41, 0x81, 0x70, 0xBD]

    def speed_limit_drive(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [None, 0x49, 0x41, 0x82, 0xcb, 0x25, 0x05, 0x80]
        sig_dst = [0x59, 0x68, None, 0x4A, None, 0x3A, 0x91, 0x42, None, None]

        ofs = find_pattern(self.data, sig) + 4
        ofs_dst = find_pattern(self.data, sig_dst, start=ofs) + len(sig_dst)

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh*10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs+4]
        self.data[speed_ofs:speed_ofs+4] = speed
        ret.append(("speed_limit_drive_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"ldr r5,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs+2] = post
        ret.append(("speed_limit_drive", hex(ofs), pre.hex(), post.hex()))
        return ret

    def speed_limit_sport(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [0xfd, 0x21, 0x41, 0x80, None, 0x49, 0x81, 0x61]
        sig_dst = [0x59, 0x68, None, 0x4A, None, 0x3A, 0x91, 0x42, None, None]

        ofs = find_pattern(self.data, sig)
        ofs_dst = find_pattern(self.data, sig_dst, start=ofs) + len(sig_dst) + 4

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh*10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs+4]
        self.data[speed_ofs:speed_ofs+4] = speed
        ret.append(("speed_limit_sport_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"ldr r1,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs+2] = post
        ret.append(("speed_limit_sport", hex(ofs), pre.hex(), post.hex()))
        return ret

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)
