import os
import time
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from logger import get_logger
from compressed_marker import CompressedMarker


@dataclass
class FileInfo:
    path: str
    size: int
    last_access_time: float
    last_modified_time: float
    file_type: str
    priority_score: float = 0.0


class TanishaModule:
    def __init__(self, base_directory: str = None):
        self.base_directory = base_directory or os.getcwd()
        self.logger = get_logger()
        self.marker = CompressedMarker()
        
        self.supported_extensions = {'.txt', '.log', '.json', '.csv', '.xml', '.yaml', '.yml'}
        
        self.ignored_extensions = {
            '.zip', '.gz', '.bz2', '.xz', '.7z', '.rar', '.tar',
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv',
            '.exe', '.dll', '.so', '.dylib', '.bin'
        }
        
        self.min_file_size = 1024  # 1KB
        
        self.max_days_for_priority = 30
        
        self.logger.log_info("Tanisha module initialized")
    
    def scan_directory(self, directory: str = None, recursive: bool = True) -> List[FileInfo]:
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
        if file_info.file_type not in self.supported_extensions:
            return False
        if file_info.file_type in self.ignored_extensions:
            return False
        
        if file_info.size < self.min_file_size:
            return False
        
        if self.marker.is_compressed(file_info.path):
            return False
        
        if not os.path.exists(file_info.path):
            return False
        
        return True
    
        current_time = time.time()
        
        for file_info in files:
            days_since_access = (current_time - file_info.last_access_time) / (24 * 3600)
            
            access_score = min(days_since_access / self.max_days_for_priority, 1.0)
            
            max_size = max(f.size for f in files) if files else 1
            size_score = file_info.size / max_size if max_size > 0 else 0
            
            file_info.priority_score = (access_score * 0.7) + (size_score * 0.3)
        
        return files
    
    def get_priority_files(self, directory: str = None, max_files: int = None,
                          min_priority: float = 0.3) -> List[FileInfo]:
        compressible_files = self.scan_directory(directory)
        
        if not compressible_files:
            self.logger.log_info("No compressible files found")
            return []
        
        files_with_scores = self.calculate_priority_scores(compressible_files)
        
        high_priority_files = [f for f in files_with_scores if f.priority_score >= min_priority]
        
        high_priority_files.sort(key=lambda x: x.priority_score, reverse=True)
        
        if max_files:
            high_priority_files = high_priority_files[:max_files]
        
        self.logger.log_info(f"Selected {len(high_priority_files)} files for compression "
                           f"(min priority: {min_priority})")
        
        return high_priority_files
    
    def get_file_statistics(self, files: List[FileInfo]) -> Dict[str, Any]:

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
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
