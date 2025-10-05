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
from bwpatcher.utils import find_pattern, get_reg


class Mi4Patcher(LKS32Patcher):
    def __init__(self, data):
        super().__init__(data)
        self.sig_branch_src = [0x20, 0x31, None, 0x72, 0x0F, None, None, 0x72]
        self.sig_branch_dst = [0xF5, 0x31, 0x01, 0x83, 0x11, 0x48]
    
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
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_dst, "speed_limit_fix")]
        sig = [0xCA, None, None, 0x80, None, None, 0xB9, 0x21, None, 0x80]

        ofs = find_pattern(self.data, sig)
        ofs_dst = find_pattern(self.data, self.sig_branch_src, start=ofs) + len(self.sig_branch_src) + 2

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_drive_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        reg = get_reg(self.disassembly(pre), default="r4")
        post = self.assembly(f"ldr {reg},[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_drive", hex(ofs), pre.hex(), post.hex()))
        return ret

    def speed_limit_sport(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_dst, "speed_limit_fix")]
        sig = [0xFC, 0x21, 0x41, 0x80, 0x78, 0x21, 0x81, 0x81]

        ofs = find_pattern(self.data, sig)
        ofs_dst = find_pattern(self.data, self.sig_branch_src, start=ofs) + len(self.sig_branch_src) + 6

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_sport_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        reg = get_reg(self.disassembly(pre), default="r1")
        post = self.assembly(f"ldr {reg},[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_sport", hex(ofs), pre.hex(), post.hex()))
        return ret

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)
