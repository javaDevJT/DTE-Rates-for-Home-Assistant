from __future__ import annotations

from datetime import timedelta

from custom_components.dte_rates.const import UPDATE_INTERVAL


def test_rate_card_and_pscr_refresh_daily_for_current_month_accuracy():
    assert UPDATE_INTERVAL <= timedelta(days=1)
