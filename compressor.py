import os
import gzip
import zlib
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import psutil

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
        if file_path.endswith(('.gz', '.zlib', '.sys', '.ini')):
            raise ValueError("File is already compressed or is a system file")

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
        else:
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

        meta = self.metadata[compressed_path]
        original_path = meta['original_path']
        algorithm = meta['algorithm']

        if algorithm == 'gzip':
            with gzip.open(compressed_path, 'rb') as f_in, open(original_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            with open(compressed_path, 'rb') as f_in, open(original_path, 'wb') as f_out:
                f_out.write(zlib.decompress(f_in.read()))

        os.utime(original_path, (meta['atime'], meta['mtime']))

        if not os.path.exists(original_path):
            raise RuntimeError("Decompression failed: output file not created")

        del self.metadata[compressed_path]
        self.save_metadata()
        return original_path

class CompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Compressor")
        self.compressor = FileCompressor()
        self.root.configure(bg='#2C2C2C')
        self.root.geometry("700x450")
        self.setup_gui()
        self.refresh()

    def setup_gui(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg_color = '#2C2C2C'
        fg_color = '#FFFFFF'
        btn_color = '#444444'
        sel_color = '#666666'

        # Button styling
        style.configure('TButton', background=btn_color, foreground=fg_color, font=('Arial',11), relief='flat', borderwidth=0)
        style.map('TButton', background=[('active', '#555555')])

        # Progressbar styling: restore blue fill
        style.configure('Horizontal.TProgressbar', troughcolor='#444444', background='#0078D7')

        # Treeview styling
        style.configure('Treeview', background='#333333', fieldbackground='#333333', foreground=fg_color, rowheight=25, borderwidth=0)
        style.map('Treeview', background=[('selected', sel_color)], foreground=[('selected', fg_color)])
        style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])

        # Disk usage frame
        usage_frame = tk.Frame(self.root, bg=bg_color)
        usage_frame.pack(fill='x', padx=15, pady=10)

        self.disk_label = tk.Label(usage_frame, text="Disk Usage: --", bg=bg_color, fg=fg_color, font=('Arial',12))
        self.disk_label.pack(side='left')

        self.disk_bar = ttk.Progressbar(usage_frame, length=250, style='Horizontal.TProgressbar')
        self.disk_bar.pack(side='right')

        # File list frame
        tree_frame = tk.Frame(self.root, bg=bg_color)
        tree_frame.pack(fill='both', expand=True, padx=15, pady=10)

        columns = ('File','Size','Algorithm')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        for col, width, anchor in [('File',300,'w'),('Size',120,'center'),('Algorithm',100,'center')]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.pack(fill='both', expand=True)

        self.tree.tag_configure('oddrow', background='#3A3A3A')
        self.tree.tag_configure('evenrow', background='#2E2E2E')

        self.placeholder = tk.Label(tree_frame, text="No compressed files.\nClick 'Compress File' to start.", bg=bg_color, fg='#AAAAAA', font=('Arial',12,'italic'))
        self.placeholder.place(relx=0.5, rely=0.5, anchor='center')

        # Buttons frame
        btn_frame = tk.Frame(self.root, bg=bg_color)
        btn_frame.pack(fill='x', padx=15, pady=10)

        compress_btn = ttk.Button(btn_frame, text="Compress File", command=self.compress_file)
        decompress_btn = ttk.Button(btn_frame, text="Decompress File", command=self.decompress_file)
        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.refresh)

        for btn in (compress_btn, decompress_btn, refresh_btn):
            btn.pack(side='left', expand=True, padx=0, pady=0)

    def refresh(self):
        self.update_disk_usage()
        self.update_file_list()

    def update_disk_usage(self):
        try:
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            used_gb = disk.used / (1024**3)
            total_gb = disk.total / (1024**3)
            pct = (used_gb / total_gb) * 100 if total_gb else 0
            self.disk_label.config(text=f"Disk Usage: {used_gb:.2f}/{total_gb:.2f} GB ({pct:.1f}%)")
            self.disk_bar['value'] = pct
        except Exception as e:
            self.disk_label.config(text=f"Disk Usage Error: {e}")

    def update_file_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.compressor.metadata:
            self.placeholder.lift()
        else:
            self.placeholder.lower()
            for idx,(path,meta) in enumerate(self.compressor.metadata.items()):
                size = os.path.getsize(path) if os.path.exists(path) else 0
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.tree.insert('', 'end', iid=path, values=(os.path.basename(path), size, meta['algorithm']), tags=(tag,))

    def compress_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        use_gzip = messagebox.askyesno("Algorithm", "Use GZIP? (Yes for GZIP, No for ZLIB)")
        alg = 'gzip' if use_gzip else 'zlib'
        try:
            out = self.compressor.compress_file(path, alg)
            messagebox.showinfo("Success", f"Compressed to:\n{out}")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def decompress_file(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a file to decompress")
            return
        comp = selected[0]
        try:
            orig = self.compressor.decompress_file(comp)
            messagebox.showinfo("Success", f"Decompressed to:\n{orig}")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CompressorGUI(root)
    root.mainloop()
