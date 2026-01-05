import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable

from models import TVConfig, TVStatus, TVState, ActionResult
from config_loader import load_config, ConfigError, AppConfig
from tv_service import execute_on_multiple_tvs


class Colors:
    GRAY = "#888888"
    YELLOW = "#FFD700"
    GREEN = "#32CD32"
    RED = "#DC143C"
    BACKGROUND = "#2B2B2B"
    FOREGROUND = "#FFFFFF"
    BUTTON_BG = "#404040"
    FRAME_BG = "#363636"


STATUS_RESET_DELAY_MS = 60000


class TVIndicator:
    def __init__(self, parent: tk.Frame, config: TVConfig, row: int):
        self.config = config
        self.reset_job_id: str | None = None

        self.indicator_label = tk.Label(
            parent,
            text="●",
            font=("Arial", 14),
            fg=Colors.GRAY,
            bg=Colors.FRAME_BG
        )
        self.indicator_label.grid(row=row, column=0, padx=(10, 5), pady=2, sticky="w")

        self.name_label = tk.Label(
            parent,
            text=config.name,
            font=("Arial", 11),
            fg=Colors.FOREGROUND,
            bg=Colors.FRAME_BG,
            width=12,
            anchor="w"
        )
        self.name_label.grid(row=row, column=1, padx=(0, 10), pady=2, sticky="w")

        self.ip_label = tk.Label(
            parent,
            text=config.ip,
            font=("Arial", 10),
            fg="#AAAAAA",
            bg=Colors.FRAME_BG,
            anchor="w"
        )
        self.ip_label.grid(row=row, column=2, padx=(0, 10), pady=2, sticky="w")

    def set_connecting(self) -> None:
        self.indicator_label.config(fg=Colors.YELLOW)

    def set_success(self) -> None:
        self.indicator_label.config(fg=Colors.GREEN)

    def set_failed(self) -> None:
        self.indicator_label.config(fg=Colors.RED)

    def set_unknown(self) -> None:
        self.indicator_label.config(fg=Colors.GRAY)

    def update_from_status(self, status: TVStatus) -> None:
        if status.state == TVState.UNREACHABLE:
            self.set_failed()
        elif status.action_result == ActionResult.FAILED:
            self.set_failed()
        elif status.state in (TVState.AWAKE, TVState.ASLEEP):
            self.set_success()
        elif "Accept prompt" in status.message:
            self.set_connecting()
        else:
            self.set_unknown()


