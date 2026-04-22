import asyncio
import json
import re

from app.browser import BrowserManager
from app.config import Settings, RESULTS_DIR, SESSION_FILE
from app.excel_exporter import ExcelExporter
from app.models import PostRef, PostStats
from app.parser import parse_count, extract_hashtags, choose_caption
from app.session import SessionManager


class InstagramStatsScraper:
    def __init__(self) -> None:
        self.settings = Settings()
        self.browser_manager = BrowserManager(self.settings.headless_mode)
        self.session_manager = SessionManager(SESSION_FILE)
        self.exporter = ExcelExporter()

        self.context = None
        self.page = None

    async def setup_session(self) -> None:
        await self.browser_manager.start()

        storage = self.session_manager.load_storage_state()
        self.context, self.page = await self.browser_manager.create_context(storage_state=storage)

        is_valid = False
        try:
            is_valid = await self.session_manager.is_valid(self.page)
        except Exception:
            is_valid = False

        if not is_valid:
            if self.context:
                await self.context.close()
            self.context, self.page = await self.browser_manager.create_context()
            await self.session_manager.login(
                self.page,
                self.settings.instagram_username,
                self.settings.instagram_password,
            )
            await self.session_manager.save(self.context)

    async def get_posts(self) -> list[PostRef]:
        await self.page.goto(self.settings.instagram_profile_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(5000)

        for _ in range(4):
            await self.page.mouse.wheel(0, 1800)
            await self.page.wait_for_timeout(1200)

        items = await self.page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'));
            return anchors
                .filter(a => a.querySelector('img'))
                .map((a, idx) => {
                    const rect = a.getBoundingClientRect();
                    const text = (a.innerText || '').toLowerCase();
                    const aria = (a.getAttribute('aria-label') || '').toLowerCase();
                    const html = (a.outerHTML || '').toLowerCase();

                    const pinned =
                        text.includes('pinned') ||
                        aria.includes('pinned') ||
                        html.includes('pinned');

                    return {
                        href: a.href || a.getAttribute('href'),
                        top: Math.round(rect.top + window.scrollY),
                        left: Math.round(rect.left + window.scrollX),
                        idx,
                        pinned
                    };
                })
                .filter(x => x.href)
                .sort((a, b) => {
                    if (Math.abs(a.top - b.top) > 30) return a.top - b.top;
                    if (a.left !== b.left) return a.left - b.left;
                    return a.idx - b.idx;
                });
        }
        """)

        result = []
        seen = set()

        for item in items:
            url = item["href"].split("?")[0].strip()
            if url.startswith("/"):
                url = "https://www.instagram.com" + url
            if url in seen:
                continue
            if "/p/" not in url and "/reel/" not in url:
                continue
            seen.add(url)
            result.append(PostRef(url=url, pinned=item.get("pinned", False)))

        if self.settings.exclude_pinned:
            result = [x for x in result if not x.pinned]

        return result[: self.settings.max_posts]

    async def scrape_post(self, post: PostRef, idx: int) -> PostStats:
        await self.page.goto(post.url)
        await self.page.wait_for_timeout(4000)

        fecha = ""
        likes = 0
        comentarios = 0
        caption = ""
        hashtags = []

        try:
            links = await self.page.query_selector_all("header a[href^='/']")
            for el in links:
                txt = (await el.inner_text()).strip()
                href = await el.get_attribute("href")
        except Exception:
            pass

        try:
            time_el = await self.page.query_selector("time")
            if time_el:
                fecha = await time_el.get_attribute("datetime")
        except Exception:
            pass

        text = ""
        for selector in ["article", "main", "body"]:
            try:
                t = await self.page.inner_text(selector)
                if t:
                    text += "\n" + t
            except Exception:
                pass

        for pattern in [
            r'(\d+[.,]?\d*\s*mill\.)',
            r'(\d+[.,]?\d*\s*mil)',
            r'(\d+[.,]?\d*\s*M)\b',
            r'(\d+[.,]?\d*\s*K)\b'
        ]:
            m = re.search(pattern, text, re.I)
            if m:
                likes = parse_count(m.group(1))
                break

        try:
            ld_scripts = await self.page.query_selector_all('script[type="application/ld+json"]')
            for sc in ld_scripts:
                raw = await sc.inner_text()
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except Exception:
                    continue

                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("commentCount") is not None:
                        comentarios = int(item["commentCount"])
                        break

                if comentarios > 0:
                    break
        except Exception:
            pass

        if comentarios == 0:
            try:
                shortcode = post.url.rstrip("/").split("/")[-1]
                scripts = await self.page.query_selector_all("script")
                for sc in scripts:
                    content = await sc.inner_text()
                    if not content or shortcode not in content:
                        continue
                    for pattern in [
                        r'"comment_count"\s*:\s*(\d+)',
                        r'"edge_media_to_parent_comment"\s*:\s*\{.*?"count"\s*:\s*(\d+)',
                        r'"edge_media_to_comment"\s*:\s*\{.*?"count"\s*:\s*(\d+)'
                    ]:
                        m = re.search(pattern, content, re.DOTALL)
                        if m:
                            comentarios = int(m.group(1))
                            break
                    if comentarios > 0:
                        break
            except Exception:
                pass

        caption = choose_caption(text)
        hashtags = extract_hashtags(f"{text} {caption}")

        return PostStats(
            index=idx + 1,
            tipo="reel" if "/reel/" in post.url else "post",
            fecha=fecha,
            likes=likes,
            comentarios=comentarios,
            hashtags=hashtags,
            url=post.url,
            caption=caption,
        )

    async def run(self) -> None:
        try:
            await self.setup_session()
            posts = await self.get_posts()
            rows = []

            for idx, post in enumerate(posts):
                rows.append(await self.scrape_post(post, idx))
                await asyncio.sleep(2)

            file_path = self.exporter.save(rows, RESULTS_DIR)
            print(file_path)
        finally:
            if self.context:
                await self.context.close()
            await self.browser_manager.stop()