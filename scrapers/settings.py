BOT_NAME = "price_intelligence"

SPIDER_MODULES = ["scrapers.spiders"]
NEWSPIDER_MODULE = "scrapers.spiders"

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 4
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

FEED_EXPORT_ENCODING = "utf-8"
