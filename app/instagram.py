import json
import re
from dataclasses import asdict
from datetime import datetime, timezone

from app.browser import BrowserManager
from app.config import Settings, SESSION_FILE
from app.models import PostRef, PostStats, ProfileStats
from app.parser import parse_count, extract_hashtags
from app.session import SessionManager


class InstagramStatsScraper:
    def __init__(self, **kwargs) -> None:
        settings = Settings()

        self.username = settings.instagram_username
        self.password = settings.instagram_password
        self.profile_url = kwargs.get("profile_url") or settings.instagram_profile_url
        self.max_posts = kwargs.get("max_posts") or settings.max_posts
        self.headless = True
        self.exclude_pinned = kwargs.get("exclude_pinned") if kwargs.get("exclude_pinned") is not None else settings.exclude_pinned

        self.browser_manager = BrowserManager(self.headless)
        self.session_manager = SessionManager(SESSION_FILE)

        self.context = None
        self.page = None

    async def setup_session(self) -> None:
        await self.browser_manager.start()

        storage = self.session_manager.load_storage_state()
        self.context, self.page = await self.browser_manager.create_context(storage_state=storage)

        try:
            is_valid = await self.session_manager.is_valid(self.page)
        except Exception:
            is_valid = False

        if not is_valid:
            if self.context:
                await self.context.close()

            self.context, self.page = await self.browser_manager.create_context()
            await self.session_manager.login(self.page, self.username, self.password)
            await self.session_manager.save(self.context)

    async def scrape_post(self, post: PostRef, idx: int) -> PostStats:
        shortcode = post.url.rstrip("/").split("/")[-1]
        raw_data = {}

        try:
            await self.page.goto(post.url, wait_until="domcontentloaded", timeout=30000)

            html = await self.page.content()
            search_key = '"xdt_api__v1__media__shortcode__web_info":'
            start_index = html.find(search_key)

            if start_index != -1:
                json_start = html.find("{", start_index)
                json_end = self._find_json_end(html, json_start)

                if json_end != -1:
                    raw_data = json.loads(html[json_start:json_end])

        except Exception as e:
            print(f"❌ Error post {idx}: {e}")

        media = self._find_media_object(raw_data, shortcode)

        likes = int(media.get("like_count") or 0)
        comments = int(media.get("comment_count") or 0)
        fecha = self._format_timestamp(
            media.get("taken_at") or media.get("taken_at_timestamp") or ""
        )

        caption = media.get("caption") or {}
        caption_text = caption.get("text", "") if isinstance(caption, dict) else ""

        return PostStats(
            index=idx,
            tipo="Reel" if "/reel/" in post.url else "Post",
            fecha=fecha,
            likes=likes,
            comentarios=comments,
            hashtags=extract_hashtags(caption_text),
            url=post.url,
            caption=caption_text,
            raw_json=raw_data
        )

    async def get_profile_info(self) -> ProfileStats:
        profile = ProfileStats(profile_url=self.profile_url)
        profile.username = self.profile_url.rstrip("/").split("/")[-1]

        try:
            await self.page.goto(self.profile_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(6000)

            html = await self.page.content()
            body = await self.page.inner_text("body")

            profile.followers = self._extract_visible_count(
                body,
                r"([\d.,]+\s*(?:mil|mill\.?|k|m)?)\s*(?:seguidores|followers)"
            )
            profile.following = self._extract_visible_count(
                body,
                r"([\d.,]+\s*(?:mil|mill\.?|k|m)?)\s*(?:seguidos|following)"
            )
            profile.posts_count = self._extract_visible_count(
                body,
                r"([\d.,]+\s*(?:mil|mill\.?|k|m)?)\s*(?:publicaciones|posts)"
            )

            if profile.followers == 0:
                profile.followers = self._extract_html_count(html, [
                    r'"follower_count":\s*(\d+)',
                    r'"edge_followed_by":\s*\{"count":\s*(\d+)\}',
                    r'"followers":\s*\{"count":\s*(\d+)\}',
                ])

            if profile.following == 0:
                profile.following = self._extract_html_count(html, [
                    r'"following_count":\s*(\d+)',
                    r'"edge_follow":\s*\{"count":\s*(\d+)\}',
                    r'"following":\s*\{"count":\s*(\d+)\}',
                ])

            if profile.posts_count == 0:
                profile.posts_count = self._extract_html_count(html, [
                    r'"media_count":\s*(\d+)',
                    r'"posts_count":\s*(\d+)',
                    r'"edge_owner_to_timeline_media":\s*\{"count":\s*(\d+)\}',
                ])

            profile.full_name = self._extract_string(html, r'"full_name":"(.*?)"')
            profile.biography = self._extract_string(html, r'"biography":"(.*?)"')
            profile.is_verified = '"is_verified":true' in html

        except Exception as e:
            print(f"❌ Error perfil: {e}")

        return profile

    async def get_posts(self) -> list[PostRef]:
        await self.page.goto(self.profile_url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)

        for _ in range(3):
            await self.page.mouse.wheel(0, 2000)
            await self.page.wait_for_timeout(1000)

        items = await self.page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'))
                .filter(a => a.querySelector('img'))
                .map(a => ({
                    href: a.href,
                    pinned: a.innerText.toLowerCase().includes('pinned')
                }))
        """)

        posts = []
        seen = set()

        for item in items or []:
            url = item["href"].split("?")[0]

            if url in seen:
                continue

            seen.add(url)

            ref = PostRef(url=url, pinned=item.get("pinned", False))

            if self.exclude_pinned and ref.pinned:
                continue

            posts.append(ref)

        return posts[:self.max_posts]

    async def run_as_api(self):
        try:
            await self.setup_session()

            profile = await self.get_profile_info()
            post_refs = await self.get_posts()

            posts = []

            for idx, ref in enumerate(post_refs, 1):
                post = await self.scrape_post(ref, idx)
                posts.append(asdict(post))

            return {
                "username": profile.username,
                "profile": asdict(profile),
                "posts": posts
            }

        finally:
            await self.close()

    async def close(self):
        if self.browser_manager:
            await self.browser_manager.stop()

    def _find_json_end(self, text: str, start: int) -> int:
        if start == -1:
            return -1

        brace_count = 0

        for i in range(start, len(text)):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1

            if brace_count == 0:
                return i + 1

        return -1

    def _find_media_object(self, data, code):
        if isinstance(data, dict):
            if data.get("shortcode") == code or data.get("code") == code:
                return data

            for value in data.values():
                found = self._find_media_object(value, code)
                if found:
                    return found

        elif isinstance(data, list):
            for item in data:
                found = self._find_media_object(item, code)
                if found:
                    return found

        return {}

    def _extract_visible_count(self, text: str, pattern: str) -> int:
        match = re.search(pattern, text, re.I)
        return parse_count(match.group(1)) if match else 0

    def _extract_html_count(self, html: str, patterns: list[str]) -> int:
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return int(match.group(1))
        return 0

    def _extract_string(self, html: str, pattern: str) -> str:
        match = re.search(pattern, html)
        return match.group(1) if match else ""

    def _format_timestamp(self, timestamp):
        if not timestamp:
            return ""

        try:
            timestamp = int(timestamp)

            if timestamp > 10_000_000_000:
                timestamp //= 1000

            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

        except Exception:
            return str(timestamp)