"""
SmartCompress FS - File Priority Module (Tanisha Module)
Calculates file priority for compression based on access time and size
"""

import os
import time
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from logger import get_logger
from compressed_marker import CompressedMarker


@dataclass
class FileInfo:
    """Data class to store file information"""
    path: str
    size: int
    last_access_time: float
    last_modified_time: float
    file_type: str
    priority_score: float = 0.0


class TanishaModule:
    """File priority calculation and selection module"""
    
    def __init__(self, base_directory: str = None):
        """
        Initialize the Tanisha module
        
        Args:
            base_directory: Base directory to scan (defaults to current directory)
        """
        self.base_directory = base_directory or os.getcwd()
        self.logger = get_logger()
        self.marker = CompressedMarker()
        
        # Supported file types for compression
        self.supported_extensions = {'.txt', '.log', '.json', '.csv', '.xml', '.yaml', '.yml'}
        
        # File types to ignore (already compressed or binary)
        self.ignored_extensions = {
            '.zip', '.gz', '.bz2', '.xz', '.7z', '.rar', '.tar',
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv',
            '.exe', '.dll', '.so', '.dylib', '.bin'
        }
        
        # Minimum file size for compression (in bytes)
        self.min_file_size = 1024  # 1KB
        
        # Maximum days since last access for high priority
        self.max_days_for_priority = 30
        
        self.logger.log_info("Tanisha module initialized")
    
    def scan_directory(self, directory: str = None, recursive: bool = True) -> List[FileInfo]:
        """
        Scan directory for compressible files
        
        Args:
            directory: Directory to scan (defaults to base_directory)
            recursive: Whether to scan subdirectories
            
        Returns:
            List of FileInfo objects for compressible files
        """
        scan_dir = directory or self.base_directory
        compressible_files = []
        total_files_scanned = 0
        
        self.logger.log_info(f"Starting directory scan: {scan_dir}")
        
        try:
            if recursive:
                for root, dirs, files in os.walk(scan_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_files_scanned += 1
                        
                        file_info = self._analyze_file(file_path)
                        if file_info and self._is_compressible(file_info):
                            compressible_files.append(file_info)
            else:
                for item in os.listdir(scan_dir):
                    file_path = os.path.join(scan_dir, item)
                    if os.path.isfile(file_path):
                        total_files_scanned += 1
                        
                        file_info = self._analyze_file(file_path)
                        if file_info and self._is_compressible(file_info):
                            compressible_files.append(file_info)
            
            self.logger.log_info(f"Scan completed: {total_files_scanned} files scanned, "
                               f"{len(compressible_files)} compressible files found")
            
            return compressible_files
            
        except Exception as e:
            self.logger.log_error("directory_scan", scan_dir, str(e))
            return []
    
    def _analyze_file(self, file_path: str) -> FileInfo:
        """
        Analyze a single file and create FileInfo object
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileInfo object or None if file cannot be analyzed
        """
        try:
            stat_info = os.stat(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()
            
            file_info = FileInfo(
                path=file_path,
                size=stat_info.st_size,
                last_access_time=stat_info.st_atime,
                last_modified_time=stat_info.st_mtime,
                file_type=file_extension
            )
            
            return file_info
            
        except (OSError, IOError) as e:
            self.logger.log_error("file_analysis", file_path, str(e))
            return None
    
    def _is_compressible(self, file_info: FileInfo) -> bool:
        """
        Check if a file is eligible for compression
        
        Args:
            file_info: FileInfo object
            
        Returns:
            True if file is compressible, False otherwise
        """
        # Check if file type is supported
        if file_info.file_type not in self.supported_extensions:
            return False
        
        # Check if file type should be ignored
        if file_info.file_type in self.ignored_extensions:
            return False
        
        # Check minimum file size
        if file_info.size < self.min_file_size:
            return False
        
        # Check if already compressed
        if self.marker.is_compressed(file_info.path):
            return False
        
        # Check if file still exists and is accessible
        if not os.path.exists(file_info.path):
            return False
        
        return True
    
    def calculate_priority_scores(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        Calculate priority scores for files based on access time and size
        
        Args:
            files: List of FileInfo objects
            
        Returns:
            List of FileInfo objects with calculated priority scores
        """
        current_time = time.time()
        
        for file_info in files:
            # Calculate days since last access
            days_since_access = (current_time - file_info.last_access_time) / (24 * 3600)
            
            # Normalize access time score (0-1, higher is better for compression)
            access_score = min(days_since_access / self.max_days_for_priority, 1.0)
            
            # Normalize size score (0-1, larger files get higher priority)
            max_size = max(f.size for f in files) if files else 1
            size_score = file_info.size / max_size if max_size > 0 else 0
            
            # Calculate combined priority score (weighted average)
            # 70% weight for access time, 30% weight for size
            file_info.priority_score = (access_score * 0.7) + (size_score * 0.3)
        
        return files
    
    def get_priority_files(self, directory: str = None, max_files: int = None,
                          min_priority: float = 0.3) -> List[FileInfo]:
        """
        Get files prioritized for compression
        
        Args:
            directory: Directory to scan
            max_files: Maximum number of files to return
            min_priority: Minimum priority score threshold
            
        Returns:
            List of FileInfo objects sorted by priority (highest first)
        """
        # Scan directory for compressible files
        compressible_files = self.scan_directory(directory)
        
        if not compressible_files:
            self.logger.log_info("No compressible files found")
            return []
        
        # Calculate priority scores
        files_with_scores = self.calculate_priority_scores(compressible_files)
        
        # Filter by minimum priority
        high_priority_files = [f for f in files_with_scores if f.priority_score >= min_priority]
        
        # Sort by priority score (descending)
        high_priority_files.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Limit number of files if specified
        if max_files:
            high_priority_files = high_priority_files[:max_files]
        
        self.logger.log_info(f"Selected {len(high_priority_files)} files for compression "
                           f"(min priority: {min_priority})")
        
        return high_priority_files
    
    def get_file_statistics(self, files: List[FileInfo]) -> Dict[str, Any]:
        """
        Get statistics about the file list
        
        Args:
            files: List of FileInfo objects
            
        Returns:
            Dictionary with file statistics
        """
        if not files:
            return {
                "total_files": 0,
                "total_size": 0,
                "average_size": 0,
                "oldest_access": None,
                "newest_access": None,
                "file_types": {}
            }
        
        total_size = sum(f.size for f in files)
        average_size = total_size / len(files)
        
        access_times = [f.last_access_time for f in files]
        oldest_access = min(access_times)
        newest_access = max(access_times)
        
        # Count file types
        file_types = {}
        for f in files:
            file_types[f.file_type] = file_types.get(f.file_type, 0) + 1
        
        return {
            "total_files": len(files),
            "total_size": total_size,
            "average_size": average_size,
            "oldest_access": time.ctime(oldest_access),
            "newest_access": time.ctime(newest_access),
            "file_types": file_types
        }
    
    def format_file_size(self, size_bytes: int) -> str:
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
