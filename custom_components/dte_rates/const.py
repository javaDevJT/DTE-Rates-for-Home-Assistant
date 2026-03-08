from datetime import timedelta

DOMAIN = "dte_rates"
RATE_CARD_URL = (
    "https://www.dteenergy.com/content/dam/dteenergy/deg/website/"
    "residential/Service-Request/pricing/residential-pricing-options/"
    "ResidentialElectricRateCard.pdf"
)

UPDATE_INTERVAL = timedelta(days=7)

CONF_SELECTED_RATE = "selected_rate"
CONF_NET_METERING = "net_metering"

ATTR_RATE_CODE = "rate_code"
ATTR_RATE_NAME = "rate_name"
ATTR_SEASON = "season"
ATTR_PERIOD = "period"
ATTR_COMPONENTS = "components"
ATTR_MONTHLY_COMPONENTS = "monthly_components"
ATTR_SOURCE_URL = "source_url"
ATTR_CARD_EFFECTIVE_DATE = "card_effective_date"
ATTR_SELECTED_RATE_AVAILABLE = "selected_rate_available"
ATTR_WARNING = "warning"
ATTR_CURRENT_RATE_NAME = "current_rate_name"
ATTR_NEXT_RATE_CHANGE = "next_rate_change"
ATTR_NEXT_RATE_NAME = "next_rate_name"
ATTR_NEXT_RATE_VALUE = "next_rate_value"
ATTR_SCHEDULE_TEXT = "schedule_text"
ATTR_SCHEDULE_BY_SEASON = "schedule_by_season"
