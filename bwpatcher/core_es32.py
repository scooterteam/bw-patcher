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

class ES32Patcher(CorePatcher):
    CHK_CONST = 0x1021

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def __compute_checksum(cls, data, offset, size):
        def checksum(param_1: int, param_2: int) -> int:
            param_1 = (param_2 << 8) ^ param_1
            for _ in range(8):
                if (param_1 & 0x8000) != 0:
                    param_1 = (param_1 << 1) ^ cls.CHK_CONST
                else:
                    param_1 = param_1 << 1
                param_1 &= 0xFFFF
            return param_1

        data = data[offset:]
        if size > len(data):
            raise Exception("Error: File is shorter than expected range.")

        chk = 0
        for i in range(0, size):
            chk = checksum(chk, data[i])
        return chk.to_bytes(2, byteorder='big')

    @classmethod
    def _calc_speed(cls, speed, factor=20.9, size=2):
        return int(factor * speed).to_bytes(size, 'little')

    def fix_checksum(self):
        sig = 'SZMC-ES-ZM-0283M'.encode()
        ofs = find_pattern(self.data, sig) + 0x20
        size = int.from_bytes(
            self.data[ofs-0x2a:ofs-0x28],
            byteorder='big'
        )
        pre = self.data[ofs:ofs+2]
        post = self.__compute_checksum(
            self.data,
            offset=ofs+0x50,
            size=size
        )
        self.data[ofs:ofs+2] = post[:2]

        return ("fix_checksum", hex(ofs), pre.hex(), post.hex())