# Rider 18 Export Rates

## Sources

- Enhancement request: calculate Rider 18 export credits to match DTE's Rider 18 calculator.
- Residential rate card: source of the active generation components for each rate period.
- MPSC DTE electric rate book: source of current PSCR factors by tariff code.

## Implementation Decision

Do not use the Rider 18 calculator workbook's period-specific outflow credits as the authoritative rates. PSCR factors are parsed dynamically by tariff code from the MPSC DTE electric rate book PDF at `https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/rate-books/electric/dte/dtee1cur.pdf`, because the residential rate card PDF does not include those factors.

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

The setup flow reports how many MPSC tariff PSCR factors were loaded. Export entities expose the selected rate's PSCR value, the PSCR source URL, and the full parsed `pscr_rates` map.

The MPSC rate book can mention `C8.5 Surcharges and Credits Applicable to Power Supply Service` in the front-matter index before the real tariff table. Parser logic must scan candidate C8.5 sections until it finds tariff rows, otherwise it can stop at the index, see no PSCR rows, and incorrectly log that the rate book does not contain PSCR tariff rows.

Export entities expose whether the active period has enough data for the full formula:

- `export_rate_source: rider18_formula` when generation components and PSCR are present.
- `export_rate_source: rider18_formula_incomplete` when one side of the formula is missing.
- `export_rate_source: net_metering` when net metering is enabled.

Issue 3 added an `include_pscr` setting. When PSCR is intentionally disabled, the Rider 18 formula uses generation components only and does not treat the omitted PSCR add-on as an incomplete parse.
