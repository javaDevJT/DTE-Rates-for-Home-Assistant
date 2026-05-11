# Rider 18 Export Rates

## Source

- Enhancement request: use DTE Rider 18 calculator rates for export calculations.
- Workbook URL: `https://www.dteenergy.com/content/dam/dteenergy/deg/website/hybris/rooftop-solar/Rider18Calculator.xlsx`

## Workbook Findings

The workbook has a `Rates and Credits` sheet with Rider 18 credit values. The relevant table is labeled `FULL SERVICE - Rider 18 Credits`.

Parser validation on May 11, 2026 downloaded the workbook successfully and extracted D1.11 Rider 18 outflow credits from that sheet.

Observed D1.11 rows:

| Workbook label | Integration season | Integration period | Outflow credit incl. PSCR |
| --- | --- | --- | --- |
| `June-Sept On Peak` | `june_through_september` | `peak` | `$0.16284/kWh` |
| `June-Sept Off Peak` | `june_through_september` | `off_peak` | `$0.10586/kWh` |
| `Oct-May On Peak` | `october_through_may` | `peak` | `$0.12196/kWh` |
| `Oct-May Off Peak` | `october_through_may` | `off_peak` | `$0.10586/kWh` |

The workbook stores credits as negative dollars per kWh. The integration converts them to positive cents per kWh internally so they flow through the same calculator path as PDF-derived rates.

## Implementation Decision

For non-net-metering export calculations, prefer the workbook `Outflow Cred. Incl. PSCR` column when a matching rate, season, and period exists. If Rider 18 data is unavailable or does not contain a matching period, fall back to the PDF generation-only calculation.

For net metering, keep the existing behavior: export uses the full active import rate from the selected rate plan.
