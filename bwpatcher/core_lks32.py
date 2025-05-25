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

import math
import crcmod

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern, SignatureException


class LKS32Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    def _speed_limits_fix(self, sig: list, sig_dst: list):
        ret = []
        ofs = find_pattern(self.data, sig) + len(sig)
        try:
            # jump to the end of the function
            ofs_dst = find_pattern(self.data, sig_dst, start=ofs) + 4
            pre = self.data[ofs:ofs+2]
            post = self.assembly(f"b {ofs_dst-ofs}")
            self.data[ofs:ofs+2] = post
            ret.append(("speed_limits_fix", hex(ofs), pre.hex(), post.hex()))

            # NOP unnecessary code, making space for 4-bytes speed limit values
            ofs += 2
            nop_size = ofs_dst - ofs
            assert nop_size % 2 == 0, "Odd size of the space needed."

            pre = self.data[ofs:ofs+nop_size]
            post = self.assembly(f"nop") * (nop_size//2)
            assert len(pre) == len(post), "Wrong length of post bytes"

            self.data[ofs:ofs+nop_size] = post
            ret.append(("speed_limits_fix_nop", hex(ofs), pre.hex(), post.hex()))
        except SignatureException:
            # verify if the patch has already been used
            # otherwise the function will raise a SignatureException
            sig_dst = [0x00, 0xBF, 0x00, 0xBF, sig_dst[-2], sig_dst[-1]]
            ofs_dst = find_pattern(self.data, sig_dst, start=ofs)

        return ret

    @staticmethod
    def _safe_ldr(ldr_offset: int, dst_ofs: int) -> tuple[int, int]:
        pc_base = (ldr_offset & ~0x3) + 4
        min_off = dst_ofs - pc_base
        if min_off < 0:
            raise ValueError("Minimum destination offset is earlier than PC_base")
        if min_off % 4 != 0:
            min_off = (min_off & ~0x3) + 4

        ldr_ofs_val = int(math.ceil(min_off / 4.0))
        return pc_base + (ldr_ofs_val * 4), min_off

    @classmethod
    def _compute_checksum(cls, data, offset, size):
        if size > len(data):
            raise Exception("Error: File is shorter than expected range.")

        data = data[offset:offset+size]

        # pad with 0xFF to make data length a multiple of 4
        pad_len = (-len(data)) % 4
        padded = data + b'\xFF' * pad_len

        # create a CRC-32 function to simulate hardware CRC unit
        crc_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0xFFFFFFFF, rev=False)

        chk = crc_func(padded) & 0xFFFFFFFF
        return chk.to_bytes(4, byteorder='little')

    def fix_checksum(self):
        sig = 'LKS32MC0'.encode()
        ofs = find_pattern(self.data, sig) - 0x8

        if self.data[ofs-2:ofs] != b'\xFF\xFF':
            return

        size = int.from_bytes(
            self.data[ofs:ofs+4],
            byteorder='little'
        )
        pre = self.data[ofs+4:ofs+8]
        post = self._compute_checksum(
            self.data,
            offset=ofs+0x18,
            size=size
        )
        self.data[ofs+4:ofs+8] = post

        res = super().fix_checksum(ofs, size)
        return [("fix_checksum", hex(ofs), pre.hex(), post.hex()), res]

    def fake_drv_version(self, firmware_version: str):
        if not firmware_version.isdigit():
            raise ValueError(f"Firmware version must contain only digits: {firmware_version}")
        if len(firmware_version) != 4:
            raise ValueError(f"Firmware version must have 4 digits: {firmware_version}")

        sig = [0x6F, 0x6B, 0x0D, None, None, None, None, 0x0D, 0x65, 0x72, 0x72, 0x6F, 0x72]
        ofs = find_pattern(self.data, sig) + 3
        pre = self.data[ofs:ofs+4]
        post = firmware_version.encode("ascii")
        self.data[ofs:ofs+4] = post
        return [("fake_drv_version", hex(ofs), pre.hex(), post.hex())]