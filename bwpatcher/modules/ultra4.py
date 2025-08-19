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


class Ultra4Patcher(LKS32Patcher):
    def __init__(self, data):
        super().__init__(data)
        self.sig_branch_src = [0xCB, 0x73, None, None, 0x03, 0x80, None, None, 0x41, 0x80]
        self.sig_branch_src_dst = [0x45, 0x81, 0x85, 0x81, None, 0x48]

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

    def motor_start_speed(self, speed: int):
        assert 1 <= speed <= 9, "Speed must be between 1 and 9km/h"
        kmh = round(-0.36*speed**2-5.39*speed+68.6)*3

        sig = [0x16, 0xE0, None, 0x88, 0x49, None, None, 0x00, None, 0x42, 0x11, 0xD2]
        ofs = find_pattern(self.data, sig) + 4

        b = self.data[ofs+1]
        if b == 0x25:  # 0015
            reg = 5
        elif b == 0x26:  # 0016, 0017 etc.
            reg = 6
        else:
            raise Exception(f"Invalid firmware file: {hex(b)}")

        post = self.assembly(f"movs r{reg}, #{kmh}")
        assert len(post) == 2, "wrong length of post bytes"
        pre = self.data[ofs:ofs+2]
        self.data[ofs:ofs+2] = post
        return [("motor_start_speed", hex(ofs), pre.hex(), post.hex())]

    def speed_limit_drive(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [0x0F, 0x23, 0xCB, 0x73, 0xCA, 0x23, 0x03, 0x80]
        sig_dst = self.sig_branch_src + [None, None]

        ofs = find_pattern(self.data, sig) + 4
        ofs_dst = find_pattern(self.data, sig_dst, start=ofs-4) + len(sig_dst)

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_drive_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"ldr r3,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_drive", hex(ofs), pre.hex(), post.hex()))
        return ret

    def speed_limit_sport(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [0x0F, 0x23, 0xCB, 0x73, None, None, 0x03, 0x80, 0xFC, 0x21, 0x41, 0x80]

        ofs = find_pattern(self.data, sig) + 8
        ofs_dst = find_pattern(self.data, self.sig_branch_src, start=ofs-8) + len(self.sig_branch_src) + 6

        speed_ofs, ldr_ofs = self._safe_ldr(ofs, ofs_dst)
        speed = int(kmh*10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs+4]
        self.data[speed_ofs:speed_ofs+4] = speed
        ret.append(("speed_limit_sport_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"ldr r3,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs+2] = post
        ret.append(("speed_limit_sport", hex(ofs), pre.hex(), post.hex()))
        return ret

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)
