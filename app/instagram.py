import asyncio
import json
import re

from app.browser import BrowserManager
from app.config import Settings, SESSION_FILE
from app.models import PostRef, PostStats, ProfileStats
from app.parser import parse_count, extract_hashtags, choose_caption
from app.session import SessionManager


class InstagramStatsScraper:
    def __init__(
        self,
        profile_url: str | None = None,
        max_posts: int | None = None,
        exclude_pinned: bool | None = None,
        headless: bool | None = None,
    ) -> None:
        settings = Settings()

        self.username = settings.instagram_username
        self.password = settings.instagram_password
        self.profile_url = profile_url or settings.instagram_profile_url
        self.max_posts = max_posts if max_posts is not None else settings.max_posts
        self.headless = headless if headless is not None else settings.headless_mode
        self.exclude_pinned = (
            exclude_pinned if exclude_pinned is not None else settings.exclude_pinned
        )

        self.browser_manager = BrowserManager(self.headless)
        self.session_manager = SessionManager(SESSION_FILE)

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
            await self.session_manager.login(self.page, self.username, self.password)
            await self.session_manager.save(self.context)

    async def get_profile_info(self) -> ProfileStats:
        await self.page.goto(self.profile_url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)

        profile = ProfileStats(profile_url=self.profile_url)

        try:
            text = await self.page.inner_text("main")
        except Exception:
            text = ""

        try:
            scripts = await self.page.query_selector_all('script[type="application/ld+json"]')
            for sc in scripts:
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

                    alt_name = item.get("alternateName")
                    if alt_name:
                        profile.username = alt_name.replace("@", "")

                    if item.get("name"):
                        profile.full_name = item.get("name")

                    if item.get("description"):
                        profile.biography = item.get("description")

                    stats = item.get("interactionStatistic")
                    if isinstance(stats, list):
                        for stat in stats:
                            if not isinstance(stat, dict):
                                continue
                            if stat.get("@type") == "FollowAction" and stat.get("userInteractionCount") is not None:
                                profile.followers = int(stat["userInteractionCount"])
                    elif isinstance(stats, dict):
                        if stats.get("@type") == "FollowAction" and stats.get("userInteractionCount") is not None:
                            profile.followers = int(stats["userInteractionCount"])

                    break
        except Exception:
            pass

        numbers = re.findall(
            r'([\d.,]+(?:\s*(?:mil|mill\.|M|K))?)\s+(publicaciones|posts|followers|seguidores|following|seguidos)',
            text,
            re.I,
        )

        for value, label in numbers:
            parsed_value = parse_count(value)
            label = label.lower()

            if label in {"publicaciones", "posts"}:
                profile.posts_count = parsed_value
            elif label in {"followers", "seguidores"}:
                profile.followers = parsed_value
            elif label in {"following", "seguidos"}:
                profile.following = parsed_value

        if not profile.username:
            profile.username = self.profile_url.rstrip("/").split("/")[-1]

        return profile

    async def get_posts(self) -> list[PostRef]:
        await self.page.goto(self.profile_url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)

        # scroll para cargar más miniaturas
        for _ in range(4):
            await self.page.mouse.wheel(0, 1800)
            await self.page.wait_for_timeout(1200)

        items = await self.page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'));

            const rows = anchors
                .filter(a => a.querySelector('img'))
                .map((a, idx) => {
                    const rect = a.getBoundingClientRect();
                    const text = (a.innerText || '').toLowerCase();
                    const aria = (a.getAttribute('aria-label') || '').toLowerCase();
                    const html = (a.outerHTML || '').toLowerCase();

                    const pinned =
                        text.includes('pinned') ||
                        text.includes('anclada') ||
                        aria.includes('pinned') ||
                        aria.includes('anclada') ||
                        html.includes('pinned') ||
                        html.includes('anclada');

                    return {
                        href: a.href || a.getAttribute('href'),
                        top: Math.round(rect.top + window.scrollY),
                        left: Math.round(rect.left + window.scrollX),
                        idx,
                        pinned
                    };
                })
                .filter(x => x.href);

            rows.sort((a, b) => {
                if (Math.abs(a.top - b.top) > 25) return a.top - b.top;
                if (a.left !== b.left) return a.left - b.left;
                return a.idx - b.idx;
            });

            return rows;
        }
        """)

        result: list[PostRef] = []
        seen = set()

        for item in items:
            url = item["href"].split("?")[0].strip()

            if url.startswith("/"):
                url = "https://www.instagram.com" + url

            if "/p/" not in url and "/reel/" not in url:
                continue

            if url in seen:
                continue

            seen.add(url)
            result.append(PostRef(url=url, pinned=item.get("pinned", False)))

        if self.exclude_pinned:
            result = [x for x in result if not x.pinned]

        return result[: self.max_posts]
    
    async def scrape_post(self, post: PostRef, idx: int) -> PostStats:
        await self.page.goto(post.url, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(1500)

        fecha = ""
        likes = 0
        comentarios = 0
        caption = ""
        hashtags: list[str] = []

        # fecha
        try:
            time_el = await self.page.query_selector("time")
            if time_el:
                fecha = await time_el.get_attribute("datetime") or ""
        except Exception:
            pass

        # leer solo una vez el texto principal
        text = ""
        try:
            text = await self.page.inner_text("main")
        except Exception:
            try:
                text = await self.page.inner_text("body")
            except Exception:
                text = ""

        # JSON-LD primero: caption, likes y comentarios
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

                    # caption
                    if not caption:
                        for key in ["caption", "articleBody", "description", "name"]:
                            value = item.get(key)
                            if isinstance(value, str) and len(value.strip()) > 10:
                                caption = value.strip()
                                break

                    # comentarios
                    if comentarios == 0 and item.get("commentCount") is not None:
                        comentarios = int(item["commentCount"])

                    # likes
                    stats = item.get("interactionStatistic")
                    if likes == 0:
                        if isinstance(stats, dict):
                            count = stats.get("userInteractionCount")
                            if count is not None:
                                likes = parse_count(str(count))

                        elif isinstance(stats, list):
                            for stat in stats:
                                if not isinstance(stat, dict):
                                    continue
                                count = stat.get("userInteractionCount")
                                if count is not None:
                                    likes = parse_count(str(count))
                                    if likes > 0:
                                        break

                if caption and likes > 0 and comentarios > 0:
                    break

        except Exception:
            pass

        # respaldo rápido para likes
        if likes == 0:
            for pattern in [
                r'(\d+[.,]?\d*\s*mill\.)',
                r'(\d+[.,]?\d*\s*mil)',
                r'(\d+[.,]?\d*\s*M)\b',
                r'(\d+[.,]?\d*\s*K)\b',
                r'(\d{1,3}(?:[.,]\d{3})+)',
                r'\b(\d{3,})\b',
            ]:
                m = re.search(pattern, text, re.I)
                if m:
                    likes = parse_count(m.group(1))
                    if likes > 0:
                        break

        # respaldo rápido para comentarios
        # respaldo rápido para comentarios desde scripts del post actual
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

        # caption final
        if not caption:
            caption = choose_caption(text)

        hashtags = extract_hashtags(f"{caption} {text}")

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

    async def run_as_api(self):
        try:
            await self.setup_session()

            profile = await self.get_profile_info()
            posts = await self.get_posts()

            rows: list[dict] = []
            for idx, post in enumerate(posts):
                row = await self.scrape_post(post, idx)
                rows.append({
                    "index": row.index,
                    "tipo": row.tipo,
                    "fecha": row.fecha,
                    "likes": row.likes,
                    "comentarios": row.comentarios,
                    "hashtags": row.hashtags,
                    "url": row.url,
                    "caption": row.caption,
                })
                await asyncio.sleep(0.5)

            return {
                "profile": {
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "biography": profile.biography,
                    "followers": profile.followers,
                    "following": profile.following,
                    "posts_count": profile.posts_count,
                    "is_verified": profile.is_verified,
                    "profile_url": profile.profile_url,
                },
                "posts": rows,
            }
        finally:
            if self.context:
                await self.context.close()
            await self.browser_manager.stop()

    async def run(self) -> None:
        result = await self.run_as_api()
        print(json.dumps(result, ensure_ascii=False, indent=2))