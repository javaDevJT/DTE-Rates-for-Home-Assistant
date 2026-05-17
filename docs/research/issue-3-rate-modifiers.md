# Issue 3 Rate Modifiers

## Source

- GitHub issue: https://github.com/javaDevJT/DTE-Rates-for-Home-Assistant/issues/3
- Title: Rate modifiers for real out-of-pocket rates
- Created: 2026-05-16

## Request Summary

The issue asks for rate modifiers so Home Assistant can show a closer out-of-pocket cost instead of only the raw DTE rate-card kWh values. The requested modifiers are PSCR and taxes, with controls to omit them when the user wants base tariff pricing.

## Decisions

- PSCR is included by default because the current rate card does not include it, and the integration already parses tariff-specific PSCR values from the MPSC DTE electric rate book.
- The refresh interval is daily so the integration re-checks the current-month PSCR source regularly instead of waiting up to a week.
- Users can disable PSCR with an `include_pscr` setting. When disabled, Rider 18 export credits intentionally use generation-only formula components and should not report a missing-PSCR warning.
- The default tax rate is `4.0%`. Michigan Treasury describes residential electricity as taxed at a 4% rate, and MPSC residential bill-charge guidance says utility companies collect 4% sales tax from residential customers.
- The tax rate remains free-form as `tax_rate`, labeled as a percentage. Users can enter `0` to omit taxes from rate calculations.

## Calculation Scope

- Import rates apply PSCR when enabled, then apply the configured tax percentage.
- Rider 18 export credits apply PSCR when enabled but do not apply tax.
- Net-metering export rates use the same modified import rate because they represent the avoided import cost for the selected rate.

## Reference Links

- Michigan Treasury sales and use tax page: https://www.michigan.gov/taxes/business-taxes/sales-use-tax
- MPSC residential electric bill charges PDF: https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/info/tips/electric_residential_bill_charges_final.pdf?rev=e80ef0b163614800b1d8910b9e781775
