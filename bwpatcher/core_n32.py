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

    def __init__(self, data):
        self.verbose = False
        self.image_header = None
        self.image_footer = None

        firmware_data = data
        # Handle full image, extract firmware if applicable
        if len(data) >= self.FIRMWARE_OFFSET + self.FIRMWARE_SIZE:
            firmware_data, self.image_header, self.image_footer = self.extract_firmware_from_image(data)

        # Detect if the original firmware was encrypted
        self.was_encrypted = self.is_encrypted(firmware_data)

        # If encrypted, decrypt it for patching
        if self.was_encrypted:
            firmware_data = self.decrypt_data(firmware_data)

        super().__init__(firmware_data)

    def fix_checksum(self, start_ofs=None):
        """
        Finalize the patch by encrypting the firmware, patching the CRC,
        and re-inserting it into the full image if necessary.
        This overrides the base class's fix_checksum and is triggered by the 'chk' patch.
        """
        # self.data is patched firmware. It will be unencrypted unless 'enc' patch was used.
        # If the original firmware was encrypted, we must re-encrypt before patching the CRC.
        if self.was_encrypted and not self.is_encrypted():
            self.encrypt_firmware()

        # Get values for return tuple, before patching CRC
        fw_size = self.calculate_firmware_size(self.data)
        offset = fw_size - 2
        chksum_before = self.data[offset:offset+2].hex()
        
        # Patch CRC
        self.patch_firmware_crc()

        # Get chksum_after
        chksum_after = self.data[offset:offset+2].hex()

        return ("fix_checksum", hex(offset), chksum_before, chksum_after)

    def create_full_image(self):
        """
        Re-assemble the full image by combining the header, patched firmware, and footer.
        This is intended to be called after 'chk' has finalized the firmware.
        """
        if self.image_header is not None and self.image_footer is not None:
            self.data = self.insert_firmware_into_image(self.data, self.image_header, self.image_footer)
            return ("create_full_image", "0x0", "N/A", "Image re-assembled")
        return ("create_full_image", "0x0", "N/A", "No header/footer found, skipping.")
        
    @classmethod
    def _calc_speed(cls, speed, factor=10, size=1):
        """
        Calculate speed value for N32 controllers.

        Args:
            speed: Speed in km/h
            factor: Conversion factor (default 10 for N32)
            size: Output size in bytes (0 = return int, 1+ = return bytes)

        Returns:
            int or bytes representing the speed value
        """
        if size == 0:
            return int(factor * speed)
        return int(factor * speed).to_bytes(size, 'little')

    def bit_reverse_8(self, value):
        """Reverse bits in an 8-bit value"""
        result = 0
        for i in range(8):
            if value & (1 << i):
                result |= 1 << (7 - i)
        return result & 0xFF

    def bit_reverse_16(self, value):
        """Reverse bits in a 16-bit value"""
        result = 0
        for i in range(16):
            if value & (1 << i):
                result |= 1 << (15 - i)
        return result & 0xFFFF

    def crc16_with_bit_reversal(self, data):
        """
        Calculate CRC-16 with bit reversal on input bytes and final result.
        Uses polynomial 0x8005.
        """
        crc = 0xFFFF

        for byte in data:
            # Bit-reverse the input byte
            reversed_byte = self.bit_reverse_8(byte)

            # XOR into CRC (shifted left 8 bits)
            crc ^= (reversed_byte << 8)

            # Process 8 bits with polynomial
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ self.CRC16_POLY) & 0xFFFF
                else:
                    crc = ((crc & 0x7FFF) << 1)

        # Bit-reverse the final CRC result
        return self.bit_reverse_16(crc)

    def encrypt_data(self, data):
        """Encrypt data using XOR with key 0xAA"""
        return bytes(b ^ self.ENCRYPTION_KEY for b in data)

    def decrypt_data(self, data):
        """Decrypt data using XOR with key 0xAA"""
        return self.encrypt_data(data)

    def calculate_firmware_size(self, firmware_data):
        """
        Find the end of the AA padding sequence.
        Returns the offset where AA padding ends, rounded up to nearest 128-byte boundary.
        """
        data = bytes(firmware_data)

        # Find the longest consecutive padding sequence (0xAA for encrypted, 0x00 for decrypted)
        max_padding_length = 0
        max_padding_end = 0
        padding_byte_found = None

        i = 0
        while i < len(data):
            padding_byte = data[i]
            if padding_byte == 0xAA or padding_byte == 0x00:
                start = i
                while i < len(data) and data[i] == padding_byte:
                    i += 1
                length = i - start

                # Track longest sequence (must be > 500 bytes)
                if length > max_padding_length and length > 500:
                    max_padding_length = length
                    max_padding_end = i
                    padding_byte_found = padding_byte
            else:
                i += 1

        if max_padding_end > 0:
            # Round up to nearest 128-byte boundary
            fw_size = ((max_padding_end + 127) // 128) * 128

            if self.verbose:
                print(f"Found {max_padding_length} consecutive 0x{padding_byte_found:02X} bytes ending at 0x{max_padding_end:X}")
                print(f"Rounded up to: 0x{fw_size:X}")
            return fw_size
        else:
            # No AA padding found, use full file size
            if self.verbose:
                print("No long AA padding found, using full file size")
            return len(data)

    def patch_firmware_crc(self, firmware_data=None):
        """
        Patch the embedded CRC-16 at the end of encrypted data.
        CRC is calculated over bytes [0x40 : size-2] and stored at [size-2 : size].

        Args:
            firmware_data: Encrypted data (bytearray or bytes).
                          If None, uses self.data

        Returns:
            bytearray: Data with correct CRC patched
        """
        if firmware_data is None:
            firmware = bytearray(self.data)
        else:
            firmware = bytearray(firmware_data)

        fw_size = self.calculate_firmware_size(firmware)

        if fw_size < 0x42:
            raise ValueError(f"Data too small ({fw_size} bytes), need at least 66 bytes")

        # Calculate CRC over bytes [0x40 : size-2]
        crc_start = 0x40
        crc_end = fw_size - 2
        crc_data = firmware[crc_start:crc_end]

        original_crc = firmware[crc_end:crc_end+2]
        # Calculate CRC with bit reversal
        correct_crc = self.crc16_with_bit_reversal(crc_data)

        # Patch the last 2 bytes with the correct CRC (big-endian)
        firmware[crc_end:fw_size] = struct.pack('>H', correct_crc)

        if self.verbose:
            print(f"CRC patch:")
            print(f"  Region: [0x{crc_start:04X}:0x{crc_end:04X}] ({len(crc_data)} bytes)")
            print(f"  Original: {original_crc.hex()}")
            print(f"  Patched:  0x{correct_crc:04X}")
            print(f"  Location: [0x{crc_end:04X}:0x{fw_size:04X}]")

        # Update self.data if we were working on it
        if firmware_data is None:
            self.data = firmware

        return firmware

    def encrypt_firmware(self):
        """
        Encrypt the data in self.data using XOR with key 0xAA

        Returns:
            bytearray: Encrypted data
        """
        print("Encrypting firmware...")
        encrypted = bytearray(self.encrypt_data(self.data))
        self.data = encrypted
        return encrypted

    def decrypt_firmware(self):
        """
        Decrypt the data in self.data using XOR with key 0xAA

        Returns:
            bytearray: Decrypted data
        """
        decrypted = bytearray(self.decrypt_data(self.data))
        self.data = decrypted
        return decrypted

    def verify_firmware_crc(self, firmware_data=None):
        """
        Verify the embedded CRC-16 in encrypted data

        Args:
            firmware_data: Encrypted data to verify.
                          If None, uses self.data

        Returns:
            tuple: (is_valid, embedded_crc, calculated_crc)
        """
        if firmware_data is None:
            firmware = bytes(self.data)
        else:
            firmware = bytes(firmware_data)

        fw_size = self.calculate_firmware_size(firmware)

        if fw_size < 0x42:
            raise ValueError(f"Data too small ({fw_size} bytes), need at least 66 bytes")

        # Extract embedded CRC
        crc_end = fw_size - 2
        embedded_crc = struct.unpack('>H', firmware[crc_end:crc_end+2])[0]

        # Calculate expected CRC
        crc_start = 0x40
        crc_data = firmware[crc_start:crc_end]
        calculated_crc = self.crc16_with_bit_reversal(crc_data)

        is_valid = (embedded_crc == calculated_crc)

        if self.verbose:
            print(f"CRC verification:")
            print(f"  Embedded:   0x{embedded_crc:04X}")
            print(f"  Calculated: 0x{calculated_crc:04X}")
            print(f"  Valid: {is_valid}")

        return (is_valid, embedded_crc, calculated_crc)

    def is_encrypted(self, firmware_data=None):
        """
        Detect if firmware is encrypted by verifying the CRC.
        Encrypted firmware will have a valid CRC.

        Args:
            firmware_data: Data to check. If None, uses self.data

        Returns:
            bool: True if encrypted (valid CRC), False if not encrypted
        """
        try:
            is_valid, _, _ = self.verify_firmware_crc(firmware_data)
            return is_valid
        except (ValueError, struct.error, IndexError):
            # If CRC verification fails, assume not encrypted
            return False

    @classmethod
    def extract_firmware_from_image(cls, full_image_data):
        """
        Extract the firmware section from a full image file.

        Args:
            full_image_data: Full image data (bytes or bytearray)

        Returns:
            tuple: (firmware_data, image_header, image_footer)
                - firmware_data: The extracted firmware section
                - image_header: Data before firmware (offset 0 to FIRMWARE_OFFSET)
                - image_footer: Data after firmware (offset FIRMWARE_OFFSET+FIRMWARE_SIZE to end)
        """
        if len(full_image_data) == cls.FIRMWARE_SIZE:
            return (full_image_data, bytes(), bytes())
        elif len(full_image_data) < cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE:
            raise ValueError(
                f"Image too small: {len(full_image_data)} bytes. "
                f"Expected at least {cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE} bytes"
            )

        # Extract the three sections
        image_header = full_image_data[:cls.FIRMWARE_OFFSET]
        firmware_data = full_image_data[cls.FIRMWARE_OFFSET:cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE]
        image_footer = full_image_data[cls.FIRMWARE_OFFSET + cls.FIRMWARE_SIZE:]

        return (firmware_data, image_header, image_footer)

    @classmethod
    def insert_firmware_into_image(cls, firmware_data, image_header, image_footer):
        """
        Insert patched firmware back into the full image structure.

        Args:
            firmware_data: Patched firmware data
            image_header: Original header data (0 to FIRMWARE_OFFSET)
            image_footer: Original footer data (after firmware)

        Returns:
            bytearray: Complete image with patched firmware
        """
        if len(firmware_data) != cls.FIRMWARE_SIZE:
            raise ValueError(
                f"Firmware size mismatch: {len(firmware_data)} bytes. "
                f"Expected {cls.FIRMWARE_SIZE} bytes"
            )

        if len(image_header) != cls.FIRMWARE_OFFSET:
            raise ValueError(
                f"Header size mismatch: {len(image_header)} bytes. "
                f"Expected {cls.FIRMWARE_OFFSET} bytes"
            )

        # Reconstruct the full image
        full_image = bytearray()
        full_image.extend(image_header)
        full_image.extend(firmware_data)
        full_image.extend(image_footer)

        return full_image

    @classmethod
    def patch_full_image(cls, full_image_data, **patches):
        """
        Complete workflow for patching a full image file:
        1. Extract firmware from full image
        2. Detect if encrypted and decrypt if needed
        3. Apply patches
        4. Encrypt and patch CRC
        5. Insert back into full image

        Args:
            full_image_data: Full image data as bytes or bytearray

        Returns:
            tuple: (patch_results, patched_full_image_data, workflow_log)
                - patch_results: List of applied patches
                - patched_full_image_data: Complete patched image
                - workflow_log: Dict with workflow step information
        """
        workflow_log = {}

        # Step 1: Extract firmware from full image
        firmware_data, image_header, image_footer = cls.extract_firmware_from_image(full_image_data)
        workflow_log['extracted_firmware_size'] = len(firmware_data)
        workflow_log['header_size'] = len(image_header)
        workflow_log['footer_size'] = len(image_footer)

        # Step 2: Detect encryption and decrypt if needed
        temp_patcher = cls(bytearray(firmware_data))
        is_encrypted = temp_patcher.is_encrypted()
        workflow_log['was_encrypted'] = is_encrypted

        if is_encrypted:
            # Decrypt the firmware
            temp_patcher.decrypt_firmware()
            firmware_data = temp_patcher.data
            workflow_log['decryption'] = 'performed'
        else:
            workflow_log['decryption'] = 'not needed'

        # Step 3: Create patcher and apply patches
        patcher = cls(bytearray(firmware_data))
        patch_results = patcher.apply_patches(**patches)
        workflow_log['patches_applied'] = len(patch_results)

        # Step 4: Encrypt and patch CRC
        patcher.encrypt_firmware()
        patcher.patch_firmware_crc()
        workflow_log['encryption'] = 'performed'
        workflow_log['crc_patched'] = True

        # Step 5: Insert back into full image
        if len(image_header) and len(image_footer):
            patched_full_image = cls.insert_firmware_into_image(
                patcher.data, image_header, image_footer
            )
        else:
            patched_full_image = patcher.data
        workflow_log['final_image_size'] = len(patched_full_image)

        return (patch_results, patched_full_image, workflow_log)
