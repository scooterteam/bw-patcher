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

import keystone
import capstone

from bwpatcher.utils import find_pattern


class CorePatcher():
    def __init__(self, data):
        self.data = bytearray(data)
        self.ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
        self.cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_LITTLE_ENDIAN)

    def assembly(self, code):
        return bytes(self.ks.asm(code)[0])

    def disassembly(self, code_bytes: bytes):
        """Disassemble bytes and return code"""
        instructions = []
        for insn in self.cs.disasm(code_bytes, 0):
            instructions.append(f"{insn.mnemonic}\t{insn.op_str}")
        return "\n".join(instructions)

    def dashboard_max_speed(self, speed: float):
        raise NotImplementedError()

    def speed_limit_drive(self, kmh: float):
        raise NotImplementedError()

    def speed_limit_sport(self, kmh: float):
        raise NotImplementedError()

    def remove_speed_limit_sport(self):
        raise NotImplementedError()

    def region_free(self):
        raise NotImplementedError()

    def fix_checksum(self):
        raise NotImplementedError()

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

    def motor_start_speed(self, speed: int):
        raise NotImplementedError()