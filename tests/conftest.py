from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _make_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    return mod


def _stub_homeassistant() -> None:
    class Platform:
        SENSOR = "sensor"

    class ConfigEntryNotReady(Exception):
        pass

    class FlowResult(dict):
        pass

    class ConfigFlow:
        VERSION = 1

        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._domain = domain

        def __init__(self):
            self.hass = None

        def async_show_form(self, *, step_id, data_schema=None, errors=None, **kwargs):
            return FlowResult(type="form", step_id=step_id, data_schema=data_schema, errors=errors or {})

        def async_create_entry(self, *, title, data):
            return FlowResult(type="create_entry", title=title, data=data)

    class ConfigEntry:
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, *, name, update_interval, config_entry=None):
            self.hass = hass
            self.data = None
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

        async def async_refresh(self):
            self.data = await self._async_update_data()

    class UpdateFailed(Exception):
        pass

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class SensorEntity:
        @property
        def native_unit_of_measurement(self):
            return getattr(self, "_attr_native_unit_of_measurement", None)

    class SensorStateClass:
        MEASUREMENT = "measurement"
    class SensorDeviceClass:
        MONETARY = "monetary"

    class HomeAssistant:
        pass

    class DeviceEntryType:
        SERVICE = "service"

    class StaticPathConfig:
        def __init__(self, url_path, path, cache_headers=True):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    dt_mod = _make_module("homeassistant.util.dt", now=lambda: None)

    mods = {
        "homeassistant": _make_module("homeassistant"),
        "homeassistant.const": _make_module("homeassistant.const", Platform=Platform),
        "homeassistant.exceptions": _make_module("homeassistant.exceptions", ConfigEntryNotReady=ConfigEntryNotReady),
        "homeassistant.config_entries": _make_module(
            "homeassistant.config_entries",
            ConfigFlow=ConfigFlow,
            ConfigEntry=ConfigEntry,
            FlowResult=FlowResult,
        ),
        "homeassistant.data_entry_flow": _make_module("homeassistant.data_entry_flow", FlowResult=FlowResult),
        "homeassistant.core": _make_module("homeassistant.core", HomeAssistant=HomeAssistant),
        "homeassistant.helpers": _make_module("homeassistant.helpers"),
        "homeassistant.helpers.update_coordinator": _make_module(
            "homeassistant.helpers.update_coordinator",
            DataUpdateCoordinator=DataUpdateCoordinator,
            UpdateFailed=UpdateFailed,
            CoordinatorEntity=CoordinatorEntity,
        ),
        "homeassistant.helpers.entity_platform": _make_module("homeassistant.helpers.entity_platform", AddEntitiesCallback=MagicMock()),
        "homeassistant.helpers.aiohttp_client": _make_module("homeassistant.helpers.aiohttp_client", async_get_clientsession=MagicMock()),
        "homeassistant.helpers.device_registry": _make_module("homeassistant.helpers.device_registry", DeviceEntryType=DeviceEntryType),
        "homeassistant.components": _make_module("homeassistant.components"),
        "homeassistant.components.http": _make_module("homeassistant.components.http", StaticPathConfig=StaticPathConfig),
        "homeassistant.components.persistent_notification": _make_module(
            "homeassistant.components.persistent_notification",
            async_create=MagicMock(),
            async_dismiss=MagicMock(),
        ),
        "homeassistant.components.sensor": _make_module(
            "homeassistant.components.sensor",
            SensorEntity=SensorEntity,
            SensorStateClass=SensorStateClass,
            SensorDeviceClass=SensorDeviceClass,
        ),
        "homeassistant.util": _make_module("homeassistant.util"),
        "homeassistant.util.dt": dt_mod,
    }

    for name, mod in mods.items():
        sys.modules.setdefault(name, mod)


_stub_homeassistant()
