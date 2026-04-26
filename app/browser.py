from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: bool) -> None:
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless
        )

    async def create_context(self, storage_state=None) -> tuple[BrowserContext, Page]:
        if self.browser is None:
            raise RuntimeError("Browser not started")

        context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = await context.new_page()
        return context, page

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()