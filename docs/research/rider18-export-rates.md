# Rider 18 Export Rates

## Sources

- Enhancement request: calculate Rider 18 export credits to match DTE's Rider 18 calculator.
- Residential rate card: source of the active generation components for each rate period.
- MPSC DTE electric rate book: source of the current PSCR scalar.

## Implementation Decision

Do not use the Rider 18 calculator workbook's period-specific outflow credits as the authoritative rates. PSCR is parsed dynamically from the MPSC DTE electric rate book PDF at `https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/rate-books/electric/dte/dtee1cur.pdf`, because the residential rate card PDF does not include that scalar.

Formula:

```text
Rider 18 export credit = generation components + PSCR
```

The parsed rate card identifies generation components by keys containing `capacity_energy` or `non_capacity_energy`.

Validation against the live D1.11 workbook on May 11, 2026 showed that DTE's workbook calculates:

```text
Rider 18 Tariff (No PSCR) = Capacity Charges + Non-Capacity Charges
Outflow Credit Incl. PSCR = Rider 18 Tariff (No PSCR) + PSCR
```

D1.11 examples:

| Period | Generation | PSCR | Expected export credit |
| --- | ---: | ---: | ---: |
| Summer On-Peak | `14.407¢/kWh` | `1.877¢/kWh` | `16.284¢/kWh` |
| Summer Off-Peak | `8.709¢/kWh` | `1.877¢/kWh` | `10.586¢/kWh` |
| Winter On-Peak | `10.319¢/kWh` | `1.877¢/kWh` | `12.196¢/kWh` |
| Winter Off-Peak | `8.709¢/kWh` | `1.877¢/kWh` | `10.586¢/kWh` |

For net metering, keep the existing behavior: export uses the full active import rate from the selected rate plan.

## UI/Entity Status

The setup flow explains that Rider 18 export credits use parsed generation plus PSCR when the PSCR value is available. Export entities expose whether the active period has enough data for the full formula:

- `export_rate_source: rider18_formula` when generation components and PSCR are present.
- `export_rate_source: rider18_formula_incomplete` when one side of the formula is missing.
- `export_rate_source: net_metering` when net metering is enabled.
