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
from bwpatcher.utils import find_pattern, SignatureException, SignatureException


class Mi5elitePatcher(CoreN32Patcher):
    """
    Patcher for Xiaomi Mi 5 Elite with N32 (Leqi) controller.
    Applies specific binary patches using signature-based pattern matching.
    """

    # Signature for the original speed limit logic, which will be replaced by a branch.
    DEPR_SIG_SPEED_LIMIT = [0x98, 0xF8, 0x05, 0x00, 0x53, 0x49, 0x00, 0xEB, 0x80, 0x00, 0x40, 0x00, 0x08, 0x80]

    # Signature for the return address after the speed limit logic.
    SIG_SPEED_LIMIT_RETURN = [ 0x08, 0x80, 0x52, 0x48, 0x52, 0x49, 0x00, 0x88, 0x09, 0x88, 0x00, 0xf1, 0x0a, 0x02, 0x8a, 0x42, 0x01, 0xd9 ]

    # Signature for the destination of our new branch, where the patch logic will be placed.
    SIG_SPEED_LIMIT_DST = [ 0xdf, 0xf8, 0xf0, 0x81, 0xa8, 0xf8, 0x00, 0x10, 0x7b, 0x49, 0x67, 0x45 ]

    # Signature for motor start speed comparisons
    SIG_MOTOR_START = [0x01, 0x80, 0x2D, 0x2B, 0xEF, 0xD3, 0x11, 0x70, 0x70, 0xBD, 0x14, 0x33, 0x2D, 0x2B, 0x07, 0xD2]

    # Signature for upper speed limit (mov.w r0, #0x15e + branch)
    SIG_UPPER_SPEED_LIMIT = [0x4f, 0xf4, 0xaf, 0x70, 0xd7, 0xe7]  # mov.w r0,#0x15e (350); b ...

    def __init__(self, data):
        """
        Initialize Mi5Elite patcher with firmware or full image data.

        Args:
            data: Firmware or full image data as bytes or bytearray
        """
        super().__init__(data)
        self.patched_speeds = {}  # Only store speeds for modes that are actually patched
        self._speed_block_patched = False  # Track if structural patch has been applied

    def _patch_speed_block(self, ped_kmh=None, drive_kmh=None, sport_kmh=None):
        # Update speed values for modes being patched
        if ped_kmh is not None:
            self.patched_speeds['ped'] = self._calc_speed(ped_kmh, size=0)
        if drive_kmh is not None:
            self.patched_speeds['drive'] = self._calc_speed(drive_kmh, size=0)
        if sport_kmh is not None:
            self.patched_speeds['sport'] = self._calc_speed(sport_kmh, size=0)

        # First time: apply the structural patches
        results = []

        # Apply the speed limit fix (removes regional restrictions)
        results.extend(self._speed_limit_fix())

        # Find the location to branch from (4 bytes before ldr r1)
        if not self._speed_block_patched:
            try:
                sig_offset = find_pattern(self.data, self.SIG_SPEED_LIMIT_RETURN)
                # Branch patch starts at ldrb.w (4 bytes before ldr r1)
                # This gives us 6 bytes: ldrb.w (4) + ldr r1 (2), preserving add.w
                self._ldr_patch_offset = sig_offset - 12
            except SignatureException:
                raise Exception("Could not find speed limit signature for patching.")

            # Find the destination for speed checking logic
            try:
                self._speed_logic_offset = find_pattern(self.data, self.SIG_SPEED_LIMIT_DST) + len(self.SIG_SPEED_LIMIT_DST) + 2
            except SignatureException:
                raise Exception("Could not find speed limit destination signature for patching.")

            # Return addresses:
            # - new_return_address: for default case, jumps to preserved add.w at offset+6
            # - old_return_address: for patched modes, jumps after lsls to strh (offset+12)
            self._new_return_address = self._ldr_patch_offset + 6   # Execute preserved add.w and lsls
            self._old_return_address = self._ldr_patch_offset + 12  # Skip add.w and lsls, go to strh

            # Find the mode data address (r0) - pattern: 8a 01 00 20 (0x2000018A)
            mode_data_pattern = [0x8a, 0x01, 0x00, 0x20]
            try:
                mode_data_addr = find_pattern(self.data, mode_data_pattern)
            except SignatureException:
                raise Exception("Could not find mode data address pattern")

            # Calculate PC-relative offset for ldr r0
            ldr_r0_pc = (self._ldr_patch_offset + 4) & ~3
            self._offset_r0 = mode_data_addr - ldr_r0_pc

            # Patch 1: Branch patch (6 bytes) - load mode and branch to speed logic
            # This replaces ldrb.w (4 bytes) + ldr r1 (2 bytes), preserving add.w at offset+6
            branch_asm = f"""
            ldr r0, [pc, #{self._offset_r0}]
            ldrb r0, [r0, #0]
            b {hex(self._speed_logic_offset)}
            """
            branch_bytes = self.assembly(branch_asm, self._ldr_patch_offset)
            assert len(branch_bytes) == 6, f"Branch patch must be 6 bytes, got {len(branch_bytes)}"

            pre_branch = self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6]
            self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6] = branch_bytes
            results.append(("branch_patch", hex(self._ldr_patch_offset), pre_branch.hex(), branch_bytes.hex()))

            # Store offset for future updates
            self._patch_start_offset = self._speed_logic_offset

            # Find the r1 data address - pattern: a4 01 00 20 (0x200001A4)
            r1_data_pattern = [0xa4, 0x01, 0x00, 0x20]
            try:
                r1_data_addr = find_pattern(self.data, r1_data_pattern)
            except SignatureException:
                raise Exception("Could not find r1 data address pattern")

            # Calculate offset for the single ldr r1 instruction at the start of the block
            ldr_r1_addr = self._patch_start_offset
            ldr_r1_pc = (ldr_r1_addr + 4) & ~3
            self._ldr_r1_offset = r1_data_addr - ldr_r1_pc

        # Build speed checking logic - only include blocks for patched modes
        asm_code = f"ldr r1, [pc, #{self._ldr_r1_offset}]\n"
        mode_checks = []

        if 'ped' in self.patched_speeds:
            mode_checks.append('ped')
        if 'drive' in self.patched_speeds:
            mode_checks.append('drive')
        if 'sport' in self.patched_speeds:
            mode_checks.append('sport')

        # Generate checks for patched modes only
        for i, mode in enumerate(mode_checks):
            mode_num = {'ped': 1, 'drive': 2, 'sport': 3}[mode]
            speed = self.patched_speeds[mode]
            next_label = f"check_{mode_checks[i+1]}" if i+1 < len(mode_checks) else "default_case"

            asm_code += f"""
            check_{mode}:
            cmp r0, #{mode_num}
            bne {next_label}
            movs.w r0, #{speed}
            b {hex(self._old_return_address)}
            """

        # Default case: execute both original instructions we replaced, then continue
        asm_code += f"""
        default_case:
        ldrb.w r0, [r8, #5]
        b {hex(self._new_return_address)}
        """

        # Assemble the complete speed logic
        patch_bytes = self.assembly(asm_code, self._patch_start_offset)

        # Apply the speed logic patch
        pre = self.data[self._patch_start_offset : self._patch_start_offset + len(patch_bytes)]
        self.data[self._patch_start_offset : self._patch_start_offset + len(patch_bytes)] = patch_bytes

        if not self._speed_block_patched:
            results.append(("speed_logic_block", hex(self._patch_start_offset), pre.hex(), patch_bytes.hex()))
            self._speed_block_patched = True # Mark as patched only after initial setup
        else:
            results.append(("speed_constants_updated", hex(self._patch_start_offset), pre.hex(), patch_bytes.hex()))

        return results

    def speed_limit_ped(self, kmh):
        """
        Set the speed limit for Pedestrian mode (r0 == 1).
        """
        return self._patch_speed_block(ped_kmh=kmh)

    def speed_limit_drive(self, kmh):
        """
        Set the speed limit for Drive mode (r0 == 2).
        """
        return self._patch_speed_block(drive_kmh=kmh)

    def speed_limit_sport(self, kmh):
        """
        Set the speed limit for Sport mode (r0 == 3).
        """
        return self._patch_speed_block(sport_kmh=kmh)

    @DeprecationWarning
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

        ofs_sig = find_pattern(self.data, self.DEPR_SIG_SPEED_LIMIT)
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
        Remove regional speed limits

        Returns:
            list: List of patch result tuples
        """
        results = []
        try:
            ofs_sig = find_pattern(self.data, self.SIG_SPEED_LIMIT_DST)
        except SignatureException:
            return results  # Already patched or not found, do nothing.

        # Patch is at offset 4 within signature
        ofs = ofs_sig + len(self.SIG_SPEED_LIMIT_DST)
        patch_size = 2

        pre = self.data[ofs:ofs + patch_size]
        post = bytes([0x3F, 0xE0])

        # Avoid re-patching
        if pre == post:
            return results

        assert len(pre) == len(post), f"Speed limit fix size mismatch: {len(pre)} != {len(post)}"
        self.data[ofs:ofs + patch_size] = post
        results.append(("speed_limit_fix", hex(ofs), pre.hex(), post.hex()))

        # Patch upper speed limit if sport mode is set
        if False and 'sport' in self.patched_speeds:  # deactivated, remove False to activate
            try:
                upper_limit_offset = find_pattern(self.data, self.SIG_UPPER_SPEED_LIMIT)
                upper_limit_speed = self.patched_speeds['sport'] + 20

                # Assemble mov.w r0, #upper_limit_speed
                upper_limit_asm = f"mov.w r0, #{upper_limit_speed}"
                upper_limit_bytes = self.assembly(upper_limit_asm, upper_limit_offset)

                # Only patch the mov.w (first 4 bytes), keep the branch
                upper_limit_patch_size = 4
                pre_upper = self.data[upper_limit_offset:upper_limit_offset + upper_limit_patch_size]
                self.data[upper_limit_offset:upper_limit_offset + upper_limit_patch_size] = upper_limit_bytes[:upper_limit_patch_size]
                results.append(("upper_speed_limit", hex(upper_limit_offset), pre_upper.hex(), upper_limit_bytes[:upper_limit_patch_size].hex()))
            except SignatureException:
                pass  # Upper speed limit pattern not found, skip this patch

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
        assert len(pre) == len(post), f"Motor threshold 1 size mismatch: {len(pre)} != {len(post)}"
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_1", hex(ofs), pre.hex(), post.hex()))

        # Patch 2: Hysteresis threshold at offset 10
        ofs = ofs_sig + 10
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed_hyst & 0xFF])
        assert len(pre) == len(post), f"Motor hysteresis size mismatch: {len(pre)} != {len(post)}"
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_hysteresis", hex(ofs), pre.hex(), post.hex()))

        # Patch 3: Main threshold byte at offset 12 (duplicate)
        ofs = ofs_sig + 12
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        assert len(pre) == len(post), f"Motor threshold 2 size mismatch: {len(pre)} != {len(post)}"
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_2", hex(ofs), pre.hex(), post.hex()))

        return results
