import json
from pathlib import Path

class SessionManager:
    def __init__(self, session_file: Path) -> None:
        self.session_file = session_file

    def exists(self) -> bool:
        return self.session_file.exists()

    def load_storage_state(self):
        if not self.exists():
            return None
        with self.session_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    async def save(self, context) -> None:
        storage = await context.storage_state()
        with self.session_file.open("w", encoding="utf-8") as f:
            json.dump(storage, f, indent=2)

    async def is_valid(self, page) -> bool:
        await page.goto("https://www.instagram.com/")
        return "accounts/login" not in page.url

    async def login(self, page, username: str, password: str) -> None:
        await page.goto("https://www.instagram.com/accounts/login/")
        await page.wait_for_timeout(4000)
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(7000)