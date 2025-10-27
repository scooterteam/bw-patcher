#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - N32 (Leqi) Module
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

import struct
from typing import Optional, Tuple
from bwpatcher.core import CorePatcher


class CoreN32Patcher(CorePatcher):
    """
    Patcher for N32 (Leqi) controllers with XOR encryption and CRC validation.
    """

    # Encryption and CRC constants
    ENCRYPTION_KEY = 0xAA
    CRC16_POLY = 0x8005

    # Image format constants
    FIRMWARE_OFFSET = 0x80      # Firmware starts at offset 128 in full image
    FIRMWARE_SIZE = 0x9880      # Expected firmware size (39040 bytes)

    # CRC calculation constants
    CRC_START_OFFSET = 0x40     # CRC calculated from this offset
    MIN_FIRMWARE_SIZE = 0x42    # Minimum valid firmware size (66 bytes)

    # Padding detection constants
    MIN_PADDING_LENGTH = 500    # Minimum consecutive padding bytes to detect end
    ALIGNMENT_BOUNDARY = 128    # Firmware size alignment boundary

    def __init__(self, data: bytes):
        """
        Initialize N32 patcher with firmware or full image data.

        Args:
            data: Raw firmware or full image data
        """
        self.verbose = False
        self.image_header: Optional[bytes] = None
        self.image_footer: Optional[bytes] = None

        firmware_data = data

        # Extract firmware from full image if present
        if len(data) >= self.FIRMWARE_OFFSET + self.FIRMWARE_SIZE:
            firmware_data, self.image_header, self.image_footer = self.extract_firmware_from_image(data)

        # Detect encryption and decrypt if needed
        self.was_encrypted = self.is_encrypted(firmware_data)
        if self.was_encrypted:
            firmware_data = self.decrypt_data(firmware_data)

        super().__init__(firmware_data)

    def fix_checksum(self, start_ofs: Optional[int] = None) -> Tuple[str, str, str, str]:
        """
        Finalize firmware by encrypting and patching CRC.

        Overrides base class method. Re-encrypts firmware if originally encrypted,
        calculates and patches CRC-16, then returns patch details.

        Args:
            start_ofs: Unused (kept for compatibility with base class)

        Returns:
            Tuple of (operation_name, offset, old_checksum, new_checksum)
        """
        # Re-encrypt if original was encrypted
        if self.was_encrypted and not self.is_encrypted():
            self.encrypt_firmware()

        # Capture checksum before patching
        fw_size = self.calculate_firmware_size(self.data)
        offset = fw_size - 2
        chksum_before = self.data[offset:offset + 2].hex()

        # Apply CRC patch
        self.patch_firmware_crc()

        chksum_after = self.data[offset:offset + 2].hex()
        return ("fix_checksum", hex(offset), chksum_before, chksum_after)

    def create_full_image(self) -> Tuple[str, str, str, str]:
        """
        Reassemble full image with header, patched firmware, and footer.

        Returns:
            Tuple of (operation_name, offset, old_value, new_value)
        """
        if self.image_header is not None and self.image_footer is not None:
            self.data = self.insert_firmware_into_image(self.data, self.image_header, self.image_footer)
            return ("create_full_image", "0x0", "N/A", "Image re-assembled")
        return ("create_full_image", "0x0", "N/A", "No header/footer found, skipping")
        
    @classmethod
    def _calc_speed(cls, speed: float, factor: int = 10, size: int = 1):
        """
        Convert km/h to N32 internal speed representation.

        Args:
            speed: Speed in km/h
            factor: Conversion factor (default 10 for N32)
            size: Output size - 0 returns int, 1+ returns little-endian bytes

        Returns:
            int or bytes representing the speed value
        """
        speed_value = int(factor * speed)
        return speed_value if size == 0 else speed_value.to_bytes(size, 'little')

    def bit_reverse_8(self, value: int) -> int:
        """Reverse bit order in an 8-bit value."""
        result = 0
        for i in range(8):
            if value & (1 << i):
                result |= 1 << (7 - i)
        return result & 0xFF

    def bit_reverse_16(self, value: int) -> int:
        """Reverse bit order in a 16-bit value."""
        result = 0
        for i in range(16):
            if value & (1 << i):
                result |= 1 << (15 - i)
        return result & 0xFFFF

    def crc16_with_bit_reversal(self, data: bytes) -> int:
        """
        Calculate CRC-16 with bit reversal using polynomial 0x8005.

        Applies bit reversal to input bytes and final CRC result.

        Args:
            data: Input data for CRC calculation

        Returns:
            16-bit CRC value with bit reversal applied
        """
        crc = 0xFFFF

        for byte in data:
            reversed_byte = self.bit_reverse_8(byte)
            crc ^= (reversed_byte << 8)

            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ self.CRC16_POLY) & 0xFFFF
                else:
                    crc = ((crc & 0x7FFF) << 1)

        return self.bit_reverse_16(crc)

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt/decrypt data using XOR with key 0xAA (symmetric operation)."""
        return bytes(b ^ self.ENCRYPTION_KEY for b in data)

    def decrypt_data(self, data: bytes) -> bytes:
        """Decrypt/encrypt data using XOR with key 0xAA (symmetric operation)."""
        return self.encrypt_data(data)

    def calculate_firmware_size(self, firmware_data: bytes) -> int:
        """
        Calculate firmware size by detecting padding sequence end.

        Finds the longest consecutive padding sequence (0xAA encrypted or 0x00 decrypted)
        and rounds up to the nearest 128-byte boundary.

        Args:
            firmware_data: Firmware data to analyze

        Returns:
            Calculated firmware size aligned to 128-byte boundary
        """
        data = bytes(firmware_data)
        max_padding_length = 0
        max_padding_end = 0
        padding_byte_found = None

        i = 0
        while i < len(data):
            padding_byte = data[i]
            if padding_byte in (0xAA, 0x00):
                start = i
                while i < len(data) and data[i] == padding_byte:
                    i += 1
                length = i - start

                if length > max_padding_length and length > self.MIN_PADDING_LENGTH:
                    max_padding_length = length
                    max_padding_end = i
                    padding_byte_found = padding_byte
            else:
                i += 1

        if max_padding_end > 0:
            fw_size = ((max_padding_end + self.ALIGNMENT_BOUNDARY - 1) //
                       self.ALIGNMENT_BOUNDARY) * self.ALIGNMENT_BOUNDARY
            if self.verbose:
                print(f"Found {max_padding_length} consecutive 0x{padding_byte_found:02X} "
                      f"bytes ending at 0x{max_padding_end:X}, rounded to 0x{fw_size:X}")
            return fw_size

        if self.verbose:
            print("No padding sequence found, using full file size")
        return len(data)

    def patch_firmware_crc(self, firmware_data: Optional[bytes] = None) -> bytearray:
        """
        Calculate and patch embedded CRC-16 at firmware end.

        CRC is calculated over bytes [0x40:size-2] and stored at [size-2:size].

        Args:
            firmware_data: Data to patch. If None, uses self.data

        Returns:
            Data with correct CRC patched

        Raises:
            ValueError: If firmware is too small (< 66 bytes)
        """
        firmware = bytearray(firmware_data if firmware_data is not None else self.data)
        fw_size = self.calculate_firmware_size(firmware)

        if fw_size < self.MIN_FIRMWARE_SIZE:
            raise ValueError(
                f"Firmware too small ({fw_size} bytes), need at least {self.MIN_FIRMWARE_SIZE} bytes"
            )

        crc_end = fw_size - 2
        crc_data = firmware[self.CRC_START_OFFSET:crc_end]
        original_crc = firmware[crc_end:crc_end + 2]
        correct_crc = self.crc16_with_bit_reversal(crc_data)

        firmware[crc_end:fw_size] = struct.pack('>H', correct_crc)

        if self.verbose:
            print(f"CRC patch: [0x{self.CRC_START_OFFSET:04X}:0x{crc_end:04X}] "
                  f"({len(crc_data)} bytes)")
            print(f"  Original: {original_crc.hex()}, Patched: 0x{correct_crc:04X}")

        if firmware_data is None:
            self.data = firmware

        return firmware

    def encrypt_firmware(self) -> bytearray:
        """
        Encrypt firmware data in-place using XOR with key 0xAA.

        Returns:
            Encrypted firmware data
        """
        print("Encrypting firmware...")
        encrypted = bytearray(self.encrypt_data(self.data))
        self.data = encrypted
        return encrypted

    def decrypt_firmware(self) -> bytearray:
        """
        Decrypt firmware data in-place using XOR with key 0xAA.

        Returns:
            Decrypted firmware data
        """
        decrypted = bytearray(self.decrypt_data(self.data))
        self.data = decrypted
        return decrypted

    def verify_firmware_crc(self, firmware_data: Optional[bytes] = None) -> Tuple[bool, int, int]:
        """
        Verify embedded CRC-16 in firmware data.

        Args:
            firmware_data: Data to verify. If None, uses self.data

        Returns:
            Tuple of (is_valid, embedded_crc, calculated_crc)

        Raises:
            ValueError: If firmware is too small
        """
        firmware = bytes(firmware_data if firmware_data is not None else self.data)
        fw_size = self.calculate_firmware_size(firmware)

        if fw_size < self.MIN_FIRMWARE_SIZE:
            raise ValueError(
                f"Firmware too small ({fw_size} bytes), need at least {self.MIN_FIRMWARE_SIZE} bytes"
            )

        crc_end = fw_size - 2
        embedded_crc = struct.unpack('>H', firmware[crc_end:crc_end + 2])[0]
        crc_data = firmware[self.CRC_START_OFFSET:crc_end]
        calculated_crc = self.crc16_with_bit_reversal(crc_data)

        is_valid = (embedded_crc == calculated_crc)

        if self.verbose:
            print(f"CRC verification: Embedded=0x{embedded_crc:04X}, "
                  f"Calculated=0x{calculated_crc:04X}, Valid={is_valid}")

        return (is_valid, embedded_crc, calculated_crc)

    def is_encrypted(self, firmware_data: Optional[bytes] = None) -> bool:
        """
        Detect if firmware is encrypted by verifying CRC.

        Encrypted firmware has a valid CRC; decrypted firmware does not.

        Args:
            firmware_data: Data to check. If None, uses self.data

        Returns:
            True if encrypted (valid CRC), False otherwise
        """
        try:
            is_valid, _, _ = self.verify_firmware_crc(firmware_data)
            return is_valid
        except (ValueError, struct.error, IndexError):
            return False

    @classmethod
    def extract_firmware_from_image(cls, full_image_data: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Extract firmware section from full image file.

        Args:
            full_image_data: Full image data

        Returns:
            Tuple of (firmware_data, image_header, image_footer)

        Raises:
            ValueError: If image is too small
        """
        if len(full_image_data) == cls.FIRMWARE_SIZE:
            return (full_image_data, bytes(), bytes())

        if len(full_image_data) < cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE:
            raise ValueError(
                f"Image too small: {len(full_image_data)} bytes, "
                f"expected at least {cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE} bytes"
            )

        image_header = full_image_data[:cls.FIRMWARE_OFFSET]
        firmware_data = full_image_data[cls.FIRMWARE_OFFSET:cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE]
        image_footer = full_image_data[cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE:]

        return (firmware_data, image_header, image_footer)

    @classmethod
    def insert_firmware_into_image(cls, firmware_data: bytes, image_header: bytes,
                                   image_footer: bytes) -> bytearray:
        """
        Insert patched firmware back into full image structure.

        Args:
            firmware_data: Patched firmware data
            image_header: Original header (0 to FIRMWARE_OFFSET)
            image_footer: Original footer (after firmware)

        Returns:
            Complete image with patched firmware

        Raises:
            ValueError: If firmware or header size doesn't match expected values
        """
        if len(firmware_data) != cls.FIRMWARE_SIZE:
            raise ValueError(
                f"Firmware size mismatch: {len(firmware_data)} bytes, "
                f"expected {cls.FIRMWARE_SIZE} bytes"
            )

        if len(image_header) != cls.FIRMWARE_OFFSET:
            raise ValueError(
                f"Header size mismatch: {len(image_header)} bytes, "
                f"expected {cls.FIRMWARE_OFFSET} bytes"
            )

        full_image = bytearray()
        full_image.extend(image_header)
        full_image.extend(firmware_data)
        full_image.extend(image_footer)

        return full_image

    @classmethod
    def patch_full_image(cls, full_image_data: bytes, **patches) -> Tuple[list, bytearray, dict]:
        """
        Complete workflow for patching a full image file.

        Workflow:
        1. Extract firmware from full image
        2. Detect encryption and decrypt if needed
        3. Apply patches
        4. Encrypt and patch CRC
        5. Insert back into full image

        Args:
            full_image_data: Full image data
            **patches: Patch parameters to apply

        Returns:
            Tuple of (patch_results, patched_image, workflow_log)
        """
        workflow_log = {}

        # Extract firmware from full image
        firmware_data, image_header, image_footer = cls.extract_firmware_from_image(full_image_data)
        workflow_log.update({
            'extracted_firmware_size': len(firmware_data),
            'header_size': len(image_header),
            'footer_size': len(image_footer)
        })

        # Detect encryption and decrypt if needed
        temp_patcher = cls(bytearray(firmware_data))
        is_encrypted = temp_patcher.is_encrypted()
        workflow_log['was_encrypted'] = is_encrypted

        if is_encrypted:
            temp_patcher.decrypt_firmware()
            firmware_data = temp_patcher.data
            workflow_log['decryption'] = 'performed'
        else:
            workflow_log['decryption'] = 'not needed'

        # Create patcher and apply patches
        patcher = cls(bytearray(firmware_data))
        patch_results = patcher.apply_patches(**patches)
        workflow_log['patches_applied'] = len(patch_results)

        # Encrypt and patch CRC
        patcher.encrypt_firmware()
        patcher.patch_firmware_crc()
        workflow_log.update({'encryption': 'performed', 'crc_patched': True})

        # Insert back into full image
        if image_header and image_footer:
            patched_full_image = cls.insert_firmware_into_image(
                patcher.data, image_header, image_footer
            )
        else:
            patched_full_image = patcher.data
        workflow_log['final_image_size'] = len(patched_full_image)

        return (patch_results, patched_full_image, workflow_log)
