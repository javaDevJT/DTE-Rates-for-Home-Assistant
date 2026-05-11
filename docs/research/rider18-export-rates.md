# Rider 18 Export Rates

## Source

- Enhancement request: calculate Rider 18 export credits from the rate card.
- User-provided formula reference: `Total per-kWh Credit = Generation Rate + Distribution/Transmission Rate`.

## Implementation Decision

Do not use the Rider 18 calculator workbook for export pricing. The integration now derives non-net-metering Rider 18 export credits directly from the parsed residential rate card.

Formula:

```text
Rider 18 export credit = generation components + distribution/transmission components
```

The parsed rate card currently identifies generation components by keys containing `capacity_energy` or `non_capacity_energy`. It identifies distribution/transmission components by keys containing `distribution` or `transmission`.

For net metering, keep the existing behavior: export uses the full active import rate from the selected rate plan.

## UI/Entity Status

The setup flow explains that Rider 18 export credits are calculated from the parsed rate card formula. Export entities expose whether the active period has enough parsed components for the full formula:

- `export_rate_source: rider18_formula` when generation and distribution/transmission components are present.
- `export_rate_source: rider18_formula_incomplete` when one side of the formula is missing.
- `export_rate_source: net_metering` when net metering is enabled.
