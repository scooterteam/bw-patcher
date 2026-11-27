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

from bwpatcher.core_lks32 import LKS32Patcher
from bwpatcher.utils import find_pattern


# Arch / ISA: Linko LKS32MC071 · Cortex-M0 · ARMv6-M · Thumb-1 only (no movw).
class Mi6ultraPatcher(LKS32Patcher):
    # Live ride code is App B @ 0x2800 (boot jumps here). App A @ 0x0 is bootloader only.
    # A second signature hit lives in the idle Path-B staging mirror @ 0xF004 — do not patch it.
    APP_B_START = 0x2800
    APP_B_END = 0xF000

    # KERS_InitRegenParams: default table[1] write, then region compares, then 71942 stub.
    # Stub = movs/adds 0x145 + strh [r0,#2] … (same site 6ultra_mod forces into).
    SIG_DRIVE_STUB = [0xFF, 0x21, 0x46, 0x31, 0x41, 0x80]
    # beq @ stub-0x1E — stock jumps to 70776 body; 6ultra_mod turns this into b stub.
    DRIVE_STUB_BEQ_BACK = 0x1E

    # MODE==5 sport speed constant (0x145) in SpeedLimit_UpdateModeTargets — definition site only.
    SIG_SPORT_MODE5 = [0xFF, 0x20, 0x46, 0x30, 0xE3, 0xE7]

    SIG_MSS_PRIMARY = [0x1E, 0x28, 0x16, 0xDA, 0xE8, 0x8B, 0x14, 0x28, 0x11, 0xD2]
    SIG_MSS_SECONDARY = [0x1E, 0x28, 0x06, 0xDA, 0xEE, 0x71]
    SIG_SOFT_OVERSPEED = [0x31, 0x48, 0x00, 0x68, 0x31, 0x4A, 0x90, 0x42, 0x3E, 0xD0]

    def _find_app_b(self, sig: list, start: int = 0) -> int:
        ofs = max(start, self.APP_B_START)
        while True:
            hit = find_pattern(self.data, sig, start=ofs)
            if self.APP_B_START <= hit < self.APP_B_END:
                return hit
            ofs = hit + 1
            if ofs >= self.APP_B_END:
                raise RuntimeError(
                    f"signature not found in live App B ({self.APP_B_START:#x}-{self.APP_B_END:#x})"
                )

    # Cortex-M0: no Thumb-2 movw. Encode u16 as movs #lo + adds #hi (max 0xFF+0xFF).
    SPEED_U16_MAX = 0xFF + 0xFF  # 510 → 51.0 km/h

    def _speed_u16(self, kmh: float) -> int:
        val = int(round(kmh * 10))
        if not 10 <= val <= self.SPEED_U16_MAX:
            raise ValueError(
                f"Speed must be between 1.0 and {self.SPEED_U16_MAX / 10:.1f} km/h "
                f"(Cortex-M0 movs+adds): {kmh}"
            )
        return val

    def _mss_u8(self, kmh: float) -> int:
        val = int(round(float(kmh) * 10))
        if not 1 <= val <= 90:
            raise ValueError(f"Motor start speed must be between 0.1 and 9.0 km/h: {kmh}")
        return val

    def _movs_adds(self, reg: str, val: int) -> bytes:
        """Thumb-1 load of 0..510 into reg (stock / 6ultra_mod style)."""
        if val <= 0xFF:
            lo, hi = val, 0
        else:
            lo, hi = 0xFF, val - 0xFF
        post = self.assembly(f"movs {reg}, #{lo}") + self.assembly(f"adds {reg}, #{hi}")
        assert len(post) == 4
        return post

    def _force_high_region_stub(self):
        """Same as ~/6ultra_mod.bin: always enter the 71942 fill stub (does not change g_regionId)."""
        cached = getattr(self, "_mi6ultra_drive_stub", None)
        if cached is not None:
            return cached, None
        stub = self._find_app_b(self.SIG_DRIVE_STUB)
        beq_ofs = stub - self.DRIVE_STUB_BEQ_BACK
        pre = self.data[beq_ofs:beq_ofs + 2]
        post = self.assembly(f"b #{stub - beq_ofs}")
        assert len(post) == 2
        self.data[beq_ofs:beq_ofs + 2] = post
        self._mi6ultra_drive_stub = stub
        return stub, ("speed_limit_force_high_stub", hex(beq_ofs), pre.hex(), post.hex())

    def _write_drive_stub(self, stub: int, val: int):
        pre = self.data[stub:stub + 6]
        post = self._movs_adds("r1", val) + self.assembly("strh r1, [r0, #0x2]")
        assert len(post) == 6
        self.data[stub:stub + 6] = post
        return ("speed_limit_drive_table1", hex(stub), pre.hex(), post.hex())

    def speed_limit_drive(self, kmh: float):
        """Raise table[1] via 6ultra_mod-style init path (KERS_InitRegenParams)."""
        val = self._speed_u16(kmh)
        stub, force = self._force_high_region_stub()
        result = []
        if force is not None:
            result.append(force)
        result.append(self._write_drive_stub(stub, val))
        return result

    def speed_limit_sport(self, kmh: float):
        """Raise MODE==5 sport constant in place (no mode3/4 dispatch rewrite).

        Also force the high init stub and set table[1] to the same value so modes
        that load table[1] (2/3/4) match — same producer style as 6ultra_mod.
        """
        val = self._speed_u16(kmh)
        res = list(self.speed_limit_drive(kmh))

        mode5 = self._find_app_b(self.SIG_SPORT_MODE5)
        pre = self.data[mode5:mode5 + 4]
        post = self._movs_adds("r0", val)
        assert len(post) == 4
        self.data[mode5:mode5 + 4] = post
        res.append(("speed_limit_sport_mode5", hex(mode5), pre.hex(), post.hex()))
        return res

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(kmh=36.7)

    def motor_start_speed(self, kmh: float):
        val = self._mss_u8(kmh)
        post = self.assembly(f"cmp r0, #{val}")
        assert len(post) == 2

        ofs = self._find_app_b(self.SIG_MSS_PRIMARY)
        pre = self.data[ofs:ofs + 2]
        self.data[ofs:ofs + 2] = post

        ofs2 = self._find_app_b(self.SIG_MSS_SECONDARY)
        pre2 = self.data[ofs2:ofs2 + 2]
        self.data[ofs2:ofs2 + 2] = post

        return [
            ("motor_start_speed_primary", hex(ofs), pre.hex(), post.hex()),
            ("motor_start_speed_secondary", hex(ofs2), pre2.hex(), post.hex()),
        ]

    def remove_soft_overspeed_brake(self):
        ofs = self._find_app_b(self.SIG_SOFT_OVERSPEED) + 6
        pre = self.data[ofs:ofs + 4]
        post = self.assembly("b #0x82") + self.assembly("nop")
        assert len(post) == 4
        self.data[ofs:ofs + 4] = post
        return [("remove_soft_overspeed_brake", hex(ofs), pre.hex(), post.hex())]
