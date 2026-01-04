import subprocess
import platform
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from config import ADB_PORT


class TVState(Enum):
    UNKNOWN = "unknown"
    AWAKE = "awake"
    ASLEEP = "asleep"
    UNREACHABLE = "unreachable"


class ActionResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TVStatus:
    name: str
    ip: str
    state: TVState
    action_result: ActionResult | None = None
    message: str = ""


def get_adb_path() -> str:
    app_directory = Path(__file__).parent
    system_name = platform.system().lower()
    
    if system_name == "darwin":
        adb_binary = app_directory / "adb" / "mac" / "adb"
    elif system_name == "windows":
        adb_binary = app_directory / "adb" / "windows" / "adb.exe"
    else:
        adb_binary = app_directory / "adb" / "linux" / "adb"
    
    if adb_binary.exists():
        return str(adb_binary)
    
    return "adb"


def run_adb_command(args: list[str], timeout_seconds: int = 10) -> tuple[bool, str]:
    adb_path = get_adb_path()
    full_command = [adb_path] + args
    
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Connection timed out"
    except FileNotFoundError:
        return False, "ADB not found"
    except Exception as e:
        return False, str(e)


def connect_to_tv(ip: str) -> tuple[bool, str]:
    address = f"{ip}:{ADB_PORT}"
    success, output = run_adb_command(["connect", address], timeout_seconds=5)
    
    is_connected = success and ("connected" in output.lower() or "already connected" in output.lower())
    return is_connected, output


def disconnect_from_tv(ip: str) -> None:
    address = f"{ip}:{ADB_PORT}"
    run_adb_command(["disconnect", address], timeout_seconds=3)


def get_tv_power_state(ip: str) -> TVState:
    address = f"{ip}:{ADB_PORT}"
    success, output = run_adb_command(
        ["-s", address, "shell", "dumpsys power | grep 'mWakefulness='"],
        timeout_seconds=5
    )
    
    if not success:
        return TVState.UNREACHABLE
    
    output_lower = output.lower()
    if "awake" in output_lower:
        return TVState.AWAKE
    elif "asleep" in output_lower or "dozing" in output_lower:
        return TVState.ASLEEP
    
    return TVState.UNKNOWN


def send_power_toggle(ip: str) -> tuple[bool, str]:
    address = f"{ip}:{ADB_PORT}"
    success, output = run_adb_command(
        ["-s", address, "shell", "input keyevent 26"],
        timeout_seconds=5
    )
    return success, output


def check_single_tv(name: str, ip: str) -> TVStatus:
    connected, connection_message = connect_to_tv(ip)
    
    if not connected:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.UNREACHABLE,
            message=f"Could not connect: {connection_message}"
        )
    
    state = get_tv_power_state(ip)
    
    return TVStatus(
        name=name,
        ip=ip,
        state=state,
        message="Connected"
    )


def turn_on_single_tv(name: str, ip: str) -> TVStatus:
    connected, connection_message = connect_to_tv(ip)
    
    if not connected:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message=f"Could not connect: {connection_message}"
        )
    
    current_state = get_tv_power_state(ip)
    
    if current_state == TVState.AWAKE:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.AWAKE,
            action_result=ActionResult.SKIPPED,
            message="Already on"
        )
    
    if current_state == TVState.UNREACHABLE:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message="Could not read power state"
        )
    
    toggle_success, toggle_message = send_power_toggle(ip)
    
    if not toggle_success:
        return TVStatus(
            name=name,
            ip=ip,
            state=current_state,
            action_result=ActionResult.FAILED,
            message=f"Toggle failed: {toggle_message}"
        )
    
    return TVStatus(
        name=name,
        ip=ip,
        state=TVState.AWAKE,
        action_result=ActionResult.SUCCESS,
        message="Turned on"
    )


def turn_off_single_tv(name: str, ip: str) -> TVStatus:
    connected, connection_message = connect_to_tv(ip)
    
    if not connected:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message=f"Could not connect: {connection_message}"
        )
    
    current_state = get_tv_power_state(ip)
    
    if current_state == TVState.ASLEEP:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.ASLEEP,
            action_result=ActionResult.SKIPPED,
            message="Already off"
        )
    
    if current_state == TVState.UNREACHABLE:
        return TVStatus(
            name=name,
            ip=ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message="Could not read power state"
        )
    
    toggle_success, toggle_message = send_power_toggle(ip)
    
    if not toggle_success:
        return TVStatus(
            name=name,
            ip=ip,
            state=current_state,
            action_result=ActionResult.FAILED,
            message=f"Toggle failed: {toggle_message}"
        )
    
    return TVStatus(
        name=name,
        ip=ip,
        state=TVState.ASLEEP,
        action_result=ActionResult.SUCCESS,
        message="Turned off"
    )


TVActionFunction = Callable[[str, str], TVStatus]


def execute_on_multiple_tvs(
    tv_list: list[tuple[str, str]],
    action_function: TVActionFunction,
    on_tv_complete: Callable[[TVStatus], None] | None = None,
    max_workers: int = 6
) -> list[TVStatus]:
    results: list[TVStatus] = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_tv = {
            executor.submit(action_function, name, ip): (name, ip)
            for name, ip in tv_list
        }
        
        for future in as_completed(future_to_tv):
            name, ip = future_to_tv[future]
            
            try:
                status = future.result()
            except Exception as e:
                status = TVStatus(
                    name=name,
                    ip=ip,
                    state=TVState.UNREACHABLE,
                    action_result=ActionResult.FAILED,
                    message=f"Error: {str(e)}"
                )
            
            results.append(status)
            
            if on_tv_complete:
                on_tv_complete(status)
    
    return results
