import asyncio
import json
import re
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from app.browser import BrowserManager
from app.config import Settings, SESSION_FILE
from app.models import PostRef, PostStats, ProfileStats
from app.parser import parse_count, extract_hashtags, choose_caption
from app.session import SessionManager

class InstagramStatsScraper:
    def __init__(self, **kwargs) -> None:
        settings = Settings()
        self.username = settings.instagram_username
        self.password = settings.instagram_password
        self.profile_url = kwargs.get("profile_url") or settings.instagram_profile_url
        self.max_posts = kwargs.get("max_posts") or settings.max_posts
        self.headless = kwargs.get("headless") if kwargs.get("headless") is not None else settings.headless_mode
        self.exclude_pinned = kwargs.get("exclude_pinned") if kwargs.get("exclude_pinned") is not None else settings.exclude_pinned

        self.browser_manager = BrowserManager(self.headless)
        self.session_manager = SessionManager(SESSION_FILE)
        
        # Carpeta para auditoría de archivos brutos
        self.output_dir = Path("scraped_json")
        self.output_dir.mkdir(exist_ok=True)

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
            if self.context: await self.context.close()
            self.context, self.page = await self.browser_manager.create_context()
            await self.session_manager.login(self.page, self.username, self.password)
            await self.session_manager.save(self.context)

    async def scrape_post(self, post: PostRef, idx: int) -> PostStats:
        target_shortcode = post.url.rstrip("/").split("/")[-1]
        full_raw_data = {}

        try:
            print(f"🚀 [{idx}] Procesando datos de: {post.url}")
            await self.page.goto(post.url, wait_until="domcontentloaded", timeout=30000)

            # 1. Recorte de precisión desde el código fuente (Fuentes)
            raw_html_content = await self.page.content()
            search_key = '"xdt_api__v1__media__shortcode__web_info":'
            start_index = raw_html_content.find(search_key)

            if start_index != -1:
                json_start = raw_html_content.find('{', start_index)
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(raw_html_content)):
                    if raw_html_content[i] == '{': brace_count += 1
                    elif raw_html_content[i] == '}': brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
                
                if json_end != -1:
                    try:
                        full_raw_data = json.loads(raw_html_content[json_start:json_end])
                    except: pass

        except Exception as e:
            print(f"❌ Error de navegación: {e}")

        # --- EXTRACCIÓN DE DATOS REQUERIDOS ---

        media_data = self._find_media_object(full_raw_data, target_shortcode)

        likes = media_data.get("like_count")
        if likes is None:
            likes = 0

        comments = media_data.get("comment_count")
        if comments is None:
            comments = 0

        caption_data = media_data.get("caption", {})
        caption_text = ""
        if isinstance(caption_data, dict):
            caption_text = caption_data.get("text") or ""

        # 3. Fecha (taken_at)
        fecha_unix = full_raw_data.get("taken_at", "")

        return PostStats(
            index=idx,
            tipo="Reel" if "/reel/" in post.url else "Post",
            fecha=str(fecha_unix),
            likes=int(likes),
            comentarios=int(comments),
            hashtags=extract_hashtags(caption_text), # Extrae hashtags del texto obtenido
            url=post.url,
            caption=caption_text, # El texto limpio que querías
            raw_json=full_raw_data # Mantenemos el bruto por si necesitas más datos luego
        )

    def _find_media_object(self, data, code):
        """Busca recursivamente el objeto que contiene el shortcode"""
        if isinstance(data, dict):
            if data.get("shortcode") == code or data.get("code") == code:
                return data
            for v in data.values():
                res = self._find_media_object(v, code)
                if res: return res
        elif isinstance(data, list):
            for item in data:
                res = self._find_media_object(item, code)
                if res: return res
        return {}

    async def get_profile_info(self) -> ProfileStats:
        profile = ProfileStats(profile_url=self.profile_url)
        profile.username = self.profile_url.rstrip("/").split("/")[-1]

        captured_jsons = []

        async def capture_response(response):
            try:
                if "instagram.com" not in response.url:
                    return

                if response.status != 200:
                    return

                content_type = response.headers.get("content-type", "")
                if "json" not in content_type:
                    return

                data = await response.json()
                captured_jsons.append(data)

            except Exception:
                pass

        def find_profile_data(obj):
            if isinstance(obj, dict):
                username = obj.get("username")

                if username == profile.username:
                    return obj

                user = obj.get("user")
                if isinstance(user, dict) and user.get("username") == profile.username:
                    return user

                for value in obj.values():
                    found = find_profile_data(value)
                    if found:
                        return found

            elif isinstance(obj, list):
                for item in obj:
                    found = find_profile_data(item)
                    if found:
                        return found

            return None

        def get_count(data, possible_keys):
            for key in possible_keys:
                value = data.get(key)

                if isinstance(value, int):
                    return value

                if isinstance(value, dict):
                    count = value.get("count")
                    if isinstance(count, int):
                        return count

            return 0

        try:
            self.page.on("response", capture_response)

            await self.page.goto(
                self.profile_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            await self.page.wait_for_timeout(7000)

            profile_data = None

            for data in captured_jsons:
                profile_data = find_profile_data(data)
                if profile_data:
                    break

            if profile_data:
                profile.full_name = profile_data.get("full_name") or ""
                profile.biography = profile_data.get("biography") or ""
                profile.is_verified = bool(profile_data.get("is_verified"))

                profile.followers = get_count(profile_data, [
                    "follower_count",
                    "followers",
                    "edge_followed_by"
                ])

                profile.following = get_count(profile_data, [
                    "following_count",
                    "following",
                    "edge_follow"
                ])

                profile.posts_count = get_count(profile_data, [
                    "media_count",
                    "posts_count",
                    "edge_owner_to_timeline_media"
                ])

                print(f"✅ Perfil encontrado: @{profile.username}")
                print(f"👥 Followers: {profile.followers}")
                print(f"➡️ Following: {profile.following}")
                print(f"🧾 Publicaciones: {profile.posts_count}")

            else:
                print("⚠️ No se encontró JSON del perfil. Se usará solo username.")

        except Exception as e:
            print(f"❌ Error perfil: {e}")

        finally:
            try:
                self.page.remove_listener("response", capture_response)
            except Exception:
                pass

        return profile

    async def get_posts(self) -> list[PostRef]:
        await self.page.goto(self.profile_url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)
        for _ in range(3):
            await self.page.mouse.wheel(0, 2000)
            await self.page.wait_for_timeout(1000)

        items = await self.page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'))
                .filter(a => a.querySelector('img'))
                .map(a => ({ href: a.href, pinned: a.innerText.toLowerCase().includes('pinned') }));
        }""")

        result, seen = [], set()
        for item in (items or []):
            url = item["href"].split("?")[0]
            if url not in seen:
                seen.add(url)
                result.append(PostRef(url=url, pinned=item.get("pinned", False)))
        return result[:self.max_posts]

    async def run_as_api(self):
        try:
            await self.setup_session()

            profile = await self.get_profile_info()
            post_refs = await self.get_posts()

            scraped_posts = []
            likes_file = []

            for idx, ref in enumerate(post_refs, 1):
                res = await self.scrape_post(ref, idx)

                post_dict = asdict(res)
                scraped_posts.append(post_dict)

                # Guardar like_count solo si existe
                if res.likes is not None and int(res.likes) > 0:
                    likes_file.append({
                        "index": idx,
                        "url": res.url,
                        "tipo": res.tipo,
                        "like_count": int(res.likes)
                    })

            # Archivo general
            final_data = {
                "username": profile.username,
                "profile": asdict(profile),
                "posts": scraped_posts
            }

            with open(
                f"resultado_{profile.username}.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(final_data, f, indent=4, ensure_ascii=False)

            # Archivo SOLO likes
            with open(
                f"likes_{profile.username}.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(likes_file, f, indent=4, ensure_ascii=False)

            print(f"✅ Archivo general creado")
            print(f"✅ Archivo likes creado")

            return final_data

        finally:
            await self.close()

    async def close(self):
        if self.browser_manager: await self.browser_manager.stop()
