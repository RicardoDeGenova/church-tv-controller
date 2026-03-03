import re
import copy
import tkinter as tk
from tkinter import messagebox
from typing import Callable

from models import TVConfig
from config_loader import AppConfig, save_config


class Colors:
    GRAY = "#888888"
    BACKGROUND = "#2B2B2B"
    FOREGROUND = "#FFFFFF"
    BUTTON_BG = "#404040"
    FRAME_BG = "#363636"


def validate_ip(ip: str) -> str | None:
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return "IP address must have 4 octets (e.g. 192.168.1.10)"
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            return f"'{part}' is not a valid number in IP address"
        if value < 0 or value > 255:
            return f"Each octet must be 0-255, got {value}"
    return None


def validate_mac(mac: str) -> str | None:
    normalized = mac.strip().replace("-", ":")
    if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", normalized):
        return "MAC address must be in format XX:XX:XX:XX:XX:XX"
    return None


def validate_port(port_str: str) -> tuple[int | None, str | None]:
    try:
        value = int(port_str.strip())
    except ValueError:
        return None, "Port must be an integer"
    if value < 1 or value > 65535:
        return None, "Port must be between 1 and 65535"
    return value, None


class TVEditDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, tv: TVConfig | None = None):
        super().__init__(parent)
        self.result: TVConfig | None = None
        self.transient(parent)
        self.grab_set()

        self.title("Edit TV" if tv else "Add TV")
        self.configure(bg=Colors.BACKGROUND)
        self.resizable(False, False)

        entry_opts = {
            "font": ("Arial", 11),
            "bg": Colors.BUTTON_BG,
            "fg": Colors.FOREGROUND,
            "insertbackground": Colors.FOREGROUND,
            "relief": "flat",
        }
        label_opts = {
            "font": ("Arial", 11),
            "fg": Colors.FOREGROUND,
            "bg": Colors.BACKGROUND,
        }

        form = tk.Frame(self, bg=Colors.BACKGROUND, padx=20, pady=15)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Name:", **label_opts).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.name_var = tk.StringVar(value=tv.name if tv else "")
        self.name_entry = tk.Entry(form, textvariable=self.name_var, width=30, **entry_opts)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8), padx=(10, 0))

        tk.Label(form, text="IP Address:", **label_opts).grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.ip_var = tk.StringVar(value=tv.ip if tv else "")
        self.ip_entry = tk.Entry(form, textvariable=self.ip_var, width=30, **entry_opts)
        self.ip_entry.grid(row=1, column=1, sticky="ew", pady=(0, 8), padx=(10, 0))

        tk.Label(form, text="Protocol:", **label_opts).grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.protocol_var = tk.StringVar(value=tv.protocol if tv else "adb")
        protocol_frame = tk.Frame(form, bg=Colors.BACKGROUND)
        protocol_frame.grid(row=2, column=1, sticky="ew", pady=(0, 8), padx=(10, 0))
        self.protocol_menu = tk.OptionMenu(protocol_frame, self.protocol_var, "adb", "webos")
        self.protocol_menu.config(
            font=("Arial", 10),
            bg=Colors.BUTTON_BG,
            fg=Colors.FOREGROUND,
            activebackground="#505050",
            activeforeground=Colors.FOREGROUND,
            relief="flat",
            highlightthickness=0,
        )
        self.protocol_menu["menu"].config(
            bg=Colors.BUTTON_BG,
            fg=Colors.FOREGROUND,
            activebackground="#505050",
            activeforeground=Colors.FOREGROUND,
        )
        self.protocol_menu.pack(anchor="w")

        tk.Label(form, text="MAC Address:", **label_opts).grid(row=3, column=0, sticky="w", pady=(0, 8))
        self.mac_var = tk.StringVar(value=tv.mac if tv and tv.mac else "")
        self.mac_entry = tk.Entry(form, textvariable=self.mac_var, width=30, **entry_opts)
        self.mac_entry.grid(row=3, column=1, sticky="ew", pady=(0, 8), padx=(10, 0))

        self.error_label = tk.Label(
            form, text="", font=("Arial", 10), fg="#DC143C", bg=Colors.BACKGROUND, wraplength=300, anchor="w"
        )
        self.error_label.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        btn_frame = tk.Frame(self, bg=Colors.BACKGROUND, padx=20, pady=(0, 15))
        btn_frame.pack(fill="x")

        btn_opts = {
            "font": ("Arial", 10),
            "bg": Colors.BUTTON_BG,
            "fg": Colors.FOREGROUND,
            "activebackground": "#505050",
            "activeforeground": Colors.FOREGROUND,
            "relief": "flat",
            "width": 10,
            "pady": 6,
        }

        tk.Button(btn_frame, text="Cancel", command=self.destroy, **btn_opts).pack(side="right", padx=(5, 0))
        tk.Button(btn_frame, text="OK", command=self.on_ok, **btn_opts).pack(side="right")

        self.protocol_var.trace_add("write", self.on_protocol_change)
        self.on_protocol_change()

        self.name_entry.focus_set()
        self.wait_window()

    def on_protocol_change(self, *_) -> None:
        if self.protocol_var.get() == "webos":
            self.mac_entry.config(state="normal")
        else:
            self.mac_entry.config(state="disabled")

    def on_ok(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.error_label.config(text="Name is required")
            return

        ip = self.ip_var.get().strip()
        if not ip:
            self.error_label.config(text="IP address is required")
            return
        ip_error = validate_ip(ip)
        if ip_error:
            self.error_label.config(text=ip_error)
            return

        protocol = self.protocol_var.get()
        mac = None

        if protocol == "webos":
            mac_raw = self.mac_var.get().strip()
            if not mac_raw:
                self.error_label.config(text="MAC address is required for WebOS TVs")
                return
            mac_error = validate_mac(mac_raw)
            if mac_error:
                self.error_label.config(text=mac_error)
                return
            mac = mac_raw.replace("-", ":").upper()

        self.result = TVConfig(name=name, ip=ip, protocol=protocol, mac=mac)
        self.destroy()


class TVListEditor(tk.Frame):
    def __init__(self, parent: tk.Widget, label: str, tv_list: list[TVConfig]):
        super().__init__(parent, bg=Colors.BACKGROUND)
        self.tv_list: list[TVConfig] = copy.deepcopy(tv_list)

        header = tk.Label(
            self, text=label, font=("Arial", 12, "bold"), fg=Colors.FOREGROUND, bg=Colors.BACKGROUND
        )
        header.pack(anchor="w", pady=(0, 5))

        self.list_frame = tk.Frame(self, bg=Colors.FRAME_BG, padx=10, pady=10)
        self.list_frame.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        label_opts = {"font": ("Arial", 10), "bg": Colors.FRAME_BG, "anchor": "w"}
        btn_opts = {
            "font": ("Arial", 9),
            "bg": Colors.BUTTON_BG,
            "fg": Colors.FOREGROUND,
            "activebackground": "#505050",
            "activeforeground": Colors.FOREGROUND,
            "relief": "flat",
            "pady": 2,
            "padx": 6,
        }

        for i, tv in enumerate(self.tv_list):
            tk.Label(self.list_frame, text=tv.name, fg=Colors.FOREGROUND, width=14, **label_opts).grid(
                row=i, column=0, sticky="w", padx=(0, 5), pady=2
            )
            tk.Label(self.list_frame, text=tv.ip, fg="#AAAAAA", width=14, **label_opts).grid(
                row=i, column=1, sticky="w", padx=(0, 5), pady=2
            )
            tk.Label(self.list_frame, text=tv.protocol, fg="#AAAAAA", width=5, **label_opts).grid(
                row=i, column=2, sticky="w", padx=(0, 5), pady=2
            )
            idx = i
            tk.Button(
                self.list_frame, text="Edit", command=lambda j=idx: self.edit_tv(j), width=4, **btn_opts
            ).grid(row=i, column=3, padx=2, pady=2)
            tk.Button(
                self.list_frame, text="Del", command=lambda j=idx: self.delete_tv(j), width=4, **btn_opts
            ).grid(row=i, column=4, padx=2, pady=2)

        add_row = len(self.tv_list)
        tk.Button(
            self.list_frame, text="+ Add TV", command=self.add_tv, width=10, **btn_opts
        ).grid(row=add_row, column=0, columnspan=5, sticky="w", pady=(8, 0))

    def add_tv(self) -> None:
        dialog = TVEditDialog(self)
        if dialog.result:
            self.tv_list.append(dialog.result)
            self.refresh()

    def edit_tv(self, index: int) -> None:
        dialog = TVEditDialog(self, tv=self.tv_list[index])
        if dialog.result:
            self.tv_list[index] = dialog.result
            self.refresh()

    def delete_tv(self, index: int) -> None:
        tv = self.tv_list[index]
        if messagebox.askyesno("Delete TV", f"Delete '{tv.name}' ({tv.ip})?", parent=self):
            self.tv_list.pop(index)
            self.refresh()

    def get_tv_list(self) -> list[TVConfig]:
        return list(self.tv_list)


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: tk.Widget, config: AppConfig, on_save_callback: Callable[[AppConfig], None]):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.transient(parent)
        self.grab_set()

        self.title("Settings")
        self.configure(bg=Colors.BACKGROUND)
        self.resizable(False, False)

        entry_opts = {
            "font": ("Arial", 11),
            "bg": Colors.BUTTON_BG,
            "fg": Colors.FOREGROUND,
            "insertbackground": Colors.FOREGROUND,
            "relief": "flat",
        }
        label_opts = {
            "font": ("Arial", 11),
            "fg": Colors.FOREGROUND,
            "bg": Colors.BACKGROUND,
        }

        main_frame = tk.Frame(self, bg=Colors.BACKGROUND, padx=20, pady=15)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame, text="Settings", font=("Arial", 16, "bold"), fg=Colors.FOREGROUND, bg=Colors.BACKGROUND
        ).pack(anchor="w", pady=(0, 15))

        global_frame = tk.Frame(main_frame, bg=Colors.BACKGROUND)
        global_frame.pack(fill="x", pady=(0, 15))
        tk.Label(global_frame, text="ADB Port:", **label_opts).pack(side="left")
        self.port_var = tk.StringVar(value=str(config.adb_port))
        tk.Entry(global_frame, textvariable=self.port_var, width=8, **entry_opts).pack(side="left", padx=(10, 0))

        self.inside_editor = TVListEditor(main_frame, "Inside TVs", config.inside_tvs)
        self.inside_editor.pack(fill="both", expand=True, pady=(0, 10))

        self.outside_editor = TVListEditor(main_frame, "Outside TVs", config.outside_tvs)
        self.outside_editor.pack(fill="both", expand=True, pady=(0, 15))

        self.error_label = tk.Label(
            main_frame, text="", font=("Arial", 10), fg="#DC143C", bg=Colors.BACKGROUND, anchor="w"
        )
        self.error_label.pack(fill="x", pady=(0, 5))

        btn_frame = tk.Frame(main_frame, bg=Colors.BACKGROUND)
        btn_frame.pack(fill="x")

        btn_opts = {
            "font": ("Arial", 10),
            "bg": Colors.BUTTON_BG,
            "fg": Colors.FOREGROUND,
            "activebackground": "#505050",
            "activeforeground": Colors.FOREGROUND,
            "relief": "flat",
            "width": 10,
            "pady": 6,
        }

        tk.Button(btn_frame, text="Cancel", command=self.destroy, **btn_opts).pack(side="right", padx=(5, 0))
        tk.Button(btn_frame, text="Save", command=self.on_save, **btn_opts).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def on_save(self) -> None:
        port, port_error = validate_port(self.port_var.get())
        if port_error:
            self.error_label.config(text=f"ADB Port: {port_error}")
            return

        new_config = AppConfig(
            adb_port=port,
            inside_tvs=self.inside_editor.get_tv_list(),
            outside_tvs=self.outside_editor.get_tv_list(),
        )

        save_config(new_config)
        self.on_save_callback(new_config)
        self.destroy()
