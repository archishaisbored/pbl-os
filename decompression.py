"""
SmartCompress FS - Decompression Module
Handles safe decompression of compressed files using metadata
"""

import os
import gzip
import zlib
import shutil
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from logger import get_logger
from compressed_marker import CompressedMarker


class DecompressionManager:
    """Manages decompression operations with integrity checks"""

    def __init__(self):
        """Initialize the decompression manager"""
        self.logger = get_logger()
        self.marker = CompressedMarker()

        # Supported compression methods
        self.decompression_methods = {
            'gzip': self._decompress_gzip,
            'zlib': self._decompress_zlib
        }

        self.logger.log_info("Decompression manager initialized")

    def decompress_file(self, original_path: str, verify_integrity: bool = True) -> bool:
        """
        Decompress a single file

        Args:
            original_path: Original file path (before compression)
            verify_integrity: Whether to verify file integrity after decompression

        Returns:
            True if decompression successful, False otherwise
        """
        try:
            # Get file metadata
            file_info = self.marker.get_compressed_file_info(original_path)
            if not file_info:
                self.logger.log_error("decompression", original_path,
                                    "File not found in compression metadata")
                return False

            compressed_path = file_info["compressed_path"]
            compression_method = file_info["compression_method"]
            original_hash = file_info.get("original_hash", "")

            # Check if compressed file exists
            if not os.path.exists(compressed_path):
                self.logger.log_error("decompression", compressed_path,
                                    "Compressed file not found")
                return False

            # Check if decompression method is supported
            if compression_method not in self.decompression_methods:
                self.logger.log_error("decompression", original_path,
                                    f"Unsupported compression method: {compression_method}")
                return False

            # Create backup of original path if it exists
            backup_path = None
            if os.path.exists(original_path):
                backup_path = f"{original_path}.backup_{int(time.time())}"
                shutil.copy2(original_path, backup_path)
                self.logger.log_info(f"Created backup: {backup_path}")

            # Perform decompression
            success = self.decompression_methods[compression_method](
                compressed_path, original_path
            )

            if not success:
                # Restore backup if decompression failed
                if backup_path and os.path.exists(backup_path):
                    shutil.move(backup_path, original_path)
                return False

            # Verify integrity if requested and hash is available
            if verify_integrity and original_hash:
                if not self._verify_file_integrity(original_path, original_hash):
                    self.logger.log_error("decompression", original_path,
                                        "File integrity verification failed")
                    # Restore backup
                    if backup_path and os.path.exists(backup_path):
                        shutil.move(backup_path, original_path)
                    return False

            # Remove compressed file
            try:
                os.remove(compressed_path)
                self.logger.log_info(f"Removed compressed file: {compressed_path}")
            except Exception as e:
                self.logger.log_warning(f"Could not remove compressed file {compressed_path}: {e}")

            # Remove from metadata
            self.marker.unmark_compressed(original_path)

            # Clean up backup
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)

            self.logger.log_decompression(original_path, success=True)
            return True

        except Exception as e:
            self.logger.log_error("decompression", original_path, str(e))
            self.logger.log_decompression(original_path, success=False, error_msg=str(e))
            return False

    def decompress_all(self, verify_integrity: bool = True) -> Tuple[int, int]:
        """
        Decompress all compressed files

        Args:
            verify_integrity: Whether to verify file integrity after decompression

        Returns:
            Tuple of (successful_count, failed_count)
        """
        compressed_files = self.marker.get_all_compressed_files()

        if not compressed_files:
            self.logger.log_info("No compressed files found for decompression")
            return 0, 0

        successful_count = 0
        failed_count = 0

        self.logger.log_info(f"Starting bulk decompression of {len(compressed_files)} files")

        for file_info in compressed_files:
            original_path = file_info["original_path"]

            if self.decompress_file(original_path, verify_integrity):
                successful_count += 1
            else:
                failed_count += 1

        self.logger.log_info(f"Bulk decompression completed: {successful_count} successful, "
                           f"{failed_count} failed")

        return successful_count, failed_count

    def decompress_by_criteria(self, file_types: List[str] = None,
                             max_age_days: int = None,
                             verify_integrity: bool = True) -> Tuple[int, int]:
        """
        Decompress files based on specific criteria

        Args:
            file_types: List of file extensions to decompress (e.g., ['.txt', '.log'])
            max_age_days: Maximum age in days since compression
            verify_integrity: Whether to verify file integrity after decompression

        Returns:
            Tuple of (successful_count, failed_count)
        """
        compressed_files = self.marker.get_all_compressed_files()

        if not compressed_files:
            return 0, 0

        # Filter files based on criteria
        filtered_files = []
        current_time = time.time()

        for file_info in compressed_files:
            # Filter by file type
            if file_types:
                file_type = file_info.get("file_type", "")
                if file_type not in file_types:
                    continue

            # Filter by age
            if max_age_days:
                compression_time = datetime.fromisoformat(
                    file_info["compression_timestamp"]
                ).timestamp()
                age_days = (current_time - compression_time) / (24 * 3600)
                if age_days > max_age_days:
                    continue

            filtered_files.append(file_info)

        if not filtered_files:
            self.logger.log_info("No files match the decompression criteria")
            return 0, 0

        successful_count = 0
        failed_count = 0

        self.logger.log_info(f"Starting criteria-based decompression of {len(filtered_files)} files")

        for file_info in filtered_files:
            original_path = file_info["original_path"]

            if self.decompress_file(original_path, verify_integrity):
                successful_count += 1
            else:
                failed_count += 1

        return successful_count, failed_count

    def _decompress_gzip(self, compressed_path: str, output_path: str) -> bool:
        """
        Decompress a gzip file

        Args:
            compressed_path: Path to compressed file
            output_path: Path for decompressed file

        Returns:
            True if successful, False otherwise
        """
        try:
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return True
        except Exception as e:
            self.logger.log_error("gzip_decompression", compressed_path, str(e))
            return False

    def _decompress_zlib(self, compressed_path: str, output_path: str) -> bool:
        """
        Decompress a zlib file

        Args:
            compressed_path: Path to compressed file
            output_path: Path for decompressed file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(compressed_path, 'rb') as f_in:
                compressed_data = f_in.read()
                decompressed_data = zlib.decompress(compressed_data)

            with open(output_path, 'wb') as f_out:
                f_out.write(decompressed_data)

            return True
        except Exception as e:
            self.logger.log_error("zlib_decompression", compressed_path, str(e))
            return False

    def _verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify file integrity using SHA-256 hash

        Args:
            file_path: Path to file to verify
            expected_hash: Expected SHA-256 hash

        Returns:
            True if hash matches, False otherwise
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)

            actual_hash = hash_sha256.hexdigest()
            return actual_hash == expected_hash

        except Exception as e:
            self.logger.log_error("integrity_check", file_path, str(e))
            return False

    def get_decompression_preview(self) -> List[Dict[str, Any]]:
        """
        Get preview of files that can be decompressed

        Returns:
            List of file information dictionaries
        """
        compressed_files = self.marker.get_all_compressed_files()
        preview_list = []

        for file_info in compressed_files:
            compressed_path = file_info["compressed_path"]

            # Check if compressed file still exists
            exists = os.path.exists(compressed_path)

            preview_info = {
                "original_path": file_info["original_path"],
                "compressed_path": compressed_path,
                "file_type": file_info.get("file_type", "unknown"),
                "original_size": file_info["original_size"],
                "compressed_size": file_info["compressed_size"],
                "compression_method": file_info["compression_method"],
                "compression_date": file_info["compression_timestamp"],
                "compressed_file_exists": exists,
                "can_decompress": exists
            }

            preview_list.append(preview_info)

        return preview_list
