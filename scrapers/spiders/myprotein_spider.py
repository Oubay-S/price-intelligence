import scrapy


class MyproteinSpider(scrapy.Spider):
    """Optional Scrapy example spider for future marketplace expansion."""

    name = "myprotein"
    allowed_domains = ["myprotein.com"]
    start_urls = ["https://www.myprotein.com/"]

    def parse(self, response):
        self.logger.info("MyProtein spider scaffold loaded: %s", response.url)
        yield {
            "source": "myprotein",
            "status": "scaffold",
            "url": response.url,
        }
