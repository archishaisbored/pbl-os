import os
import json
import logging
from datetime import datetime
from typing import List, Tuple

# --- Configuration ---
WATCH_DIRECTORY = "/Users/tanishachauhan/Downloads/TestFiles"  
LOG_FILE = "smartcompress.log"
METADATA_FILE = "metadata.json"
PRIORITY_LIMIT = 10


# ---  Logging ---
def setup_logger():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def log_event(message: str):
    logging.info(message)


def log_error(message: str):
    logging.error(message)


# --- File Prioritization ---
def get_file_stats(directory: str) -> List[Tuple[str, float, int]]:
    file_stats = []
    for root, _, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            if os.path.isfile(path) and not path.endswith('.gz'):
                try:
                    access_time = os.path.getatime(path)
                    size = os.path.getsize(path)
                    file_stats.append((path, access_time, size))
                except Exception as e:
                    log_error(f"Error reading file: {path} - {e}")
    return file_stats


def prioritize_files(file_stats: List[Tuple[str, float, int]], limit: int = 10) -> List[str]:
    sorted_files = sorted(file_stats, key=lambda x: (x[1], -x[2]))
    return [entry[0] for entry in sorted_files[:limit]]


# --- Metadata Management ---
def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return {}
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_file_metadata(original_path: str, compressed_path: str, original_size: int):
    data = load_metadata()
    data[compressed_path] = {
        "original_path": original_path,
        "original_size": original_size,
        "compressed_time": datetime.now().isoformat()
    }
    save_metadata(data)


# ---  Test/Demo Execution ---
if __name__ == "__main__":
    setup_logger()


    files_info = get_file_stats(WATCH_DIRECTORY)
    files_to_compress = prioritize_files(files_info, PRIORITY_LIMIT)

    for file_path in files_to_compress:
        try:
            compressed_path = file_path + ".gz"  #compression for test
            original_size = os.path.getsize(file_path)
            add_file_metadata(file_path, compressed_path, original_size)
            log_event(f"Marked for compression: {file_path}")
        except Exception as e:
            log_error(f"Error processing {file_path}: {e}")

    log_event("Finished processing files.")
