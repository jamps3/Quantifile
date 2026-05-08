import threading
import time
import tkinter as tk
from tkinter import ttk

from actions_controller import ActionsMixin
from render_controller import RenderMixin
from scan_controller import ScanMixin
from settings_controller import SettingsMixin


class Quantifile(SettingsMixin, ScanMixin, RenderMixin, ActionsMixin, tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Quantifile")

        self.load_settings()
        self.apply_geometry()

        self.root_node = None
        self.current_node = None
        self.rect_nodes = {}
        self.dark_mode = False

        # Bookmarks: dict of path -> scanned root node
        self.bookmarks = {}
        self.bookmarked_paths = []  # ordered list for UI

        self.create_ui()
        self.apply_theme()
        self.load_bookmarks()

        # Save window position on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_search_ui(self):
        # Search row
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=4, pady=(0, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_search())

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 4))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left", padx=(0, 4))

        self.search_type_var = tk.StringVar(value="name")
        ttk.Radiobutton(search_frame, text="Name", variable=self.search_type_var, value="name",
                        command=self.apply_search).pack(side="left", padx=2)
        ttk.Radiobutton(search_frame, text="Size ≥ ", variable=self.search_type_var, value="size",
                        command=self.apply_search).pack(side="left", padx=2)

        self.min_size_var = tk.StringVar(value="1MB")
        self.size_entry = ttk.Entry(search_frame, textvariable=self.min_size_var, width=8)
        self.size_entry.pack(side="left", padx=(0, 4))
        self.size_entry.bind("<Return>", lambda e: self.apply_search())
        self.size_entry.bind("<KeyRelease>", lambda e: self.apply_search() if e.keysym in ("Return", "KP_Enter") else None)

        ttk.Button(search_frame, text="×", width=2, command=self.clear_search).pack(side="left", padx=2)

    def create_status_ui(self):
        # Status row
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=4, pady=(0, 4))

        self.status = ttk.Label(status_frame, text="Choose a folder to scan", anchor="w")
        self.status.pack(fill="x")

    def create_bookmarks_ui(self):
        # Create bookmarks UI in the tab
        self.create_bookmarks_tab_ui()

        # Create bookmarks UI in the side panel
        self.create_bookmarks_panel_ui()

    def create_bookmarks_tab_ui(self):
        # Bookmarks tab toolbar
        bookmarks_toolbar = ttk.Frame(self.bookmarks_tab)
        bookmarks_toolbar.pack(fill="x", padx=4, pady=4)

        ttk.Button(bookmarks_toolbar, text="Add Current", command=self.add_current_to_bookmarks).pack(side="left", padx=2)
        ttk.Button(bookmarks_toolbar, text="Remove Selected", command=self.remove_selected_bookmark).pack(side="left", padx=2)
        ttk.Button(bookmarks_toolbar, text="Browse Selected", command=self.browse_selected_bookmark).pack(side="left", padx=2)

        # Bookmarks listbox with scrollbar for tab
        bookmarks_frame = ttk.Frame(self.bookmarks_tab)
        bookmarks_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.bookmarks_tab_listbox = tk.Listbox(bookmarks_frame, selectmode="single")
        self.bookmarks_tab_listbox.pack(side="left", fill="both", expand=True)

        bookmarks_scrollbar = ttk.Scrollbar(bookmarks_frame, orient="vertical", command=self.bookmarks_tab_listbox.yview)
        bookmarks_scrollbar.pack(side="right", fill="y")
        self.bookmarks_tab_listbox.configure(yscrollcommand=bookmarks_scrollbar.set)

        self.bookmarks_tab_listbox.bind("<Double-Button-1>", self.on_bookmark_double_click)
        self.bookmarks_tab_listbox.bind("<Return>", self.browse_selected_bookmark)

    def create_bookmarks_panel_ui(self):
        # Bookmarks panel toolbar
        bookmarks_toolbar = ttk.Frame(self.bookmarks_panel)
        bookmarks_toolbar.pack(fill="x", padx=4, pady=4)

        ttk.Button(bookmarks_toolbar, text="Add Current", command=self.add_current_to_bookmarks).pack(side="left", padx=2)
        ttk.Button(bookmarks_toolbar, text="Remove Selected", command=self.remove_selected_bookmark).pack(side="left", padx=2)

        # Bookmarks listbox with scrollbar for panel
        bookmarks_frame = ttk.Frame(self.bookmarks_panel)
        bookmarks_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.bookmarks_panel_listbox = tk.Listbox(bookmarks_frame, selectmode="single")
        self.bookmarks_panel_listbox.pack(side="left", fill="both", expand=True)

        bookmarks_scrollbar = ttk.Scrollbar(bookmarks_frame, orient="vertical", command=self.bookmarks_panel_listbox.yview)
        bookmarks_scrollbar.pack(side="right", fill="y")
        self.bookmarks_panel_listbox.configure(yscrollcommand=bookmarks_scrollbar.set)

        self.bookmarks_panel_listbox.bind("<Double-Button-1>", self.on_bookmark_double_click)
        self.bookmarks_panel_listbox.bind("<Return>", self.browse_selected_bookmark)

    def truncate_text(self, text):
        import tkinter.font as tkfont
        # Get available width for text (window width minus padding)
        available_width = max(100, self.winfo_width() - 20)  # Minimum 100
        font_str = self.status.cget("font")
        font = tkfont.Font(font=font_str)
        full_width = font.measure(text)
        if full_width <= available_width:
            return text
        # Binary search for max length
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            truncated = text[:mid] + "..."
            width = font.measure(truncated)
            if width <= available_width:
                low = mid
            else:
                high = mid - 1
        return text[:low] + "..."

    def create_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Open Folder", command=self.choose_folder).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Quick Browse", command=self.quick_browse).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Rescan", command=self.rescan).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Zoom Out", command=self.zoom_out).pack(side="left", padx=4, pady=4)
        self.quick_zoom_button = ttk.Button(toolbar, text="Quick Zoom (OFF)", command=self.toggle_quick_zoom)
        self.quick_zoom_button.pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Open Selected", command=self.open_selected).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4, pady=4)
        self.free_space_button = ttk.Button(toolbar, text="Free Space (OFF)", command=self.toggle_free_space)
        self.free_space_button.pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Export SVG", command=self.export_svg).pack(side="left", padx=4, pady=4)
        self.bookmarks_toggle_button = ttk.Button(toolbar, text="Bookmarks (HIDDEN)", command=self.toggle_bookmarks_panel)
        self.bookmarks_toggle_button.pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Settings", command=self.show_settings).pack(side="right", padx=4, pady=4)
        ttk.Button(toolbar, text="About", command=self.show_about).pack(side="right", padx=4, pady=4)

        self.create_search_ui()
        self.create_status_ui()

        # Progress bar (initially hidden)
        self.progress_frame = ttk.Frame(self)
        self.progress = ttk.Progressbar(self.progress_frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=5, pady=2)
        self.progress_label = ttk.Label(self.progress_frame, text="", anchor="center")
        self.progress_label.pack(fill="x", padx=5)
        self.cancel_button = ttk.Button(self.progress_frame, text="Cancel Scan", command=self.cancel_scan)
        self.cancel_button.pack(pady=2)
        self.progress_frame.pack_forget()

        # Create main paned window for split view
        self.main_paned = ttk.PanedWindow(self, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True)

        # Left panel for bookmarks (initially hidden)
        self.bookmarks_panel = ttk.Frame(self.main_paned)
        self.bookmarks_visible = False

        # Right panel for main content
        self.main_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(self.main_panel)

        self.main_notebook = ttk.Notebook(self.main_panel)
        self.main_notebook.pack(fill="both", expand=True)

        self.treemap_tab = ttk.Frame(self.main_notebook)
        self.log_tab = ttk.Frame(self.main_notebook)
        self.bookmarks_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.treemap_tab, text="Treemap")
        self.main_notebook.add(self.log_tab, text="Log")
        self.main_notebook.add(self.bookmarks_tab, text="Bookmarks")

        self.canvas = tk.Canvas(self.treemap_tab, bg="white")
        self.canvas.pack(fill="both", expand=True)

        self.log_toolbar = ttk.Frame(self.log_tab)
        self.log_toolbar.pack(fill="x", padx=4, pady=4)
        ttk.Button(self.log_toolbar, text="Clear Log", command=self.clear_log).pack(side="left")

        self.log_text = tk.Text(self.log_tab, height=8, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(0, 4))
        log_scrollbar = ttk.Scrollbar(self.log_tab, orient="vertical", command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=(0, 4))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        # Create bookmarks UI in both panel and tab
        self.create_bookmarks_ui()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Configure>", self.on_resize)

        self.bind("<BackSpace>", lambda e: self.zoom_out())
        self.bind("<Return>", self.on_enter)
        self.bind("<KP_Enter>", self.on_enter)
        self.bind("<Left>", self.on_arrow)
        self.bind("<Right>", self.on_arrow)
        self.bind("<Up>", self.on_arrow)
        self.bind("<Down>", self.on_arrow)

        self.selected_node = None
        self.scan_aborted = False
        self.nodes_scanned = 0
        self._nodes_scanned_lock = threading.Lock()
        self._resize_job = None

        # Search state
        self.search_matches = set()  # Set of node paths that match the current search
        self.current_search = ""
        self.search_active = False

        # Right-click menu and toggle
        self.quick_zoom_mode = False  # False = show menu, True = instant zoom out
        self.context_menu = None

        # Free space toggle
        self.show_free_space_toggle = False

        self.log_message("Ready. Choose a folder to scan.", "INFO", show_log=False)

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def log_message(self, message, level="INFO", show_log=False):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {level}: {message}\n"

        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")

        if hasattr(self, "status"):
            self.status.config(text=message)

        if show_log and hasattr(self, "main_notebook") and hasattr(self, "log_tab"):
            self.main_notebook.select(self.log_tab)

    def log_from_worker(self, message, level="WARNING", show_log=None):
        if show_log is None:
            show_log = level == "ERROR"
        self.after(0, lambda: self.log_message(message, level, show_log))


