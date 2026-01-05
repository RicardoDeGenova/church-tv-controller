import subprocess
import platform
from pathlib import Path

from models import TVConfig, TVStatus, TVState, ActionResult
from config_loader import load_config


def get_adb_port() -> int:
    try:
        config = load_config()
        return config.adb_port
    except Exception:
        return 5555


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
    port = get_adb_port()
    address = f"{ip}:{port}"
    success, output = run_adb_command(["connect", address], timeout_seconds=5)

    is_connected = success and ("connected" in output.lower() or "already connected" in output.lower())
    return is_connected, output


def disconnect_from_tv(ip: str) -> None:
    port = get_adb_port()
    address = f"{ip}:{port}"
    run_adb_command(["disconnect", address], timeout_seconds=3)


def get_tv_power_state(ip: str) -> TVState:
    port = get_adb_port()
    address = f"{ip}:{port}"
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
    port = get_adb_port()
    address = f"{ip}:{port}"
    success, output = run_adb_command(
        ["-s", address, "shell", "input keyevent 26"],
        timeout_seconds=5
    )
    return success, output


def check_single_tv(config: TVConfig) -> TVStatus:
    connected, connection_message = connect_to_tv(config.ip)

    if not connected:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            message=f"Could not connect: {connection_message}"
        )

    state = get_tv_power_state(config.ip)

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=state,
        message="Connected"
    )


def turn_on_single_tv(config: TVConfig) -> TVStatus:
    connected, connection_message = connect_to_tv(config.ip)

    if not connected:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message=f"Could not connect: {connection_message}"
        )

    current_state = get_tv_power_state(config.ip)

    if current_state == TVState.AWAKE:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.AWAKE,
            action_result=ActionResult.SKIPPED,
            message="Already on"
        )

    if current_state == TVState.UNREACHABLE:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message="Could not read power state"
        )

    toggle_success, toggle_message = send_power_toggle(config.ip)

    if not toggle_success:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=current_state,
            action_result=ActionResult.FAILED,
            message=f"Toggle failed: {toggle_message}"
        )

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=TVState.AWAKE,
        action_result=ActionResult.SUCCESS,
        message="Turned on"
    )


def turn_off_single_tv(config: TVConfig) -> TVStatus:
    connected, connection_message = connect_to_tv(config.ip)

    if not connected:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message=f"Could not connect: {connection_message}"
        )

    current_state = get_tv_power_state(config.ip)

    if current_state == TVState.ASLEEP:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.ASLEEP,
            action_result=ActionResult.SKIPPED,
            message="Already off"
        )

    if current_state == TVState.UNREACHABLE:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            action_result=ActionResult.FAILED,
            message="Could not read power state"
        )

    toggle_success, toggle_message = send_power_toggle(config.ip)

    if not toggle_success:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=current_state,
            action_result=ActionResult.FAILED,
            message=f"Toggle failed: {toggle_message}"
        )

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=TVState.ASLEEP,
        action_result=ActionResult.SUCCESS,
        message="Turned off"
    )
