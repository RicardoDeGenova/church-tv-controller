import json
import socket
from pathlib import Path

from pywebostv.connection import WebOSClient
from pywebostv.controls import SystemControl

from models import TVConfig, TVStatus, TVState, ActionResult


def get_tokens_path() -> Path:
    return Path(__file__).parent / "webos_tokens.json"


def load_tokens() -> dict[str, dict]:
    tokens_path = get_tokens_path()
    if not tokens_path.exists():
        return {}
    try:
        with open(tokens_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_tokens(tokens: dict[str, dict]) -> None:
    tokens_path = get_tokens_path()
    with open(tokens_path, "w") as f:
        json.dump(tokens, f, indent=2)


def save_token_for_ip(ip: str, store: dict) -> None:
    tokens = load_tokens()
    tokens[ip] = store
    save_tokens(tokens)


def get_token_for_ip(ip: str) -> dict:
    tokens = load_tokens()
    return tokens.get(ip, {})


def send_wol_packet(mac_address: str) -> bool:
    try:
        mac_bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
        magic_packet = b'\xff' * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('255.255.255.255', 9))
        return True
    except Exception:
        return False


def connect_to_webos_tv(ip: str) -> tuple[WebOSClient | None, str]:
    store = get_token_for_ip(ip)

    try:
        client = WebOSClient(ip)
        client.connect()

        for status in client.register(store):
            if status == WebOSClient.PROMPTED:
                save_token_for_ip(ip, store)
                return None, "Accept prompt on TV"
            elif status == WebOSClient.REGISTERED:
                save_token_for_ip(ip, store)
                return client, "Connected"

        return None, "Registration failed"

    except Exception as e:
        return None, str(e)


def check_single_tv(config: TVConfig) -> TVStatus:
    client, message = connect_to_webos_tv(config.ip)

    if client is None:
        if "Accept prompt" in message:
            return TVStatus(
                name=config.name,
                ip=config.ip,
                state=TVState.UNKNOWN,
                message=message
            )
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNREACHABLE,
            message=f"Could not connect: {message}"
        )

    try:
        client.disconnect()
    except Exception:
        pass

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=TVState.AWAKE,
        message="Connected"
    )


def turn_on_single_tv(config: TVConfig) -> TVStatus:
    if not config.mac:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNKNOWN,
            action_result=ActionResult.FAILED,
            message="No MAC address configured for Wake-on-LAN"
        )

    client, message = connect_to_webos_tv(config.ip)

    if client is not None:
        try:
            client.disconnect()
        except Exception:
            pass
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.AWAKE,
            action_result=ActionResult.SKIPPED,
            message="Already on"
        )

    if "Accept prompt" in message:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.UNKNOWN,
            action_result=ActionResult.FAILED,
            message=message
        )

    wol_success = send_wol_packet(config.mac)

    if not wol_success:
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.ASLEEP,
            action_result=ActionResult.FAILED,
            message="Wake-on-LAN packet failed to send"
        )

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=TVState.AWAKE,
        action_result=ActionResult.SUCCESS,
        message="Wake-on-LAN packet sent"
    )


def turn_off_single_tv(config: TVConfig) -> TVStatus:
    client, message = connect_to_webos_tv(config.ip)

    if client is None:
        if "Accept prompt" in message:
            return TVStatus(
                name=config.name,
                ip=config.ip,
                state=TVState.UNKNOWN,
                action_result=ActionResult.FAILED,
                message=message
            )
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.ASLEEP,
            action_result=ActionResult.SKIPPED,
            message="Already off or unreachable"
        )

    try:
        system = SystemControl(client)
        system.power_off()
    except Exception as e:
        try:
            client.disconnect()
        except Exception:
            pass
        return TVStatus(
            name=config.name,
            ip=config.ip,
            state=TVState.AWAKE,
            action_result=ActionResult.FAILED,
            message=f"Power off failed: {str(e)}"
        )

    try:
        client.disconnect()
    except Exception:
        pass

    return TVStatus(
        name=config.name,
        ip=config.ip,
        state=TVState.ASLEEP,
        action_result=ActionResult.SUCCESS,
        message="Turned off"
    )
