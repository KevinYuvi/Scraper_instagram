import asyncio
from app.instagram import InstagramStatsScraper


async def main():
    scraper = InstagramStatsScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())