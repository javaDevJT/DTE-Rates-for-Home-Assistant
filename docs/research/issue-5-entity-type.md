# Issue 5 Entity Type Warning

## Source

- GitHub issue: https://github.com/javaDevJT/DTE-Rates-for-Home-Assistant/issues/5
- Title: Entity type issue
- Created: 2026-05-29

## Report

Home Assistant logs warnings for `DteImportRateSensor` and `DteExportRateSensor`:

`device_class: monetary` was combined with `state_class: measurement`.

Current Home Assistant sensor validation rejects that combination. Monetary sensors may have no state class, or use state class `total` when the entity represents a total amount. These rate sensors represent a current price in `USD/kWh`, not an accumulating monetary total.

## Decision

- Keep `device_class: monetary`.
- Keep `native_unit_of_measurement: USD/kWh`.
- Remove `state_class` from the import/export price sensors.

This preserves the current-price entity shape while avoiding invalid long-term statistics metadata.

## Reference

- Home Assistant sensor developer docs: https://developers.home-assistant.io/docs/core/entity/sensor/
