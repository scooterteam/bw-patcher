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

from bwpatcher.core_es32 import ES32Patcher
from bwpatcher.utils import find_pattern, extract_ldr_offset, offset_to_nearest_word, SignatureException


class S60Patcher(ES32Patcher):
    def __init__(self, data):
        super().__init__(data)
    
    def __remove_speed_check(self):
        sig = [ 0x14, 0x20, 0x38, 0x5e, 0x88, 0x42, 0xe2, 0xdd, 0xb9, 0x82 ]
        ofs = find_pattern(self.data, sig)
        pre = self.data[ofs:ofs+len(sig)]
        post = self.assembly("nop") * (len(sig) // 2)
        assert len(pre) == len(post)
        self.data[ofs:ofs+len(sig)] = post

        return [("remove_speed_check", hex(ofs), pre.hex(), post.hex())]

    def speed_limit_drive(self, speed):
        res = []
        
        sig = [ 0x5c, 0x4a, 0x12, 0x88, 0xea, 0xe7 ]
        ofs_ = find_pattern(self.data, sig)
        pre_ = self.data[ofs_:ofs_+2]

        ofs = ofs_ + 2
        pre = self.data[ofs:ofs+2]
        post = self.assembly("nop")
        self.data[ofs:ofs+2] = post
        res += [("speed_limit_drive_0", hex(ofs), pre.hex(), post.hex())]

        try:
            disasm = self.disassembly(pre_)
            ofs_ldr = extract_ldr_offset(disasm)
            ofs = offset_to_nearest_word(ofs_+ofs_ldr)
            pre = self.data[ofs:ofs+4]
            post = self._calc_speed(speed, size=4)
            self.data[ofs:ofs+4] = post
            res += [("speed_limit_drive_1", hex(ofs), pre.hex(), post.hex())]
        except:
            raise SignatureException("Pattern not found!")

        try:
            res += self.__remove_speed_check()
        except SignatureException:
            pass

        return res

    def speed_limit_sport(self, speed):
        res = []
        
        sig = [ 0x68, 0x48, 0x01, 0x2a, 0x17, 0xd0 ]
        ofs_ = find_pattern(self.data, sig)
        pre_ = self.data[ofs_:ofs_+2]

        dst_reg = 2
        sig = [ 0x02, 0x88, 0xe8, 0xe7, 0x1a, 0x78, 0x01, 0x2a ]
        ofs = find_pattern(self.data, sig)
        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"mov r{dst_reg},r0")
        self.data[ofs:ofs+2] = post
        res += [("speed_limit_sport_0", hex(ofs), pre.hex(), post.hex())]

        try:
            disasm = self.disassembly(pre_)
            ofs_ldr = extract_ldr_offset(disasm)
            ofs = offset_to_nearest_word(ofs_+ofs_ldr)
            pre = self.data[ofs:ofs+4]
            post = self._calc_speed(speed, size=4)
            self.data[ofs:ofs+4] = post
            res += [("speed_limit_sport_1", hex(ofs), pre.hex(), post.hex())]
        except:
            raise SignatureException("Pattern not found!")

        try:
            res += self.__remove_speed_check()
        except SignatureException:
            pass

        return res

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(speed=36.7)
