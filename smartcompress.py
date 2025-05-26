import os
import shutil
import psutil
import time
import gzip
import logging
from datetime import datetime


WATCH_DIRECTORY = "/Users/manpreetwalia/Desktop/TestFiles"
DISK_PATH = "/"
THRESHOLD_PERCENT = 99  
LOG_FILE = "smartcompress.log"


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

def get_disk_free_percent(path):
    usage = psutil.disk_usage(path)
    return usage.free / usage.total * 100

def should_compress(path):
    try:
       
        return os.path.isfile(path) and not path.endswith('.gz')
    except Exception as e:
        logging.error(f"Error checking file: {path} - {e}")
        return False

def compress_file(path):
    try:
        with open(path, 'rb') as f_in:
            with gzip.open(path + '.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(path)
        logging.info(f"Compressed: {path}")
    except Exception as e:
        logging.error(f"Compression failed for {path}: {e}")

def find_files_to_compress(directory, limit=10):
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if should_compress(full_path):
                last_access = os.path.getatime(full_path)
                size = os.path.getsize(full_path)
                all_files.append((full_path, last_access, size))
    
   
    all_files.sort(key=lambda x: (x[1], -x[2]))
    return [file[0] for file in all_files[:limit]]

def monitor_and_compress():
    while True:
        free_percent = get_disk_free_percent(DISK_PATH)
        print(f"Free space: {free_percent:.2f}%")
        
        if free_percent < THRESHOLD_PERCENT:
            logging.warning("Low disk space! Starting compression cycle.")
            files = find_files_to_compress(WATCH_DIRECTORY)
            if files:
                for file_path in files:
                    compress_file(file_path)
            else:
                logging.info("No eligible files to compress.")
        time.sleep(60)  

if __name__ == "__main__":
    monitor_and_compress()
