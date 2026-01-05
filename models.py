from dataclasses import dataclass
from enum import Enum


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
class TVConfig:
    name: str
    ip: str
    protocol: str = "adb"
    mac: str | None = None


@dataclass
class TVStatus:
    name: str
    ip: str
    state: TVState
    action_result: ActionResult | None = None
    message: str = ""
