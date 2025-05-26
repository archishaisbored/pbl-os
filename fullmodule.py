import os
import gzip
import zlib
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import psutil

print("Starting GUI script...")


class FileCompressor:
    def __init__(self, metadata_file="compression_metadata.json"):
        self.metadata_file = metadata_file
        self.metadata = self.load_metadata()

    def load_metadata(self):
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning("Warning", "Metadata file is corrupted. Starting fresh.")
        return {}

    def save_metadata(self):
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {e}")

    def compress_file(self, file_path, algorithm='gzip'):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
        # Added more common system/config file extensions to avoid compression
        if file_path.endswith(('.gz', '.zlib', '.sys', '.ini', '.dll', '.exe', '.log', '.tmp')):
            raise ValueError("File is already compressed or is a system/temporary file that should not be compressed.")

        st = os.stat(file_path)
        metadata = {
            'original_path': file_path,
            'atime': st.st_atime,
            'mtime': st.st_mtime,
            'algorithm': algorithm
        }

        ext = '.gz' if algorithm == 'gzip' else '.zlib'
        output_path = file_path + ext

        if algorithm == 'gzip':
            with open(file_path, 'rb') as f_in, gzip.open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        else: # zlib
            with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                f_out.write(zlib.compress(f_in.read()))

        if not os.path.exists(output_path):
            raise RuntimeError("Compression failed: output file not created")

        self.metadata[output_path] = metadata
        self.save_metadata()
        return output_path

    def decompress_file(self, compressed_path):
        if compressed_path not in self.metadata:
            raise ValueError("No metadata found for file")
        if not os.path.exists(compressed_path):
            raise FileNotFoundError(f"Compressed file {compressed_path} not found.")


        meta = self.metadata[compressed_path]
        original_path = meta['original_path']
        algorithm = meta['algorithm']

        # Check if the original file already exists and warn the user
        if os.path.exists(original_path):
            overwrite = messagebox.askyesno(
                "File Exists",
                f"The original file '{os.path.basename(original_path)}' already exists.\nDo you want to overwrite it?"
            )
            if not overwrite:
                return # Stop decompression if user chooses not to overwrite

        if algorithm == 'gzip':
            with gzip.open(compressed_path, 'rb') as f_in, open(original_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        else: # zlib
            with open(compressed_path, 'rb') as f_in, open(original_path, 'wb') as f_out:
                f_out.write(zlib.decompress(f_in.read()))

        os.utime(original_path, (meta['atime'], meta['mtime']))

        if not os.path.exists(original_path):
            raise RuntimeError("Decompression failed: output file not created")

        # After successful decompression, remove the compressed file and its metadata
        try:
            os.remove(compressed_path)
            del self.metadata[compressed_path]
            self.save_metadata()
        except Exception as e:
            messagebox.showwarning("Cleanup Warning", f"Successfully decompressed, but failed to clean up compressed file or metadata: {e}")

        return original_path

class CompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Compressor")
        self.compressor = FileCompressor()
        self.root.geometry("750x500")
        self.root.minsize(750, 400) # Set a minimum size for the window
        self.setup_gui()
        self.refresh()
        # Start the automatic disk usage check loop
        self.auto_check_disk_usage()

    def setup_gui(self):
        self.root.configure(bg='navy')

        style = ttk.Style()
        style.theme_use('clam') # Modern theme for a cleaner look

        # Define colors for the dark theme
        bg_color = '#2C2C2C'
        fg_color = '#E0E0E0'
        btn_color = '#444444'
        sel_color = '#555555'
        hover_color = '#555555'

        # Apply button styling
        style.configure('TButton',
                        background=btn_color,
                        foreground=fg_color,
                        font=('Segoe UI', 11, 'bold'),
                        relief='flat',
                        borderwidth=0,
                        padding=8)
        style.map('TButton',
                  background=[('active', hover_color), ('pressed', '#666666')],
                  foreground=[('disabled', '#AAAAAA')])

        # Apply Progressbar styling
        style.configure('Horizontal.TProgressbar',
                        troughcolor='#444444',
                        background='#0078D7', # A nice blue for the progress bar
                        thickness=20)

        # Apply Treeview styling
        style.configure('Treeview',
                        background='#333333',
                        fieldbackground='#333333',
                        foreground=fg_color,
                        rowheight=28,
                        borderwidth=0,
                        font=('Segoe UI', 10))
        style.map('Treeview',
                  background=[('selected', sel_color)],
                  foreground=[('selected', fg_color)])
        # Ensure the treeview area itself uses the defined background
        style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Treeview.Heading",
                        background=btn_color, # Darker header
                        foreground=fg_color,
                        font=('Segoe UI', 10, 'bold'))

        # --- GUI Layout using pack ---

        # 1. Disk usage frame (TOP)
        usage_frame = tk.Frame(self.root, bg='#4B0082') # Debugging color: Indigo
        usage_frame.pack(fill='x', padx=20, pady=(15, 10))

        self.disk_label = tk.Label(usage_frame,
                                    text="Disk Usage: --",
                                    bg='#4B0082', # Match frame color
                                    fg=fg_color,
                                    font=('Segoe UI', 12, 'bold'),
                                    anchor='w')
        self.disk_label.pack(side='left', fill='x', expand=True) # Allow label to expand horizontally

        self.disk_bar = ttk.Progressbar(usage_frame,
                                        length=300,
                                        style='Horizontal.TProgressbar')
        self.disk_bar.pack(side='right', padx=(10,0)) # Add a bit of padding

        # 2. Buttons frame (BELOW DISK USAGE)
        btn_frame = tk.Frame(self.root, bg='#8B0000', height=50, relief='raised', bd=2) # Debugging color: Dark Red, fixed height
        btn_frame.pack(fill='x', padx=20, pady=(0,10)) # Ensure adequate padding between sections
        btn_frame.pack_propagate(False) # Prevent frame from shrinking to fit content

        self.compress_btn = ttk.Button(btn_frame, text="Compress File", command=self.compress_file)
        self.decompress_btn = ttk.Button(btn_frame, text="Decompress File", command=self.decompress_file)
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.refresh)

        # Pack buttons without 'expand=True' in the button frame
        # They will take their natural size and be placed side-by-side
        self.compress_btn.pack(side='left', padx=10, pady=5)
        self.decompress_btn.pack(side='left', padx=10, pady=5)
        self.refresh_btn.pack(side='left', padx=10, pady=5)


        # 3. File list frame (Treeview) (MID-SECTION, ALLOW TO EXPAND VERTICALLY)
        tree_frame = tk.Frame(self.root, bg='#006400', bd=1, relief='sunken') # Debugging color: Dark Green
        tree_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15)) # This frame expands to fill available space

        columns = ('File','Size (Bytes)','Algorithm')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        for col, width, anchor in [('File',350,'w'), ('Size (Bytes)',120,'center'), ('Algorithm',120,'center')]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.pack(fill='both', expand=True, side='left') # Treeview itself expands within its frame

        # Add a scrollbar to the Treeview
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=tree_scrollbar.set)


        # Row tagging for alternating colors
        self.tree.tag_configure('oddrow', background='#3A3A3A')
        self.tree.tag_configure('evenrow', background='#2E2E2E')

        # Placeholder label for empty treeview
        self.placeholder = tk.Label(tree_frame,
                                    text="No compressed files.\nClick 'Compress File' to start.",
                                    bg='#006400', # Match frame color
                                    fg='#AAAAAA',
                                    font=('Segoe UI', 13, 'italic'),
                                    justify='center')
        self.placeholder.place(relx=0.5, rely=0.5, anchor='center') # Use place here as it's for an overlay within tree_frame


        # 4. Status bar for logs (BOTTOM)
        self.status_label = tk.Label(self.root,
                                      text="Status: Idle",
                                      bg='#B8860B', # Debugging color: Dark Goldenrod
                                      fg='#CCCCCC',
                                      font=('Segoe UI', 10),
                                      anchor='w',
                                      relief='sunken',
                                      bd=1)
        self.status_label.pack(fill='x', padx=20, pady=(0,10)) # Packs at the very bottom


    def log(self, message):
        self.status_label.config(text=f"Status: {message}")
        # Also print to console for debugging
        print(message)

    def refresh(self):
        self.update_disk_usage()
        self.update_file_list()

    def update_disk_usage(self):
        try:
            # Get the drive where the script is running (or a specific drive, e.g., 'C:')
            # For cross-platform, os.path.abspath(os.sep) gets the root of the current drive on Windows
            # and '/' on Unix-like systems.
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            used_gb = disk.used / (1024**3)
            total_gb = disk.total / (1024**3)
            pct = (used_gb / total_gb) * 100 if total_gb else 0
            self.disk_label.config(text=f"Disk Usage: {used_gb:.2f}/{total_gb:.2f} GB ({pct:.1f}%)")
            self.disk_bar['value'] = pct
        except Exception as e:
            self.disk_label.config(text=f"Disk Usage Error: {e}")
            self.log(f"Error getting disk usage: {e}")


    def update_file_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.compressor.metadata:
            self.placeholder.lift() # Show placeholder if no files
        else:
            self.placeholder.lower() # Hide placeholder if files exist
            idx = 0
            # Sort metadata by original path for consistent display
            sorted_metadata_items = sorted(self.compressor.metadata.items(), key=lambda item: item[0].lower())
            for path, meta in sorted_metadata_items:
                size = os.path.getsize(path) if os.path.exists(path) else 0
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.tree.insert('', 'end', iid=path, # Use path as iid for easy lookup
                                 values=(os.path.basename(path), size, meta['algorithm']),
                                 tags=(tag,))
                idx += 1

    def compress_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return # User cancelled

        # Prompt for algorithm choice
        use_gzip = messagebox.askyesno(
            "Compression Algorithm",
            "Do you want to use GZIP for compression? (Yes for GZIP, No for ZLIB)"
        )
        alg = 'gzip' if use_gzip else 'zlib'

        try:
            self.log(f"Compressing {os.path.basename(path)}...")
            out = self.compressor.compress_file(path, alg)
            messagebox.showinfo("Success", f"File compressed successfully to:\n{out}")
            self.log(f"Successfully compressed file: {os.path.basename(out)}")
            self.refresh()
        except ValueError as ve:
            messagebox.showwarning("Warning", str(ve))
            self.log(f"Compression warning: {ve}")
        except FileNotFoundError as fnfe:
            messagebox.showerror("Error", str(fnfe))
            self.log(f"Compression error: {fnfe}")
        except RuntimeError as re:
            messagebox.showerror("Error", str(re))
            self.log(f"Compression runtime error: {re}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during compression: {e}")
            self.log(f"Unexpected compression error: {e}")


    def decompress_file(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a file from the list to decompress.")
            return

        # Assuming single selection mode ('browse'), get the first selected item
        comp_path_to_decompress = selected_items[0]

        try:
            self.log(f"Decompressing {os.path.basename(comp_path_to_decompress)}...")
            orig = self.compressor.decompress_file(comp_path_to_decompress)
            messagebox.showinfo("Success", f"File decompressed successfully to:\n{orig}")
            self.log(f"Successfully decompressed file: {os.path.basename(orig)}")
            self.refresh()
        except ValueError as ve:
            messagebox.showwarning("Warning", str(ve))
            self.log(f"Decompression warning: {ve}")
        except FileNotFoundError as fnfe:
            messagebox.showerror("Error", str(fnfe))
            self.log(f"Decompression error: {fnfe}")
        except RuntimeError as re:
            messagebox.showerror("Error", str(re))
            self.log(f"Decompression runtime error: {re}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during decompression: {e}")
            self.log(f"Unexpected decompression error: {e}")

    def auto_check_disk_usage(self):
        # This function runs periodically to check disk usage and potentially auto-compress
        try:
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            pct_used = disk.percent
            threshold = 85.0  # percent usage to trigger auto-compression

            # Update the disk usage display
            self.update_disk_usage()

            if pct_used >= threshold:
                self.log(f"Disk usage is {pct_used:.1f}%, at or above threshold ({threshold:.1f}%). Checking for files to auto-compress...")
                compressed_something = False
                # Iterate through existing metadata to find original files that are NOT yet compressed
                # and are still present on disk.
                # Use list(self.compressor.metadata.items()) to iterate over a copy,
                # as the dictionary might change during compression.
                for compressed_file_path, meta in list(self.compressor.metadata.items()):
                    original_file_path = meta['original_path']

                    # Check if the original file exists and the *compressed* version doesn't
                    # (meaning it was decompressed or never compressed after initial metadata saving)
                    if os.path.exists(original_file_path) and not os.path.exists(compressed_file_path):
                        # Ensure we don't compress system/program files
                        if not original_file_path.endswith(('.sys', '.ini', '.dll', '.exe', '.log', '.tmp')):
                            try:
                                self.log(f"Attempting to auto-compress: {os.path.basename(original_file_path)}")
                                out = self.compressor.compress_file(original_file_path, meta['algorithm'])
                                self.log(f"Auto compressed: {os.path.basename(out)}")
                                compressed_something = True
                                # Optional: remove original file after successful auto-compression
                                # os.remove(original_file_path)
                            except Exception as e:
                                self.log(f"Auto compression error for {os.path.basename(original_file_path)}: {e}")
                    elif os.path.exists(compressed_file_path):
                        # If the compressed file already exists, it's fine.
                        pass
                    else:
                        # If neither original nor compressed file exists, metadata might be stale.
                        # Consider removing stale metadata here if needed, but be careful.
                        self.log(f"Warning: Neither original '{os.path.basename(original_file_path)}' nor compressed '{os.path.basename(compressed_file_path)}' found for metadata entry. Metadata might be stale.")
                        # This could be handled by a periodic metadata cleanup function.

                if compressed_something:
                    self.log("Auto-compression completed. Refreshing file list.")
                    self.refresh()
                else:
                    self.log("Disk usage high, but no eligible files found for auto-compression.")
            else:
                self.log(f"Disk usage normal ({pct_used:.1f}%).")

        except Exception as e:
            self.log(f"Auto check disk usage error: {e}")

        # Schedule the next check
        self.root.after(10000, self.auto_check_disk_usage) # Check every 10 seconds (10000 ms)


if __name__ == "__main__":
    root = tk.Tk()
    app = CompressorGUI(root)
    root.mainloop()
