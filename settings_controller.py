import json
import tkinter as tk
from tkinter import ttk


class SettingsMixin:
    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        defaults = {
            "dark_mode": False,
            "min_density": 1,
            "disable_delete": False,
            "remember_window_pos": True,
            "fullscreen": False,
            "show_scan_progress": True,
            "max_scan_threads": 6,
            "animated_zoom": False,
            "auto_rescan_on_delete": True,
            "dir_color": "",
            "file_color": "",
            "selection_color": "#ffcc00",
            "outline_color": "",
            "label_color": "",
            "canvas_bg": "",
            "ui_font_family": "Segoe UI",
            "ui_font_size": 9,
            "heading_font_size": 10,
            "canvas_font_family": "Segoe UI",
            "canvas_label_min_size": 5,
            "canvas_label_max_size": 8,
             "file_type_colors": {
                 "image": "#ff6600",
                 "video": "#cc0000",
                 "audio": "#00cc00",
                 "document": "#0066ff",
                 "archive": "#cccc00",
                 "executable": "#cc00cc",
                 "code": "#00cccc",
                 "text": "#aaaaaa",
                 "other": ""
             },
             "log_bg": "",
             "log_fg": ""
        }
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
        self.dark_mode = self.settings.get("dark_mode", False)

    def apply_geometry(self):
        """Restore window position and size if remembered."""
        if self.settings.get("remember_window_pos", True):
            fullscreen = self.settings.get("fullscreen", False)
            if fullscreen:
                self.state("zoomed")
                return
            # Try saved geometry
            geom = self.settings.get("window_geometry")
            if geom:
                try:
                    self.geometry(geom)
                    return
                except tk.TclError:
                    pass  # Invalid geometry, use default
        
        # Fallback to default centered geometry
        self.geometry("1100x750")
        self.center_window()

    def center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def on_close(self):
        """Save window position before exiting."""
        if self.settings.get("remember_window_pos", True):
            fullscreen = self.state() == "zoomed"
            self.settings["fullscreen"] = fullscreen
            if not fullscreen:
                self.settings["window_geometry"] = self.geometry()
            else:
                # Clear geometry if maximized
                self.settings.pop("window_geometry", None)
            self.save_settings()
        self.destroy()

    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)

    def apply_theme(self):
        ui_font = (
            self.settings.get("ui_font_family", "Segoe UI"),
            self.get_setting_int("ui_font_size", 9, 6, 24)
        )
        heading_font = (
            self.settings.get("ui_font_family", "Segoe UI"),
            self.get_setting_int("heading_font_size", 10, 6, 28),
            "bold"
        )

        if self.dark_mode:
            # Dark theme
            self.configure(bg="#1e1e1e")
            base_bg = "#1e1e1e"
            default_canvas_bg = "#2d2d30"
            self.style = ttk.Style()
            self.style.configure(".", font=ui_font)
            self.style.configure("TFrame", background="#1e1e1e")
            self.style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
            self.style.configure("TNotebook.Tab", background="#2d2d30", foreground="#cccccc", font=ui_font)
            self.style.map("TNotebook.Tab", background=[("selected", "#3c3c3c")])
            self.style.configure("TButton", background="#3c3c3c", foreground="#cccccc", font=ui_font)
            self.style.map("TButton", background=[("active", "#4a4a4a")])
            self.style.configure("TLabel", background="#1e1e1e", foreground="#cccccc", font=ui_font)
            self.style.configure("Heading.TLabel", background="#1e1e1e", foreground="#cccccc", font=heading_font)
        else:
            # Light theme
            self.configure(bg="#f0f0f0")
            base_bg = "#f0f0f0"
            default_canvas_bg = "white"
            self.style = ttk.Style()
            self.style.configure(".", font=ui_font)
            self.style.configure("TFrame", background="#f0f0f0")
            self.style.configure("TNotebook", background="#f0f0f0", borderwidth=0)
            self.style.configure("TNotebook.Tab", background="#e0e0e0", foreground="black", font=ui_font)
            self.style.map("TNotebook.Tab", background=[("selected", "#f8f8f8")])
            self.style.configure("TButton", background="#e0e0e0", foreground="black", font=ui_font)
            self.style.map("TButton", background=[("active", "#d0d0d0")])
            self.style.configure("TLabel", background="#f0f0f0", foreground="black", font=ui_font)
            self.style.configure("Heading.TLabel", background="#f0f0f0", foreground="black", font=heading_font)

        # Apply canvas background (custom or default)
        canvas_bg = self.settings.get("canvas_bg", default_canvas_bg)
        if not canvas_bg:
            canvas_bg = default_canvas_bg
        self.canvas.configure(bg=canvas_bg)
        if hasattr(self, "treemap_tab"):
            self.treemap_tab.configure(style="Treemap.TFrame")
            self.style.configure("Treemap.TFrame", background=canvas_bg)
        if hasattr(self, "main_notebook"):
            self.style.configure("Main.TNotebook", background=base_bg, borderwidth=0)
            self.main_notebook.configure(style="Main.TNotebook")

        if hasattr(self, "log_text"):
            log_bg = self.settings.get("log_bg", "")
            if not log_bg:
                log_bg = "#1f1f1f" if self.dark_mode else "white"
            log_fg = self.settings.get("log_fg", "")
            if not log_fg:
                log_fg = "#dddddd" if self.dark_mode else "black"
            log_insert = log_fg  # Use text color for cursor
            self.log_text.configure(
                bg=log_bg,
                fg=log_fg,
                insertbackground=log_insert,
                font=ui_font
            )
            if hasattr(self, "log_tab"):
                self.log_tab.configure(style="Log.TFrame")
                self.style.configure("Log.TFrame", background=log_bg)
            if hasattr(self, "log_toolbar"):
                self.log_toolbar.configure(style="Log.TFrame")

    def get_setting_int(self, key, default, minimum, maximum):
        try:
            value = int(self.settings.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

    def get_int_var(self, variable, default, minimum, maximum):
        try:
            value = int(variable.get())
        except (tk.TclError, TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

    def toggle_dark_mode(self, enabled):
        self.dark_mode = enabled
        self.settings["dark_mode"] = enabled
        self.save_settings()
        self.apply_theme()
        if self.current_node:
            self.draw()

    def show_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        width, height = 480, 520
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        settings_win.geometry(f"{width}x{height}+{x}+{y}")
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.resizable(False, False)

        main_frame = ttk.Frame(settings_win, padding=12)
        main_frame.pack(fill="both", expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)

        appearance_tab = ttk.Frame(notebook, padding=12)
        fonts_tab = ttk.Frame(notebook, padding=12)
        behavior_tab = ttk.Frame(notebook, padding=12)
        scan_tab = ttk.Frame(notebook, padding=12)

        notebook.add(appearance_tab, text="Appearance")
        notebook.add(fonts_tab, text="Fonts")
        notebook.add(behavior_tab, text="Behavior")
        notebook.add(scan_tab, text="Scan")

        ttk.Label(appearance_tab, text="Theme", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        theme_frame = ttk.Frame(appearance_tab)
        theme_frame.pack(fill="x", pady=(0, 16))

        ttk.Label(theme_frame, text="Mode:").pack(side="left")

        self.theme_var = tk.StringVar(value="light" if not self.dark_mode else "dark")

        ttk.Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light",
                        command=lambda: self.on_theme_change("light")).pack(side="left", padx=(10, 20))
        ttk.Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark",
                        command=lambda: self.on_theme_change("dark")).pack(side="left", padx=(0, 20))

        ttk.Label(appearance_tab, text="Colors", style="Heading.TLabel").pack(anchor="w", pady=(8, 10))
        ttk.Button(appearance_tab, text="General Colors...", command=self.show_color_settings).pack(anchor="w", pady=(0, 8))
        ttk.Button(appearance_tab, text="File Type Colors...", command=self.show_file_type_colors).pack(anchor="w", pady=(0, 8))
        ttk.Button(appearance_tab, text="Log Colors...", command=self.show_log_color_settings).pack(anchor="w", pady=(0, 16))

        ttk.Label(fonts_tab, text="Interface Font", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        font_family_values = sorted({
            "Segoe UI",
            "Arial",
            "Calibri",
            "Consolas",
            "Tahoma",
            "Verdana",
            self.settings.get("ui_font_family", "Segoe UI"),
            self.settings.get("canvas_font_family", "Segoe UI")
        })

        def add_labeled_spinbox(parent, label, variable, from_, to_, width=6):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=24).pack(side="left")
            ttk.Spinbox(row, from_=from_, to=to_, textvariable=variable, width=width).pack(side="left")

        ui_family_frame = ttk.Frame(fonts_tab)
        ui_family_frame.pack(fill="x", pady=3)
        ttk.Label(ui_family_frame, text="UI font family", width=24).pack(side="left")
        self.ui_font_family_var = tk.StringVar(value=self.settings.get("ui_font_family", "Segoe UI"))
        ttk.Combobox(
            ui_family_frame,
            textvariable=self.ui_font_family_var,
            values=font_family_values,
            width=20
        ).pack(side="left")

        self.ui_font_size_var = tk.IntVar(value=self.get_setting_int("ui_font_size", 9, 6, 24))
        add_labeled_spinbox(fonts_tab, "UI font size", self.ui_font_size_var, 6, 24)

        self.heading_font_size_var = tk.IntVar(value=self.get_setting_int("heading_font_size", 10, 6, 28))
        add_labeled_spinbox(fonts_tab, "Heading font size", self.heading_font_size_var, 6, 28)

        ttk.Separator(fonts_tab, orient="horizontal").pack(fill="x", pady=14)
        ttk.Label(fonts_tab, text="Treemap Labels", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        canvas_family_frame = ttk.Frame(fonts_tab)
        canvas_family_frame.pack(fill="x", pady=3)
        ttk.Label(canvas_family_frame, text="Label font family", width=24).pack(side="left")
        self.canvas_font_family_var = tk.StringVar(value=self.settings.get("canvas_font_family", "Segoe UI"))
        ttk.Combobox(
            canvas_family_frame,
            textvariable=self.canvas_font_family_var,
            values=font_family_values,
            width=20
        ).pack(side="left")

        self.canvas_label_min_size_var = tk.IntVar(value=self.get_setting_int("canvas_label_min_size", 5, 4, 18))
        add_labeled_spinbox(fonts_tab, "Minimum label size", self.canvas_label_min_size_var, 4, 18)

        self.canvas_label_max_size_var = tk.IntVar(value=self.get_setting_int("canvas_label_max_size", 8, 5, 32))
        add_labeled_spinbox(fonts_tab, "Maximum label size", self.canvas_label_max_size_var, 5, 32)

        ttk.Label(behavior_tab, text="Actions", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        self.density_var = tk.IntVar(value=self.settings.get("min_density", 1))
        ttk.Checkbutton(behavior_tab, text="Hide small files (density filter)", variable=self.density_var).pack(anchor="w", pady=2)

        self.disable_delete_var = tk.BooleanVar(value=self.settings.get("disable_delete", False))
        ttk.Checkbutton(behavior_tab, text="Disable delete command", variable=self.disable_delete_var).pack(anchor="w", pady=2)

        self.remember_pos_var = tk.BooleanVar(value=self.settings.get("remember_window_pos", True))
        ttk.Checkbutton(behavior_tab, text="Remember window position", variable=self.remember_pos_var).pack(anchor="w", pady=2)

        self.animated_zoom_var = tk.BooleanVar(value=self.settings.get("animated_zoom", False))
        ttk.Checkbutton(behavior_tab, text="Animated zoom in/out", variable=self.animated_zoom_var).pack(anchor="w", pady=2)

        self.auto_rescan_var = tk.BooleanVar(value=self.settings.get("auto_rescan_on_delete", True))
        ttk.Checkbutton(behavior_tab, text="Auto rescan after delete", variable=self.auto_rescan_var).pack(anchor="w", pady=2)

        ttk.Label(scan_tab, text="Scan Progress", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        self.show_scan_progress_var = tk.BooleanVar(value=self.settings.get("show_scan_progress", True))
        ttk.Checkbutton(scan_tab, text="Show scan progress details", variable=self.show_scan_progress_var).pack(anchor="w", pady=2)

        ttk.Label(scan_tab, text="Maximum scan threads:").pack(anchor="w", pady=(12, 2))
        self.max_threads_var = tk.IntVar(value=self.get_setting_int("max_scan_threads", 6, 1, 32))
        ttk.Spinbox(scan_tab, from_=1, to=32, textvariable=self.max_threads_var, width=5).pack(anchor="w", pady=(0, 10))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(12, 0))

        def save_and_close():
            self.settings["min_density"] = self.density_var.get()
            self.settings["disable_delete"] = self.disable_delete_var.get()
            self.settings["remember_window_pos"] = self.remember_pos_var.get()
            self.settings["show_scan_progress"] = self.show_scan_progress_var.get()
            self.settings["max_scan_threads"] = self.get_int_var(self.max_threads_var, 6, 1, 32)
            self.settings["animated_zoom"] = self.animated_zoom_var.get()
            self.settings["auto_rescan_on_delete"] = self.auto_rescan_var.get()
            self.settings["dark_mode"] = (self.theme_var.get() == "dark")
            self.settings["ui_font_family"] = self.ui_font_family_var.get().strip() or "Segoe UI"
            self.settings["ui_font_size"] = self.get_int_var(self.ui_font_size_var, 9, 6, 24)
            self.settings["heading_font_size"] = self.get_int_var(self.heading_font_size_var, 10, 6, 28)
            self.settings["canvas_font_family"] = self.canvas_font_family_var.get().strip() or "Segoe UI"
            min_label_size = self.get_int_var(self.canvas_label_min_size_var, 5, 4, 18)
            max_label_size = self.get_int_var(self.canvas_label_max_size_var, 8, 5, 32)
            self.settings["canvas_label_min_size"] = min_label_size
            self.settings["canvas_label_max_size"] = max(min_label_size, max_label_size)
            self.dark_mode = self.settings["dark_mode"]
            self.save_settings()
            self.apply_theme()
            if self.current_node:
                self.draw()
            settings_win.destroy()

        def cancel_and_close():
            self.load_settings()
            settings_win.destroy()

        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_and_close).pack(side="right")

        settings_win.protocol("WM_DELETE_WINDOW", cancel_and_close)

    def on_theme_change(self, theme):
        self.toggle_dark_mode(theme == "dark")
