# DTE Residential Rates for Home Assistant

[![Website](https://img.shields.io/badge/Website-javadevjt.tech-0A66C2?logo=googlechrome&logoColor=white)](https://javadevjt.tech)
[![Buy%20Me%20a%20Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-javadevjt-FFDD00?logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/javadevjt)

A Home Assistant custom integration that pulls the official DTE residential electric rate card PDF, parses rates dynamically, and exposes import/export price entities that track time-of-day and season.

## What It Does

- Downloads the live DTE Residential Electric Rate Card PDF.
- Parses plans, periods, windows, and component pricing dynamically.
- Updates on a weekly schedule.
- Exposes entities for:
  - Current import rate (`USD/kWh`)
  - Current export rate (`USD/kWh`)
  - Current rate name (string)
  - Full schedule entity (structured schedule attributes)
- Handles net-metering option for export calculation.
- Warns when a previously selected rate disappears from the latest card.
- Includes a custom Lovelace card (`custom:dte-rates-card`).

## Requirements

- Home Assistant with support for custom integrations.
- Internet access from Home Assistant to:
  - `dteenergy.com` (rate card PDF)

## Installation

### Option A: HACS (Recommended)

1. Open HACS -> Integrations -> three-dot menu -> Custom repositories.
2. Add repository URL `https://github.com/javaDevJT/DTE-Rates-for-Home-Assistant` and set category to **Integration**.
3. Install **DTE Residential Rates** from HACS.
4. Restart Home Assistant.
5. Go to Settings -> Devices & Services -> Add Integration.
6. Search for **DTE Residential Rates** and complete setup.

### Option B: Manual Install

1. Copy the folder:
   - `custom_components/dte_rates`
   into your Home Assistant config directory under:
   - `/config/custom_components/dte_rates`
2. Restart Home Assistant.
3. Go to Settings -> Devices & Services -> Add Integration.
4. Search for **DTE Residential Rates** and complete setup.

## Configuration Flow

During setup you choose:

- **Rate plan** from the currently parsed DTE PDF.
- **Net metering enabled** (checkbox).

## Entities Created

- `DTE Import Rate`
  - `device_class: monetary`
  - `unit: USD/kWh`
- `DTE Export Rate`
  - `device_class: monetary`
  - `unit: USD/kWh`
- `DTE Current Rate Name`
  - string state (example: `Winter Off-Peak`)
- `DTE Rate Schedule`
  - contains structured schedule attributes for dashboard usage

## Key Attributes

Core rate entities include attributes such as:

- `current_rate_name`
- `next_rate_change`
- `next_rate_name`
- `next_rate_value`
- `components`
- `monthly_components`
- `card_effective_date`
- `selected_rate_available`
- `warning` (when selected plan disappears)

## Services

Domain: `dte_rates`

- `dte_rates.refresh_rate_card`
  - Force refresh now (all entries or by `entry_id`).
- `dte_rates.show_rate_schedule`
  - Show parsed schedule in a persistent notification.
- `dte_rates.show_lovelace_card_example`
  - Creates a notification with card resource + YAML example.

## Custom Lovelace Card

Card type: `custom:dte-rates-card`

### Add Card Resource

1. Settings -> Dashboards -> three-dot menu -> Resources.
2. Add resource:
   - URL: `/dte_rates_files/dte-rates-card.js`
   - Type: `JavaScript Module`
3. Save and hard refresh browser.

### Example Card YAML

```yaml
type: custom:dte-rates-card
title: DTE Residential Rates
import_entity: sensor.dte_import_rate
export_entity: sensor.dte_export_rate
name_entity: sensor.dte_current_rate_name
schedule_entity: sensor.dte_rate_schedule
```

## Energy Dashboard Use

Use `DTE Import Rate` as your current electricity price entity (`USD/kWh`) where appropriate in Home Assistant Energy configuration.

## Troubleshooting

### Card updates not visible

- Browser caches card JS aggressively.
- Update resource URL to include a version suffix, for example:
  - `/dte_rates_files/dte-rates-card.js?v=3`
- Then hard refresh browser.

### Logo/branding not showing

- Restart Home Assistant and hard refresh browser.
- Re-create integration entry if metadata is cached.

### Selected rate disappeared

- The integration sets warning attributes and creates persistent notifications.
- Re-open integration config and choose a current rate.

## Notes on Pricing Logic

- Import is full per-kWh total for the active period.
- Export is generation-only unless net metering is enabled.
- Next-rate calculations are schedule-aware and aligned to time boundaries.

## Project Layout

- `custom_components/dte_rates/` -> integration code
- `custom_components/dte_rates/frontend/` -> Lovelace card module
- `custom_components/dte_rates/services.yaml` -> service docs
- `hacs.json` -> HACS metadata

## Support

- Site: [javadevjt.tech](https://javadevjt.tech)
- Buy me a coffee: [buymeacoffee.com/javadevjt](https://buymeacoffee.com/javadevjt)
