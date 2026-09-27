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
from bwpatcher.utils import experimental, find_pattern


CURRENT_PER_SPEED = 3
CURRENT_SOFT_CAP = 1000


class Ultra4Patcher(LKS32Patcher):
    def __init__(self, data):
        super().__init__(data)
        self.sig_branch_src = [0xCB, 0x73, None, None, 0x03, 0x80, None, None, 0x41, 0x80]
        self.sig_branch_src_dst = [0x45, 0x81, 0x85, 0x81, None, 0x48]
        self.sig_drive_current = [0xC1, 0x80, None, 0x4D, 0x05, 0x81]
        self.sig_sport_current = [0xB9, 0x21, 0x89, 0x00, 0x41, 0x81, 0x81, 0x81]

    def _branch_site(self):
        return find_pattern(self.data, self.sig_branch_src) + len(self.sig_branch_src)

    @staticmethod
    def _current_for_speed(kmh: float) -> int:
        return min(CURRENT_SOFT_CAP, round(kmh * 10 * CURRENT_PER_SPEED))

    def _patch_drive_current(self, kmh: float):
        ofs = find_pattern(self.data, self.sig_drive_current)
        ldr_ofs = ofs + 2
        imm = self.data[ldr_ofs]
        pc_base = (ldr_ofs + 4) & ~3
        pool = pc_base + imm * 4
        val = self._current_for_speed(kmh).to_bytes(4, byteorder="little")
        pre = self.data[pool:pool + 4]
        self.data[pool:pool + 4] = val
        return [("speed_limit_drive_current", hex(pool), pre.hex(), val.hex())]

    def _patch_sport_current(self, kmh: float):
        ofs = find_pattern(self.data, self.sig_sport_current)
        pool_ofs, ldr_imm = self._safe_ldr(ofs, self._branch_site() + 2 + 8)
        val = self._current_for_speed(kmh).to_bytes(4, byteorder="little")
        pre_pool = self.data[pool_ofs:pool_ofs + 4]
        self.data[pool_ofs:pool_ofs + 4] = val

        pre = self.data[ofs:ofs + 4]
        post = self.assembly(f"ldr r1,[pc, #{ldr_imm}]") + self.assembly("nop")
        assert len(post) == 4, "wrong length of sport current patch"
        self.data[ofs:ofs + 4] = post
        return [
            ("speed_limit_sport_current_value", hex(pool_ofs), pre_pool.hex(), val.hex()),
            ("speed_limit_sport_current", hex(ofs), pre.hex(), post.hex()),
        ]

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

    @experimental
    def speed_limit_drive(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [0xCA, 0x23, 0x03, 0x80]
        ofs = find_pattern(self.data, sig)
        speed_ofs, ldr_ofs = self._safe_ldr(ofs, self._branch_site() + 2)

        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_drive_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"ldr r3,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_drive", hex(ofs), pre.hex(), post.hex()))
        ret.extend(self._patch_drive_current(kmh))
        return ret

    @experimental
    def speed_limit_sport(self, kmh: float):
        ret = [self._branch_from_to(self.sig_branch_src, self.sig_branch_src_dst, "speed_limit_fix")]
        sig = [0xFC, 0x21, 0x41, 0x80]
        ofs = find_pattern(self.data, sig)
        speed_ofs, ldr_ofs = self._safe_ldr(ofs, self._branch_site() + 2 + 4)

        speed = int(kmh * 10).to_bytes(4, byteorder='little')
        pre = self.data[speed_ofs:speed_ofs + 4]
        self.data[speed_ofs:speed_ofs + 4] = speed
        ret.append(("speed_limit_sport_value", hex(speed_ofs), pre.hex(), speed.hex()))

        pre = self.data[ofs:ofs + 2]
        post = self.assembly(f"ldr r1,[pc, #{ldr_ofs}]")
        assert len(post) == 2, "Wrong length of post bytes"
        self.data[ofs:ofs + 2] = post
        ret.append(("speed_limit_sport", hex(ofs), pre.hex(), post.hex()))
        ret.extend(self._patch_sport_current(kmh))
        return ret

    @experimental
    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)
