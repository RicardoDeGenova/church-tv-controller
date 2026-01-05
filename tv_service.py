from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Literal

from models import TVConfig, TVStatus, TVState, ActionResult
import adb_controller
import webos_controller


def check_single_tv(config: TVConfig) -> TVStatus:
    if config.protocol == "webos":
        return webos_controller.check_single_tv(config)
    return adb_controller.check_single_tv(config)


def turn_on_single_tv(config: TVConfig) -> TVStatus:
    if config.protocol == "webos":
        return webos_controller.turn_on_single_tv(config)
    return adb_controller.turn_on_single_tv(config)


def turn_off_single_tv(config: TVConfig) -> TVStatus:
    if config.protocol == "webos":
        return webos_controller.turn_off_single_tv(config)
    return adb_controller.turn_off_single_tv(config)


TVActionFunction = Callable[[TVConfig], TVStatus]


def get_action_function(action: Literal["on", "off", "check"]) -> TVActionFunction:
    if action == "on":
        return turn_on_single_tv
    elif action == "off":
        return turn_off_single_tv
    return check_single_tv


def execute_on_multiple_tvs(
    tv_list: list[TVConfig],
    action: Literal["on", "off", "check"],
    on_tv_complete: Callable[[TVStatus], None] | None = None,
    max_workers: int = 6
) -> list[TVStatus]:
    results: list[TVStatus] = []
    action_function = get_action_function(action)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_tv = {
            executor.submit(action_function, config): config
            for config in tv_list
        }

        for future in as_completed(future_to_tv):
            config = future_to_tv[future]

            try:
                status = future.result()
            except Exception as e:
                status = TVStatus(
                    name=config.name,
                    ip=config.ip,
                    state=TVState.UNREACHABLE,
                    action_result=ActionResult.FAILED,
                    message=f"Error: {str(e)}"
                )

            results.append(status)

            if on_tv_complete:
                on_tv_complete(status)

    return results
