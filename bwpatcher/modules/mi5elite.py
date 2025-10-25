#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Mi 5 Elite Module
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

from bwpatcher.core_n32 import CoreN32Patcher
from bwpatcher.utils import find_pattern


class Mi5elitePatcher(CoreN32Patcher):
    """
    Patcher for Xiaomi Mi 5 Elite with N32 (Leqi) controller.
    Applies specific binary patches using signature-based pattern matching.
    """

    # Signature for sport mode speed limit patch
    SIG_SPEED_LIMIT_SPORT = [0x98, 0xF8, 0x05, 0x00, 0x53, 0x49, 0x00, 0xEB, 0x80, 0x00, 0x40, 0x00, 0x08, 0x80]

    # Signature for speed limit branch fix (BNE -> B unconditional)
    SIG_SPEED_LIMIT_FIX = [0x7B, 0x49, 0x67, 0x45, 0x16, 0xD0, 0x0B, 0xDC]

    # Signature for motor start speed comparisons
    SIG_MOTOR_START = [0x01, 0x80, 0x2D, 0x2B, 0xEF, 0xD3, 0x11, 0x70, 0x70, 0xBD, 0x14, 0x33, 0x2D, 0x2B, 0x07, 0xD2]

    def __init__(self, data):
        """
        Initialize Mi5Elite patcher with firmware data.

        Args:
            data: Raw (unencrypted) firmware data as bytes or bytearray
        """
        super().__init__(data)

    def remove_speed_limit_sport(self):
        """        Remove sport mode speed limit by setting it to a high value.
        Replaces instructions at 0x3C1E with:
        - MOV.W r0, #22000 (sets high speed value)
        - NOP (fills remaining bytes)

        This effectively removes the sport mode speed limit.

        Returns:
            list: List of patch result tuples
        """
        results = []

        ofs_sig = find_pattern(self.data, self.SIG_SPEED_LIMIT_SPORT)
        # Patch is at offset 6 within signature
        ofs = ofs_sig + 6
        patch_size = 6

        pre = self.data[ofs:ofs + patch_size]
        # 5F F4 AF 70 = MOV.W r0, #22000 (0x55F0 = 22000 decimal, ~36.7 km/h with factor 600)
        # 00 BF = NOP
        post = bytes([0x5F, 0xF4, 0xAF, 0x70, 0x00, 0xBF])

        self.data[ofs:ofs + patch_size] = post
        results.append(("remove_speed_limit_sport", hex(ofs), pre.hex(), post.hex()))

        return results

    def _speed_limit_fix(self):
        """
        Fix branch instruction to enable speed limit patches.

        Changes conditional branch (BNE) to unconditional branch (B).
        This allows the speed limit modifications to take effect.

        Changes: 16 D0 (BNE) -> 3F E0 (B with different offset)

        Returns:
            list: List of patch result tuples
        """
        results = []

        ofs_sig = find_pattern(self.data, self.SIG_SPEED_LIMIT_FIX)
        # Patch is at offset 4 within signature
        ofs = ofs_sig + 4
        patch_size = 2

        pre = self.data[ofs:ofs + patch_size]
        post = bytes([0x3F, 0xE0])

        self.data[ofs:ofs + patch_size] = post
        results.append(("speed_limit_fix", hex(ofs), pre.hex(), post.hex()))

        return results

    def motor_start_speed(self, kmh):
        """
        Set motor start speed (minimum speed before motor engages).

        This patches three comparison values in the firmware:
        - Main threshold (appears twice)
        - Hysteresis threshold (half of main threshold)

        Args:
            kmh: Desired motor start speed in km/h

        Returns:
            list: List of tuples (patch_name, offset, old_hex, new_hex) for each patch applied
        """
        results = []

        ofs_sig = find_pattern(self.data, self.SIG_MOTOR_START)

        # Calculate speed values (factor = 10 for N32)
        speed = self._calc_speed(kmh, size=0)
        speed_hyst = speed // 2  # Hysteresis is half the target speed

        # Patch 1: Main threshold byte at offset 2 (CMP instruction immediate)
        ofs = ofs_sig + 2
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_1", hex(ofs), pre.hex(), post.hex()))

        # Patch 2: Hysteresis threshold at offset 10
        ofs = ofs_sig + 10
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed_hyst & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_hysteresis", hex(ofs), pre.hex(), post.hex()))

        # Patch 3: Main threshold byte at offset 12 (duplicate)
        ofs = ofs_sig + 12
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_2", hex(ofs), pre.hex(), post.hex()))

        return results
