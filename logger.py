"""
SmartCompress FS - Logging Module
Handles all logging operations for compression/decompression events
"""

import logging
import os
from datetime import datetime
from typing import Optional


class SmartCompressLogger:
    """Centralized logging system for SmartCompress FS operations"""
    
    def __init__(self, log_dir: str = "logs", log_file: str = "smartcompress.log"):
        """
        Initialize the logger
        
        Args:
            log_dir: Directory to store log files
            log_file: Name of the log file
        """
        self.log_dir = log_dir
        self.log_file = log_file
        self.log_path = os.path.join(log_dir, log_file)
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up logger
        self.logger = logging.getLogger('SmartCompressFS')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Log initialization
        self.logger.info("SmartCompress FS Logger initialized")
    
    def log_compression(self, file_path: str, original_size: int, compressed_size: int, 
                       compression_method: str = "gzip") -> None:
        """
        Log file compression event
        
        Args:
            file_path: Path of the compressed file
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            compression_method: Compression algorithm used
        """
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        message = (f"COMPRESSED: {file_path} | "
                  f"Original: {self._format_size(original_size)} | "
                  f"Compressed: {self._format_size(compressed_size)} | "
                  f"Saved: {compression_ratio:.1f}% | "
                  f"Method: {compression_method}")
        
        self.logger.info(message)
    
    def log_decompression(self, file_path: str, success: bool = True, 
                         error_msg: Optional[str] = None) -> None:
        """
        Log file decompression event
        
        Args:
            file_path: Path of the decompressed file
            success: Whether decompression was successful
            error_msg: Error message if decompression failed
        """
        if success:
            message = f"DECOMPRESSED: {file_path} - Successfully restored"
        else:
            message = f"DECOMPRESSION FAILED: {file_path} - {error_msg or 'Unknown error'}"
        
        self.logger.info(message)
    
    def log_disk_scan(self, total_files: int, compressible_files: int, 
                     disk_usage_percent: float) -> None:
        """
        Log disk scan results
        
        Args:
            total_files: Total number of files scanned
            compressible_files: Number of files eligible for compression
            disk_usage_percent: Current disk usage percentage
        """
        message = (f"DISK SCAN: {total_files} files scanned | "
                  f"{compressible_files} compressible | "
                  f"Disk usage: {disk_usage_percent:.1f}%")
        
        self.logger.info(message)
    
    def log_threshold_trigger(self, disk_usage_percent: float, threshold: float) -> None:
        """
        Log when disk usage threshold is triggered
        
        Args:
            disk_usage_percent: Current disk usage percentage
            threshold: Threshold percentage that was exceeded
        """
        message = (f"THRESHOLD TRIGGERED: Disk usage {disk_usage_percent:.1f}% "
                  f"exceeds threshold {threshold:.1f}% - Starting auto-compression")
        
        self.logger.warning(message)
    
    def log_error(self, operation: str, file_path: str, error_msg: str) -> None:
        """
        Log error events
        
        Args:
            operation: Type of operation (compression, decompression, etc.)
            file_path: File path where error occurred
            error_msg: Error message
        """
        message = f"ERROR in {operation}: {file_path} - {error_msg}"
        self.logger.error(message)
    
    def log_info(self, message: str) -> None:
        """
        Log general information
        
        Args:
            message: Information message to log
        """
        self.logger.info(message)
    
    def log_warning(self, message: str) -> None:
        """
        Log warning message
        
        Args:
            message: Warning message to log
        """
        self.logger.warning(message)
    
    def get_recent_logs(self, lines: int = 10) -> list:
        """
        Get recent log entries
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of recent log lines
        """
        try:
            with open(self.log_path, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) >= lines else all_lines
        except FileNotFoundError:
            return ["No log file found"]
        except Exception as e:
            return [f"Error reading log file: {str(e)}"]
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# Global logger instance
_logger_instance = None

def get_logger() -> SmartCompressLogger:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SmartCompressLogger()
    return _logger_instance
