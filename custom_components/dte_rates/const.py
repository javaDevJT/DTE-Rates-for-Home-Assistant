from datetime import timedelta

DOMAIN = "dte_rates"
RATE_CARD_URL = (
    "https://www.dteenergy.com/content/dam/dteenergy/deg/website/"
    "residential/Service-Request/pricing/residential-pricing-options/"
    "ResidentialElectricRateCard.pdf"
)
PSCR_RATE_BOOK_URL = (
    "https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/"
    "rate-books/electric/dte/dtee1cur.pdf"
)

UPDATE_INTERVAL = timedelta(days=1)

CONF_SELECTED_RATE = "selected_rate"
CONF_NET_METERING = "net_metering"
CONF_INCLUDE_PSCR = "include_pscr"
CONF_TAX_RATE = "tax_rate"

DEFAULT_INCLUDE_PSCR = True
DEFAULT_TAX_RATE_PERCENT = "4.0"

ATTR_RATE_CODE = "rate_code"
ATTR_RATE_NAME = "rate_name"
ATTR_SEASON = "season"
ATTR_PERIOD = "period"
ATTR_COMPONENTS = "components"
ATTR_MONTHLY_COMPONENTS = "monthly_components"
ATTR_SOURCE_URL = "source_url"
ATTR_PSCR_CENTS = "pscr_cents"
ATTR_PSCR_RATE_CODE = "pscr_rate_code"
ATTR_PSCR_RATES = "pscr_rates"
ATTR_PSCR_SOURCE_URL = "pscr_source_url"
ATTR_RIDER18_EXPORT_AVAILABLE = "rider18_export_available"
ATTR_EXPORT_RATE_SOURCE = "export_rate_source"
ATTR_EXPORT_RATE_WARNING = "export_rate_warning"
ATTR_INCLUDE_PSCR = "include_pscr"
ATTR_TAX_RATE_PERCENT = "tax_rate_percent"
ATTR_CARD_EFFECTIVE_DATE = "card_effective_date"
ATTR_SELECTED_RATE_AVAILABLE = "selected_rate_available"
ATTR_WARNING = "warning"
ATTR_CURRENT_RATE_NAME = "current_rate_name"
ATTR_CURRENT_RATE_CALCULATION = "current_rate_calculation"
ATTR_CURRENT_RATE_FORMULA = "current_rate_formula"
ATTR_NEXT_RATE_CHANGE = "next_rate_change"
ATTR_NEXT_RATE_NAME = "next_rate_name"
ATTR_NEXT_RATE_VALUE = "next_rate_value"
ATTR_SCHEDULE_TEXT = "schedule_text"
ATTR_SCHEDULE_BY_SEASON = "schedule_by_season"
