import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from logger import get_logger


class CompressedMarker:
    
    def __init__(self, metadata_dir: str = "metadata", 
                 metadata_file: str = "compression_metadata.json"):
        self.metadata_dir = metadata_dir
        self.metadata_file = metadata_file
        self.metadata_path = os.path.join(metadata_dir, metadata_file)
        self.logger = get_logger()
        
        # Create metadata directory if it doesn't exist
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Initialize metadata file if it doesn't exist
        if not os.path.exists(self.metadata_path):
            self._create_empty_metadata()
        
        self.logger.log_info("Compressed marker system initialized")
    
    def _create_empty_metadata(self) -> None:
        """Create an empty metadata file"""
        empty_metadata = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "compressed_files": {}
        }
        
        with open(self.metadata_path, 'w') as f:
            json.dump(empty_metadata, f, indent=2)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file"""
        try:
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.log_error("metadata_load", self.metadata_path, str(e))
            self._create_empty_metadata()
            return self._load_metadata()
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save metadata to file"""
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self.logger.log_error("metadata_save", self.metadata_path, str(e))
            raise
    
    def _calculate_file_hash(self, file_path: str) -> str:
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.log_error("hash_calculation", file_path, str(e))
            return ""
    
    def mark_as_compressed(self, original_path: str, compressed_path: str,
                          original_size: int, compressed_size: int,
                          compression_method: str = "gzip") -> bool:
        try:
            metadata = self._load_metadata()
            
            # Calculate hash of original file (if it still exists)
            original_hash = ""
            if os.path.exists(original_path):
                original_hash = self._calculate_file_hash(original_path)
            
            # Create file metadata entry
            file_metadata = {
                "original_path": original_path,
                "compressed_path": compressed_path,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_method": compression_method,
                "compression_timestamp": datetime.now().isoformat(),
                "original_hash": original_hash,
                "file_type": os.path.splitext(original_path)[1].lower()
            }
            
            # Use original path as key
            metadata["compressed_files"][original_path] = file_metadata
            
            # Save updated metadata
            self._save_metadata(metadata)
            
            self.logger.log_info(f"Marked as compressed: {original_path}")
            return True
            
        except Exception as e:
            self.logger.log_error("mark_compressed", original_path, str(e))
            return False
    
    def is_compressed(self, file_path: str) -> bool:
        try:
            metadata = self._load_metadata()
            return file_path in metadata["compressed_files"]
        except Exception as e:
            self.logger.log_error("check_compressed", file_path, str(e))
            return False
    
    def get_compressed_file_info(self, original_path: str) -> Optional[Dict[str, Any]]:
        try:
            metadata = self._load_metadata()
            return metadata["compressed_files"].get(original_path)
        except Exception as e:
            self.logger.log_error("get_file_info", original_path, str(e))
            return None
    
    def get_all_compressed_files(self) -> List[Dict[str, Any]]:
        try:
            metadata = self._load_metadata()
            return list(metadata["compressed_files"].values())
        except Exception as e:
            self.logger.log_error("get_all_compressed", "metadata", str(e))
            return []
    
    def unmark_compressed(self, original_path: str) -> bool:

        try:
            metadata = self._load_metadata()
            
            if original_path in metadata["compressed_files"]:
                del metadata["compressed_files"][original_path]
                self._save_metadata(metadata)
                self.logger.log_info(f"Unmarked as compressed: {original_path}")
                return True
            else:
                self.logger.log_warning(f"File not found in compressed list: {original_path}")
                return False
                
        except Exception as e:
            self.logger.log_error("unmark_compressed", original_path, str(e))
            return False
    
    def get_compression_stats(self) -> Dict[str, Any]:
        try:
            metadata = self._load_metadata()
            compressed_files = metadata["compressed_files"]
            
            if not compressed_files:
                return {
                    "total_files": 0,
                    "total_original_size": 0,
                    "total_compressed_size": 0,
                    "total_space_saved": 0,
                    "average_compression_ratio": 0
                }
            
            total_original = sum(f["original_size"] for f in compressed_files.values())
            total_compressed = sum(f["compressed_size"] for f in compressed_files.values())
            space_saved = total_original - total_compressed
            avg_ratio = (space_saved / total_original * 100) if total_original > 0 else 0
            
            return {
                "total_files": len(compressed_files),
                "total_original_size": total_original,
                "total_compressed_size": total_compressed,
                "total_space_saved": space_saved,
                "average_compression_ratio": avg_ratio
            }
            
        except Exception as e:
            self.logger.log_error("get_stats", "metadata", str(e))
            return {}
    
    def cleanup_invalid_entries(self) -> int:
        try:
            metadata = self._load_metadata()
            compressed_files = metadata["compressed_files"].copy()
            cleaned_count = 0
            
            for original_path, file_info in compressed_files.items():
                compressed_path = file_info.get("compressed_path", "")
                
                # Check if compressed file still exists
                if not os.path.exists(compressed_path):
                    del metadata["compressed_files"][original_path]
                    cleaned_count += 1
                    self.logger.log_info(f"Cleaned up invalid entry: {original_path}")
            
            if cleaned_count > 0:
                self._save_metadata(metadata)
                self.logger.log_info(f"Cleaned up {cleaned_count} invalid entries")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.log_error("cleanup", "metadata", str(e))
            return 0
