# Project Notes

This directory stores research and implementation notes that support changes to the DTE Rates integration.

## Structure

- `research/` - Source observations, mapping decisions, and implementation notes gathered while working on external rate-card or calculator data.

Use these notes as context for why parsers map external DTE documents into Home Assistant entities. The code remains the source of truth for behavior.

Current research notes:

- `research/rider18-export-rates.md` - Rider 18 export-rate source mapping and PSCR formula decisions.
- `research/issue-3-rate-modifiers.md` - PSCR/tax modifier defaults and calculation scope for real out-of-pocket rates.
- `research/issue-5-entity-type.md` - Home Assistant monetary sensor state-class warning and entity metadata decision.
