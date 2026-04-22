from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: bool) -> None:
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)

    async def create_context(self, storage_state=None) -> tuple[BrowserContext, Page]:
        if not self.browser:
            raise RuntimeError("Browser not started")

        context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 720}
        )
        return context, await context.new_page()

    async def stop(self) -> None:
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()