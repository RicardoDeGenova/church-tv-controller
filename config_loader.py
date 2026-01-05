import json
from pathlib import Path
from dataclasses import dataclass

from models import TVConfig


@dataclass
class AppConfig:
    adb_port: int
    inside_tvs: list[TVConfig]
    outside_tvs: list[TVConfig]


class ConfigError(Exception):
    pass


DEFAULT_CONFIG = {
    "adb_port": 5555,
    "inside_tvs": [
        {"name": "Example TV 1", "ip": "192.168.1.10"},
        {"name": "Example WebOS TV", "ip": "192.168.1.11", "protocol": "webos", "mac": "AA:BB:CC:DD:EE:FF"}
    ],
    "outside_tvs": []
}


def get_config_path() -> Path:
    return Path(__file__).parent / "config.json"


def create_default_config() -> None:
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)


def parse_tv_config(tv_data: dict, index: int, group_name: str) -> TVConfig:
    if "name" not in tv_data:
        raise ConfigError(f"Missing 'name' for TV at index {index} in {group_name}")

    if "ip" not in tv_data:
        raise ConfigError(f"Missing 'ip' for TV '{tv_data.get('name', 'unknown')}' in {group_name}")

    protocol = tv_data.get("protocol", "adb")
    if protocol not in ("adb", "webos"):
        raise ConfigError(
            f"Invalid protocol '{protocol}' for TV '{tv_data['name']}' in {group_name}. "
            f"Must be 'adb' or 'webos'"
        )

    mac = tv_data.get("mac")
    if protocol == "webos" and not mac:
        raise ConfigError(
            f"Missing 'mac' for WebOS TV '{tv_data['name']}' in {group_name}. "
            f"MAC address is required for Wake-on-LAN power on"
        )

    return TVConfig(
        name=tv_data["name"],
        ip=tv_data["ip"],
        protocol=protocol,
        mac=mac
    )


def parse_tv_list(tv_list: list, group_name: str) -> list[TVConfig]:
    result = []
    for index, tv_data in enumerate(tv_list):
        if not isinstance(tv_data, dict):
            raise ConfigError(f"Invalid TV entry at index {index} in {group_name}: expected object")
        result.append(parse_tv_config(tv_data, index, group_name))
    return result


def load_config() -> AppConfig:
    config_path = get_config_path()

    if not config_path.exists():
        create_default_config()
        raise ConfigError(
            f"No config.json found. A template has been created at:\n"
            f"{config_path}\n\n"
            f"Please edit it with your TV information and restart the application."
        )

    try:
        with open(config_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config.json: {e}")

    if not isinstance(data, dict):
        raise ConfigError("config.json must be a JSON object")

    adb_port = data.get("adb_port", 5555)
    if not isinstance(adb_port, int):
        raise ConfigError("'adb_port' must be an integer")

    inside_tvs_data = data.get("inside_tvs", [])
    if not isinstance(inside_tvs_data, list):
        raise ConfigError("'inside_tvs' must be an array")

    outside_tvs_data = data.get("outside_tvs", [])
    if not isinstance(outside_tvs_data, list):
        raise ConfigError("'outside_tvs' must be an array")

    inside_tvs = parse_tv_list(inside_tvs_data, "inside_tvs")
    outside_tvs = parse_tv_list(outside_tvs_data, "outside_tvs")

    return AppConfig(
        adb_port=adb_port,
        inside_tvs=inside_tvs,
        outside_tvs=outside_tvs
    )
