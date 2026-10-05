from .client import CloudClient, CloudConnectionError
from .runtime import CloudProxy, get_runtime, shutdown_all
from .release import announce_load

announce_load()

__all__ = [
    "CloudClient", "CloudConnectionError", "CloudProxy", "get_runtime",
    "shutdown_all", "CloudPanel", "add_preview_routes",
]


def __getattr__(name):
    if name == "CloudPanel":
        from .cloud import CloudPanel
        return CloudPanel
    if name == "add_preview_routes":
        from .cloud_preview import add_preview_routes
        return add_preview_routes
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def create_device(config):
    from .device import CloudDevice
    return CloudDevice(config)