class ChurchTVController:
    def __init__(self, config: AppConfig):
        self.config = config
        self.root = tk.Tk()
        self.root.title("Waves TV Controller")
        self.root.configure(bg=Colors.BACKGROUND)
        self.root.resizable(False, False)

        self.indicators: dict[str, TVIndicator] = {}
        self.is_operation_running = False
        self.reset_jobs: dict[str, str] = {}

        self.build_ui()
        self.center_window()

    def center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"+{x}+{y}")

    def build_ui(self) -> None:
        title_label = tk.Label(
            self.root,
            text="Waves TV Controller",
            font=("Arial", 18, "bold"),
            fg=Colors.FOREGROUND,
            bg=Colors.BACKGROUND,
            pady=15
        )
        title_label.pack(fill="x")

        tv_container = tk.Frame(self.root, bg=Colors.BACKGROUND)
        tv_container.pack(fill="both", expand=True, padx=20, pady=10)

        inside_frame = self.create_tv_group_frame(
            tv_container,
            "INSIDE TVs",
            self.config.inside_tvs,
            "inside"
        )
        inside_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        outside_frame = self.create_tv_group_frame(
            tv_container,
            "OUTSIDE TVs",
            self.config.outside_tvs,
            "outside"
        )
        outside_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        inside_buttons_frame = tk.Frame(self.root, bg=Colors.BACKGROUND)
        inside_buttons_frame.pack(fill="x", padx=20, pady=(0, 5))

        inside_buttons_inner = tk.Frame(inside_buttons_frame, bg=Colors.BACKGROUND)
        inside_buttons_inner.pack(side="left", expand=True)

        self.inside_on_btn = self.create_button(
            inside_buttons_inner,
            "Inside ON",
            lambda: self.turn_on_group(self.config.inside_tvs, "inside")
        )
        self.inside_on_btn.pack(side="left", padx=5)

        self.inside_off_btn = self.create_button(
            inside_buttons_inner,
            "Inside OFF",
            lambda: self.turn_off_group(self.config.inside_tvs, "inside")
        )
        self.inside_off_btn.pack(side="left", padx=5)

        outside_buttons_inner = tk.Frame(inside_buttons_frame, bg=Colors.BACKGROUND)
        outside_buttons_inner.pack(side="right", expand=True)

        self.outside_on_btn = self.create_button(
            outside_buttons_inner,
            "Outside ON",
            lambda: self.turn_on_group(self.config.outside_tvs, "outside")
        )
        self.outside_on_btn.pack(side="left", padx=5)

        self.outside_off_btn = self.create_button(
            outside_buttons_inner,
            "Outside OFF",
            lambda: self.turn_off_group(self.config.outside_tvs, "outside")
        )
        self.outside_off_btn.pack(side="left", padx=5)

        separator = ttk.Separator(self.root, orient="horizontal")
        separator.pack(fill="x", padx=20, pady=15)

        all_buttons_frame = tk.Frame(self.root, bg=Colors.BACKGROUND)
        all_buttons_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.all_on_btn = self.create_button(
            all_buttons_frame,
            "ALL TVs ON",
            self.turn_all_on,
            width=15
        )
        self.all_on_btn.pack(side="left", expand=True, padx=5)

        self.all_off_btn = self.create_button(
            all_buttons_frame,
            "ALL TVs OFF",
            self.turn_all_off,
            width=15
        )
        self.all_off_btn.pack(side="left", expand=True, padx=5)

        self.check_status_btn = self.create_button(
            all_buttons_frame,
            "CHECK STATUS",
            self.check_all_status,
            width=15
        )
        self.check_status_btn.pack(side="left", expand=True, padx=5)

        status_separator = ttk.Separator(self.root, orient="horizontal")
        status_separator.pack(fill="x", padx=20, pady=(10, 0))

        self.status_label = tk.Label(
            self.root,
            text="Status: Ready",
            font=("Arial", 11),
            fg=Colors.FOREGROUND,
            bg=Colors.BACKGROUND,
            pady=10
        )
        self.status_label.pack(fill="x", padx=20)

    def create_tv_group_frame(
        self,
        parent: tk.Frame,
        title: str,
        tv_list: list[TVConfig],
        group_prefix: str
    ) -> tk.Frame:
        outer_frame = tk.Frame(parent, bg=Colors.BACKGROUND)

        title_label = tk.Label(
            outer_frame,
            text=title,
            font=("Arial", 12, "bold"),
            fg=Colors.FOREGROUND,
            bg=Colors.BACKGROUND,
            pady=5
        )
        title_label.pack(anchor="w")

        inner_frame = tk.Frame(outer_frame, bg=Colors.FRAME_BG, padx=10, pady=10)
        inner_frame.pack(fill="both", expand=True)

        for row, config in enumerate(tv_list):
            indicator_key = f"{group_prefix}_{config.name}"
            indicator = TVIndicator(inner_frame, config, row)
            self.indicators[indicator_key] = indicator

        return outer_frame

    def create_button(
        self,
        parent: tk.Frame,
        text: str,
        command: Callable,
        width: int = 12
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            font=("Arial", 10),
            bg=Colors.BUTTON_BG,
            fg=Colors.FOREGROUND,
            activebackground="#505050",
            activeforeground=Colors.FOREGROUND,
            relief="flat",
            width=width,
            pady=8,
            command=command
        )
        return button

    def get_all_buttons(self) -> list[tk.Button]:
        return [
            self.inside_on_btn,
            self.inside_off_btn,
            self.outside_on_btn,
            self.outside_off_btn,
            self.all_on_btn,
            self.all_off_btn,
            self.check_status_btn,
        ]

    def disable_all_buttons(self) -> None:
        for button in self.get_all_buttons():
            button.config(state="disabled")

    def enable_all_buttons(self) -> None:
        for button in self.get_all_buttons():
            button.config(state="normal")

    def set_status(self, message: str) -> None:
        self.status_label.config(text=f"Status: {message}")

    def get_indicator_key(self, name: str, ip: str) -> str | None:
        for key, indicator in self.indicators.items():
            if indicator.config.name == name and indicator.config.ip == ip:
                return key
        return None

    def set_indicators_connecting(self, tv_list: list[TVConfig]) -> None:
        for config in tv_list:
            key = self.get_indicator_key(config.name, config.ip)
            if key and key in self.indicators:
                self.indicators[key].set_connecting()

    def schedule_indicator_reset(self, key: str) -> None:
        if key in self.reset_jobs:
            self.root.after_cancel(self.reset_jobs[key])

        job_id = self.root.after(
            STATUS_RESET_DELAY_MS,
            lambda: self.reset_single_indicator(key)
        )
        self.reset_jobs[key] = job_id

    def reset_single_indicator(self, key: str) -> None:
        if key in self.indicators:
            self.indicators[key].set_unknown()
        if key in self.reset_jobs:
            del self.reset_jobs[key]

    def on_tv_complete(self, status: TVStatus) -> None:
        key = self.get_indicator_key(status.name, status.ip)
        if key and key in self.indicators:
            self.root.after(0, lambda: self.update_indicator_from_status(key, status))

    def update_indicator_from_status(self, key: str, status: TVStatus) -> None:
        if key in self.indicators:
            self.indicators[key].update_from_status(status)
            self.schedule_indicator_reset(key)

    def run_threaded_operation(
        self,
        tv_list: list[TVConfig],
        action: str,
        status_message: str,
        completion_message: str
    ) -> None:
        if self.is_operation_running:
            return

        self.is_operation_running = True
        self.disable_all_buttons()
        self.set_status(status_message)
        self.set_indicators_connecting(tv_list)

        def run_operation():
            execute_on_multiple_tvs(
                tv_list,
                action,
                on_tv_complete=self.on_tv_complete,
                max_workers=6
            )
            self.root.after(0, lambda: self.on_operation_complete(completion_message))

        thread = threading.Thread(target=run_operation, daemon=True)
        thread.start()

    def on_operation_complete(self, message: str) -> None:
        self.is_operation_running = False
        self.enable_all_buttons()
        self.set_status(message)

    def turn_on_group(self, tv_list: list[TVConfig], group_name: str) -> None:
        self.run_threaded_operation(
            tv_list,
            "on",
            f"Turning on {group_name} TVs...",
            f"{group_name.capitalize()} TVs operation complete"
        )

    def turn_off_group(self, tv_list: list[TVConfig], group_name: str) -> None:
        self.run_threaded_operation(
            tv_list,
            "off",
            f"Turning off {group_name} TVs...",
            f"{group_name.capitalize()} TVs operation complete"
        )

    def turn_all_on(self) -> None:
        all_tvs = self.config.inside_tvs + self.config.outside_tvs
        self.run_threaded_operation(
            all_tvs,
            "on",
            "Turning on all TVs...",
            "All TVs operation complete"
        )

    def turn_all_off(self) -> None:
        all_tvs = self.config.inside_tvs + self.config.outside_tvs
        self.run_threaded_operation(
            all_tvs,
            "off",
            "Turning off all TVs...",
            "All TVs operation complete"
        )

    def check_all_status(self) -> None:
        all_tvs = self.config.inside_tvs + self.config.outside_tvs
        self.run_threaded_operation(
            all_tvs,
            "check",
            "Checking all TV statuses...",
            "Status check complete"
        )

    def run(self) -> None:
        self.root.mainloop()


def main():
    try:
        config = load_config()
    except ConfigError as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Configuration Error", str(e))
        sys.exit(1)

    app = ChurchTVController(config)
    app.run()


if __name__ == "__main__":
    main()
