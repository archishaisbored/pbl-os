import os
import gzip
import zlib
import time
import threading
import psutil
from typing import List, Optional, Dict, Any
from logger import get_logger
from compressed_marker import CompressedMarker
from tanisha_module import TanishaModule, FileInfo


class SmartCompressFS:
    
    def __init__(self, base_directory: str = None, disk_threshold: float = 90.0):

        self.base_directory = base_directory or os.getcwd()
        self.disk_threshold = disk_threshold
        self.logger = get_logger()
        self.marker = CompressedMarker()
        self.tanisha = TanishaModule(self.base_directory)
        
        # Monitoring control
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 60  # Check every 60 seconds
        
        # Compression settings
        self.compression_method = "gzip"  # Default compression method
        self.max_files_per_batch = 50     # Maximum files to compress in one batch
        
        self.logger.log_info(f"SmartCompress FS initialized - Directory: {self.base_directory}, "
                           f"Threshold: {disk_threshold}%")
    
    def get_disk_usage(self, path: str = None) -> Dict[str, Any]:
        check_path = path or self.base_directory
        
        try:
            usage = psutil.disk_usage(check_path)
            
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            used_percent = (usage.used / usage.total) * 100
            
            return {
                "path": check_path,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "used_percent": used_percent
            }
            
        except Exception as e:
            self.logger.log_error("disk_usage", check_path, str(e))
            return {}
    
    def should_trigger_compression(self, path: str = None) -> bool:
        disk_info = self.get_disk_usage(path)
        
        if not disk_info:
            return False
        
        used_percent = disk_info["used_percent"]
        
        if used_percent >= self.disk_threshold:
            self.logger.log_threshold_trigger(used_percent, self.disk_threshold)
            return True
        
        return False
    
    def compress_file(self, file_info: FileInfo) -> bool:
        try:
            original_path = file_info.path
            
            # Check if file still exists and is accessible
            if not os.path.exists(original_path):
                self.logger.log_error("compression", original_path, "File not found")
                return False
            
            # Generate compressed file path
            compressed_path = f"{original_path}.{self.compression_method}"
            
            # Ensure compressed file doesn't already exist
            counter = 1
            while os.path.exists(compressed_path):
                compressed_path = f"{original_path}.{self.compression_method}.{counter}"
                counter += 1
            
            # Perform compression
            if self.compression_method == "gzip":
                success = self._compress_gzip(original_path, compressed_path)
            elif self.compression_method == "zlib":
                success = self._compress_zlib(original_path, compressed_path)
            else:
                self.logger.log_error("compression", original_path, 
                                    f"Unsupported compression method: {self.compression_method}")
                return False
            
            if not success:
                return False
            
            # Get compressed file size
            compressed_size = os.path.getsize(compressed_path)
            
            # Mark file as compressed in metadata
            self.marker.mark_as_compressed(
                original_path, compressed_path, 
                file_info.size, compressed_size, 
                self.compression_method
            )
            
            # Remove original file
            try:
                os.remove(original_path)
                self.logger.log_info(f"Removed original file: {original_path}")
            except Exception as e:
                self.logger.log_warning(f"Could not remove original file {original_path}: {e}")
            
            # Log compression
            self.logger.log_compression(
                original_path, file_info.size, compressed_size, self.compression_method
            )
            
            return True
            
        except Exception as e:
            self.logger.log_error("compression", file_info.path, str(e))
            return False
    
    def compress_files(self, max_files: int = None) -> Dict[str, Any]:
        max_files = max_files or self.max_files_per_batch
        
        # Get priority files for compression
        priority_files = self.tanisha.get_priority_files(
            directory=self.base_directory,
            max_files=max_files
        )
        
        if not priority_files:
            self.logger.log_info("No files selected for compression")
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "space_saved": 0
            }
        
        successful_count = 0
        failed_count = 0
        total_space_saved = 0
        
        self.logger.log_info(f"Starting compression of {len(priority_files)} files")
        
        for file_info in priority_files:
            original_size = file_info.size
            
            if self.compress_file(file_info):
                successful_count += 1
                # Estimate space saved (actual calculation would require compressed size)
                # This is a rough estimate - actual savings calculated in marker
                total_space_saved += original_size * 0.3  # Assume 30% compression ratio
            else:
                failed_count += 1
        
        results = {
            "total_files": len(priority_files),
            "successful": successful_count,
            "failed": failed_count,
            "space_saved": total_space_saved
        }
        
        self.logger.log_info(f"Compression completed: {successful_count} successful, "
                           f"{failed_count} failed")
        
        return results
    
    def auto_compress_if_needed(self) -> bool:
        if self.should_trigger_compression():
            self.logger.log_info("Auto-compression triggered due to disk usage threshold")
            results = self.compress_files()
            
            if results["successful"] > 0:
                self.logger.log_info(f"Auto-compression completed: {results['successful']} files compressed")
                return True
            else:
                self.logger.log_warning("Auto-compression triggered but no files were compressed")
        
        return False
    
    def start_monitoring(self) -> bool:
        if self.monitoring:
            self.logger.log_warning("Monitoring is already running")
            return False
        
        try:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            self.logger.log_info("Disk monitoring started")
            return True
            
        except Exception as e:
            self.logger.log_error("start_monitoring", "system", str(e))
            self.monitoring = False
            return False
    
    def stop_monitoring(self) -> bool:
        if not self.monitoring:
            self.logger.log_warning("Monitoring is not running")
            return False
        
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.log_info("Disk monitoring stopped")
        return True
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop (runs in separate thread)"""
        self.logger.log_info(f"Monitoring loop started (interval: {self.monitor_interval}s)")
        
        while self.monitoring:
            try:
                # Check if auto-compression is needed
                self.auto_compress_if_needed()
                
                # Wait for next check
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.log_error("monitor_loop", "system", str(e))
                time.sleep(self.monitor_interval)
        
        self.logger.log_info("Monitoring loop ended")
    
    def _compress_gzip(self, input_path: str, output_path: str) -> bool:

        try:
            with open(input_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            return True
        except Exception as e:
            self.logger.log_error("gzip_compression", input_path, str(e))
            return False
    
    def _compress_zlib(self, input_path: str, output_path: str) -> bool:

        try:
            with open(input_path, 'rb') as f_in:
                data = f_in.read()
                compressed_data = zlib.compress(data)
                
            with open(output_path, 'wb') as f_out:
                f_out.write(compressed_data)
            
            return True
        except Exception as e:
            self.logger.log_error("zlib_compression", input_path, str(e))
            return False
