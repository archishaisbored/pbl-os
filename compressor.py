"""
SmartCompress FS - GUI Module
Tkinter-based graphical user interface for manual control and monitoring
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from typing import Dict, Any
from smartcompress import SmartCompressFS
from decompression import DecompressionManager
from logger import get_logger


class SmartCompressGUI:
    """GUI application for SmartCompress FS"""

    def __init__(self):
        """Initialize the GUI application"""
        self.logger = get_logger()
        self.smartcompress = None
        self.decompressor = DecompressionManager()

        # Create main window
        self.root = tk.Tk()
        self.root.title("SmartCompress FS - Intelligent File Compression")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Dark theme colors
        self.colors = {
            'bg_dark': '#1a1a1a',      # Darkest background
            'bg_medium': '#2d2d2d',    # Medium background
            'bg_light': '#404040',     # Lighter background
            'fg_white': '#ffffff',     # White text
            'fg_grey': '#cccccc',      # Light grey text
            'accent': '#4a9eff',       # Blue accent
            'success': '#4caf50',      # Green for success
            'warning': '#ff9800',      # Orange for warning
            'error': '#f44336'         # Red for error
        }

        # Configure root window
        self.root.configure(bg=self.colors['bg_dark'])

        # Variables for GUI updates
        self.status_var = tk.StringVar()
        self.disk_usage_var = tk.StringVar()
        self.monitoring_var = tk.StringVar()

        # Configure ttk styles for dark theme
        self.setup_styles()

        # Initialize GUI components
        self.setup_gui()
        self.update_status("Ready")

        # Start periodic updates
        self.start_periodic_updates()

        self.logger.log_info("SmartCompress GUI initialized")

    def setup_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()

        # Configure frame styles
        style.configure('Dark.TFrame',
                       background=self.colors['bg_medium'],
                       borderwidth=1,
                       relief='solid')

        style.configure('Light.TFrame',
                       background=self.colors['bg_light'],
                       borderwidth=1,
                       relief='solid')

        # Configure label styles
        style.configure('Dark.TLabel',
                       background=self.colors['bg_medium'],
                       foreground=self.colors['fg_white'],
                       font=('Arial', 10))

        style.configure('Title.TLabel',
                       background=self.colors['bg_dark'],
                       foreground=self.colors['fg_white'],
                       font=('Arial', 16, 'bold'))

        style.configure('Status.TLabel',
                       background=self.colors['bg_medium'],
                       foreground=self.colors['accent'],
                       font=('Arial', 10, 'bold'))

        # Configure button styles
        style.configure('Dark.TButton',
                       background='#808080',  # Black background
                       foreground='#808080',  # White text
                       borderwidth=1,
                       focuscolor='none',
                       font=('Arial', 10, 'bold'))

        style.map('Dark.TButton',
                       background=[('active', '#333333'),  # Slightly lighter black when active
                      ('pressed', '#808080')],
                       foreground=[('active', '#FFFFFF'),  # Keep text white on hover/active
                      ('pressed', '#FFFFFF')])


        # Configure entry styles
        style.configure('Dark.TEntry',
                       fieldbackground=self.colors['bg_light'],
                       foreground=self.colors['fg_white'],
                       borderwidth=1,
                       insertcolor=self.colors['fg_white'])

        # Configure labelframe styles
        style.configure('Dark.TLabelframe',
                       background=self.colors['bg_medium'],
                       foreground=self.colors['fg_white'],
                       borderwidth=2,
                       relief='groove')

        style.configure('Dark.TLabelframe.Label',
                       background=self.colors['bg_medium'],
                       foreground=self.colors['fg_white'],
                       font=('Arial', 10, 'bold'))

        # Configure progressbar styles
        style.configure('Dark.Horizontal.TProgressbar',
                       background=self.colors['accent'],
                       troughcolor=self.colors['bg_light'],
                       borderwidth=1,
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'])

    def setup_gui(self):
        """Set up the GUI layout and components"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10", style='Dark.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="SmartCompress FS",
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Directory selection
        dir_frame = ttk.LabelFrame(main_frame, text="Directory Settings",
                                  padding="5", style='Dark.TLabelframe')
        dir_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)

        ttk.Label(dir_frame, text="Base Directory:",
                 style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.dir_var = tk.StringVar(value=os.getcwd())
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=50,
                                  style='Dark.TEntry')
        self.dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))

        browse_btn = tk.Button(dir_frame, text="Browse",
                              command=self.browse_directory,
                              bg='black', 
                              font=('Arial', 12, 'bold'))
        browse_btn.grid(row=0, column=2, padx=(5, 0))

        init_btn = tk.Button(dir_frame, text="Initialize",
                            command=self.initialize_smartcompress,
                            bg='black', 
                            font=('Arial', 12, 'bold'))
        init_btn.grid(row=0, column=3, padx=(5, 0))

        # Status information
        status_frame = ttk.LabelFrame(main_frame, text="System Status",
                                     padding="5", style='Dark.TLabelframe')
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Status:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.status_var, style='Status.TLabel').grid(row=0, column=1, sticky=tk.W)

        ttk.Label(status_frame, text="Disk Usage:", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.disk_usage_var, style='Status.TLabel').grid(row=1, column=1, sticky=tk.W)

        ttk.Label(status_frame, text="Monitoring:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.monitoring_var, style='Status.TLabel').grid(row=2, column=1, sticky=tk.W)

        # Control buttons
        button_frame = ttk.LabelFrame(main_frame, text="Controls",
                                     padding="5", style='Dark.TLabelframe')
        button_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # First row of buttons
        scan_btn = tk.Button(button_frame, text="Scan Disk",
                            command=self.scan_disk,
                            bg='black',
                            font=('Arial', 12, 'bold'))
        scan_btn.grid(row=0, column=0, padx=(0, 5), pady=(0, 5))

        compress_btn = tk.Button(button_frame, text="Compress Now",
                                command=self.compress_now,
                                bg='black', 
                                font=('Arial', 12, 'bold'))
        compress_btn.grid(row=0, column=1, padx=5, pady=(0, 5))

        decompress_btn = tk.Button(button_frame, text="Decompress All",
                                  command=self.decompress_all,
                                  bg='black', 
                                  font=('Arial', 12, 'bold'))
        decompress_btn.grid(row=0, column=2, padx=5, pady=(0, 5))

        # Second row of buttons
        self.monitor_button = tk.Button(button_frame, text="Start Monitoring",
                                       command=self.toggle_monitoring,
                                       bg='black', 
                                       font=('Arial', 12, 'bold'))
        self.monitor_button.grid(row=1, column=0, padx=(0, 5), pady=(5, 0))

        stats_btn = tk.Button(button_frame, text="View Stats",
                             command=self.view_statistics,
                             bg='black', 
                             font=('Arial', 12, 'bold'))
        stats_btn.grid(row=1, column=1, padx=5, pady=(5, 0))

        clear_btn = tk.Button(button_frame, text="Clear Logs",
                             command=self.clear_logs,
                             bg='black', 
                             font=('Arial', 12, 'bold'))
        clear_btn.grid(row=1, column=2, padx=5, pady=(5, 0))

        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log",
                                  padding="5", style='Dark.TLabelframe')
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                 bg=self.colors['bg_light'],
                                                 fg=self.colors['fg_white'],
                                                 insertbackground=self.colors['fg_white'],
                                                 selectbackground=self.colors['accent'],
                                                 selectforeground=self.colors['fg_white'],
                                                 font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate',
                                       style='Dark.Horizontal.TProgressbar')
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)

    def initialize_smartcompress(self):
        """Initialize SmartCompress with selected directory"""
        try:
            directory = self.dir_var.get()
            if not directory or not os.path.exists(directory):
                messagebox.showerror("Error", "Please select a valid directory")
                return

            self.smartcompress = SmartCompressFS(base_directory=directory)
            self.update_status("Initialized")
            self.log_message(f"SmartCompress initialized for directory: {directory}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize: {str(e)}")
            self.log_message(f"Initialization error: {str(e)}")

    def scan_disk(self):
        """Scan disk and display results"""
        if not self.smartcompress:
            messagebox.showwarning("Warning", "Please initialize SmartCompress first")
            return

        def scan_thread():
            try:
                self.progress.start()
                self.update_status("Scanning...")

                # Get disk usage
                disk_info = self.smartcompress.get_disk_usage()

                # Get compressible files
                priority_files = self.smartcompress.tanisha.get_priority_files()

                # Update display
                self.update_disk_usage(disk_info)

                message = (f"Scan completed:\n"
                          f"- Found {len(priority_files)} compressible files\n"
                          f"- Disk usage: {disk_info.get('used_percent', 0):.1f}%")

                self.log_message(message)
                self.update_status("Scan completed")

            except Exception as e:
                self.log_message(f"Scan error: {str(e)}")
                self.update_status("Scan failed")
            finally:
                self.progress.stop()

        threading.Thread(target=scan_thread, daemon=True).start()

    def compress_now(self):
        """Manually trigger compression"""
        if not self.smartcompress:
            messagebox.showwarning("Warning", "Please initialize SmartCompress first")
            return

        def compress_thread():
            try:
                self.progress.start()
                self.update_status("Compressing...")

                results = self.smartcompress.compress_files()

                message = (f"Compression completed:\n"
                          f"- Files processed: {results['total_files']}\n"
                          f"- Successful: {results['successful']}\n"
                          f"- Failed: {results['failed']}")

                self.log_message(message)
                self.update_status("Compression completed")

                if results['successful'] > 0:
                    messagebox.showinfo("Success",
                                      f"Successfully compressed {results['successful']} files")

            except Exception as e:
                self.log_message(f"Compression error: {str(e)}")
                self.update_status("Compression failed")
                messagebox.showerror("Error", f"Compression failed: {str(e)}")
            finally:
                self.progress.stop()

        threading.Thread(target=compress_thread, daemon=True).start()

    def decompress_all(self):
        """Decompress all compressed files"""
        # Confirm action
        if not messagebox.askyesno("Confirm",
                                  "Are you sure you want to decompress all files?"):
            return

        def decompress_thread():
            try:
                self.progress.start()
                self.update_status("Decompressing...")

                successful, failed = self.decompressor.decompress_all()

                message = (f"Decompression completed:\n"
                          f"- Successful: {successful}\n"
                          f"- Failed: {failed}")

                self.log_message(message)
                self.update_status("Decompression completed")

                if successful > 0:
                    messagebox.showinfo("Success",
                                      f"Successfully decompressed {successful} files")

            except Exception as e:
                self.log_message(f"Decompression error: {str(e)}")
                self.update_status("Decompression failed")
                messagebox.showerror("Error", f"Decompression failed: {str(e)}")
            finally:
                self.progress.stop()

        threading.Thread(target=decompress_thread, daemon=True).start()

    def toggle_monitoring(self):
        """Start or stop monitoring"""
        if not self.smartcompress:
            messagebox.showwarning("Warning", "Please initialize SmartCompress first")
            return

        try:
            if not self.smartcompress.monitoring:
                if self.smartcompress.start_monitoring():
                    self.monitor_button.config(text="Stop Monitoring")
                    self.log_message("Monitoring started")
                else:
                    messagebox.showerror("Error", "Failed to start monitoring")
            else:
                if self.smartcompress.stop_monitoring():
                    self.monitor_button.config(text="Start Monitoring")
                    self.log_message("Monitoring stopped")
                else:
                    messagebox.showerror("Error", "Failed to stop monitoring")

        except Exception as e:
            messagebox.showerror("Error", f"Monitoring error: {str(e)}")

    def view_statistics(self):
        """Display compression statistics"""
        try:
            stats = self.smartcompress.marker.get_compression_stats() if self.smartcompress else {}

            if not stats or stats.get('total_files', 0) == 0:
                messagebox.showinfo("Statistics", "No compression statistics available")
                return

            stats_text = (f"Compression Statistics:\n\n"
                         f"Total compressed files: {stats['total_files']}\n"
                         f"Original size: {self._format_size(stats['total_original_size'])}\n"
                         f"Compressed size: {self._format_size(stats['total_compressed_size'])}\n"
                         f"Space saved: {self._format_size(stats['total_space_saved'])}\n"
                         f"Average compression ratio: {stats['average_compression_ratio']:.1f}%")

            messagebox.showinfo("Statistics", stats_text)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get statistics: {str(e)}")

    def clear_logs(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)

    def update_status(self, status: str):
        """Update status display"""
        self.status_var.set(status)

    def update_disk_usage(self, disk_info: Dict[str, Any]):
        """Update disk usage display"""
        if disk_info:
            usage_text = f"{disk_info['used_percent']:.1f}% ({self._format_size(disk_info['free_bytes'])} free)"
            self.disk_usage_var.set(usage_text)

    def log_message(self, message: str, msg_type: str = "info"):
        """Add message to log display with color coding"""
        timestamp = time.strftime("%H:%M:%S")

        # Configure text tags for different message types
        self.log_text.tag_configure("info", foreground=self.colors['fg_white'])
        self.log_text.tag_configure("success", foreground=self.colors['success'])
        self.log_text.tag_configure("warning", foreground=self.colors['warning'])
        self.log_text.tag_configure("error", foreground=self.colors['error'])
        self.log_text.tag_configure("accent", foreground=self.colors['accent'])

        # Determine message type based on content if not specified
        if msg_type == "info":
            if "✓" in message or "successful" in message.lower():
                msg_type = "success"
            elif "⚠" in message or "warning" in message.lower():
                msg_type = "warning"
            elif "✗" in message or "error" in message.lower() or "failed" in message.lower():
                msg_type = "error"
            elif "compression" in message.lower() or "decompression" in message.lower():
                msg_type = "accent"

        # Insert message with appropriate tag
        full_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, full_message, msg_type)
        self.log_text.see(tk.END)

    def start_periodic_updates(self):
        """Start periodic GUI updates"""
        def update():
            try:
                # Update monitoring status
                if self.smartcompress:
                    status = "Active" if self.smartcompress.monitoring else "Inactive"
                    self.monitoring_var.set(status)

                    # Update disk usage
                    disk_info = self.smartcompress.get_disk_usage()
                    self.update_disk_usage(disk_info)

            except Exception as e:
                pass  # Ignore errors in periodic updates

            # Schedule next update
            self.root.after(5000, update)  # Update every 5 seconds

        update()

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def run(self):
        """Start the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.log_info("GUI application interrupted")
        finally:
            if self.smartcompress and self.smartcompress.monitoring:
                self.smartcompress.stop_monitoring()


def main():
    """Main entry point for GUI application"""
    import os
    app = SmartCompressGUI()
    app.run()


if __name__ == "__main__":
    main()
