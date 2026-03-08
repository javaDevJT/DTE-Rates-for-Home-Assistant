from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components import persistent_notification

from .const import DOMAIN
from .coordinator import DteRateCoordinator
from .rate_calculator import current_export_rate_cents, current_import_rate_cents, period_display_name

PLATFORMS: list[Platform] = [Platform.SENSOR]
SERVICE_REFRESH_RATE_CARD = "refresh_rate_card"
SERVICE_SHOW_RATE_SCHEDULE = "show_rate_schedule"
SERVICE_SHOW_CARD_EXAMPLE = "show_lovelace_card_example"
FRONTEND_URL_PATH = "/dte_rates_files"
FRONTEND_CARD_JS = "dte-rates-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await _async_register_frontend(hass)
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _async_register_services(hass)
    coordinator = DteRateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Unable to load DTE rate card: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            _async_unregister_services(hass)
    return unloaded


def _async_register_services(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_RATE_CARD):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH_RATE_CARD, _make_refresh_handler(hass))

    if not hass.services.has_service(DOMAIN, SERVICE_SHOW_RATE_SCHEDULE):
        hass.services.async_register(DOMAIN, SERVICE_SHOW_RATE_SCHEDULE, _make_show_schedule_handler(hass))
    if not hass.services.has_service(DOMAIN, SERVICE_SHOW_CARD_EXAMPLE):
        hass.services.async_register(DOMAIN, SERVICE_SHOW_CARD_EXAMPLE, _make_show_card_example_handler(hass))


def _async_unregister_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_RATE_CARD):
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_RATE_CARD)
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_RATE_SCHEDULE):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_RATE_SCHEDULE)
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_CARD_EXAMPLE):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_CARD_EXAMPLE)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL_PATH,
                str(frontend_path),
                cache_headers=True,
            )
        ]
    )


def _make_refresh_handler(hass: HomeAssistant):
    async def _handle_refresh_service(call) -> None:
        entry_id = call.data.get("entry_id")
        coordinators: list[DteRateCoordinator]
        if entry_id:
            coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
            coordinators = [coordinator] if coordinator else []
        else:
            coordinators = list(hass.data.get(DOMAIN, {}).values())

        for coordinator in coordinators:
            await coordinator.async_request_refresh()

    return _handle_refresh_service


def _make_show_schedule_handler(hass: HomeAssistant):
    async def _handle_show_schedule_service(call) -> None:
        entry_id = call.data.get("entry_id")
        if not entry_id:
            if not hass.data.get(DOMAIN):
                return
            entry_id = next(iter(hass.data[DOMAIN]))

        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if coordinator is None:
            return

        rate_code = call.data.get("rate_code")
        if rate_code:
            rate = coordinator.data.rates.get(rate_code)
        else:
            entry = next((e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id == entry_id), None)
            rate = coordinator.data.rates.get(entry.data.get("selected_rate")) if entry else None

        if rate is None:
            return

        lines_by_season: dict[str, list[str]] = defaultdict(list)
        for period in sorted(rate.periods, key=lambda p: (p.season_name, p.period_name)):
            import_usd = float(current_import_rate_cents(period) / 100)
            export_usd = float(current_export_rate_cents(period, False) / 100)
            lines_by_season[period.season_name].append(
                f"{period_display_name(period)}: Import ${import_usd:.4f}/kWh | Export ${export_usd:.4f}/kWh"
            )

        lines = [f"{rate.name} ({rate.code})"]
        for season in sorted(lines_by_season):
            lines.append("")
            lines.append(f"[{season}]")
            lines.extend(lines_by_season[season])

        persistent_notification.async_create(
            hass,
            "\n".join(lines),
            title="DTE Rate Schedule",
            notification_id=f"dte_rates_schedule_{entry_id}",
        )

    return _handle_show_schedule_service


def _make_show_card_example_handler(hass: HomeAssistant):
    async def _handle_show_card_example(_call) -> None:
        message = (
            "Add this Lovelace resource:\\n"
            f"URL: {FRONTEND_URL_PATH}/{FRONTEND_CARD_JS}\\n"
            "Type: JavaScript module\\n\\n"
            "Then add this card:\\n\\n"
            "type: custom:dte-rates-card\\n"
            "title: DTE Residential Rates\\n"
            "import_entity: sensor.dte_import_rate\\n"
            "export_entity: sensor.dte_export_rate\\n"
            "name_entity: sensor.dte_current_rate_name\\n"
            "schedule_entity: sensor.dte_rate_schedule\\n"
        )
        persistent_notification.async_create(
            hass,
            message,
            title="DTE Lovelace Card Setup",
            notification_id="dte_rates_lovelace_card_setup",
        )

    return _handle_show_card_example
