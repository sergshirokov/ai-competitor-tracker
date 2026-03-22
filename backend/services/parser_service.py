"""
Парсинг веб-страниц через Playwright (Chromium) со снижением признаков автоматизации.
После pip install: playwright install chromium

На Windows async Playwright вызывает asyncio.create_subprocess_exec; под uvicorn/debugpy
часто активен цикл без Proactor → NotImplementedError. Поэтому используется sync API
в отдельном потоке (asyncio.to_thread).
"""
import asyncio
import base64
import logging
import time
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from backend.config import settings

logger = logging.getLogger("competitor_monitor.parser")

_CHROMIUM_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--window-size=1920,1080",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-extensions",
    "--no-first-run",
    "--no-default-browser-check",
)


def _navigator_languages_tuple() -> Tuple[str, str]:
    parts = [x.strip() for x in settings.parser_navigator_languages.split(",") if x.strip()][:2]
    if len(parts) >= 2:
        return (parts[0], parts[1])
    if len(parts) == 1:
        return (parts[0], "en")
    return ("en-US", "en")


class ParserService:
    """Парсинг страниц через Playwright + stealth-скрипты, скриншот viewport."""

    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация Parser сервиса (Playwright, sync в потоке)")
        logger.info(f"  Timeout (операции страницы): {settings.parser_timeout} сек")
        logger.info(f"  Timeout навигации (goto): {settings.parser_navigation_timeout} сек")
        logger.info(f"  User-Agent: {settings.parser_user_agent[:60]}...")
        logger.info(f"  Locale: {settings.parser_locale}, TZ: {settings.parser_timezone}")
        logger.info("=" * 50)

    def _build_stealth(self) -> Stealth:
        langs = _navigator_languages_tuple()
        return Stealth(
            navigator_user_agent_override=settings.parser_user_agent,
            navigator_languages_override=langs,
            navigator_platform_override=settings.parser_platform,
            chrome_runtime=True,
            navigator_webdriver=True,
            navigator_plugins=True,
            sec_ch_ua=True,
        )

    def _parse_sync(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        """Синхронный парсинг (вызывается из asyncio.to_thread)."""
        logger.info("=" * 50)
        logger.info(f"🔍 ПАРСИНГ САЙТА: {url}")
        total_start = time.perf_counter()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=settings.parser_headless,
                    args=list(_CHROMIUM_ARGS),
                )
                context = None
                try:
                    context = browser.new_context(
                        user_agent=settings.parser_user_agent,
                        viewport={"width": 1920, "height": 1080},
                        locale=settings.parser_locale,
                        timezone_id=settings.parser_timezone,
                        device_scale_factor=1,
                        has_touch=False,
                        is_mobile=False,
                        color_scheme="light",
                        extra_http_headers={
                            "Accept-Language": settings.parser_accept_language,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                            "Sec-Fetch-Dest": "document",
                            "Sec-Fetch-Mode": "navigate",
                            "Sec-Fetch-Site": "none",
                            "Sec-Fetch-User": "?1",
                            "Upgrade-Insecure-Requests": "1",
                        },
                    )
                    stealth = self._build_stealth()
                    stealth.apply_stealth_sync(context)

                    page = context.new_page()
                    page.set_default_timeout(settings.parser_timeout * 1000)
                    nav_timeout_ms = settings.parser_navigation_timeout * 1000

                    logger.info("  📄 Загрузка страницы...")
                    page_start = time.perf_counter()
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=nav_timeout_ms,
                    )
                    page_elapsed = time.perf_counter() - page_start
                    logger.info(f"  ✓ Страница загружена за {page_elapsed:.2f} сек")

                    logger.info("  ⏳ Ожидание body...")
                    page.wait_for_selector("body", timeout=settings.parser_timeout * 1000)
                    logger.info("  ✓ Body найден")

                    logger.info("  ⏳ Ожидание динамического контента (2 сек)...")
                    time.sleep(2)

                    title = page.title()
                    logger.info(f"  📌 Title: {title[:60] if title else 'N/A'}...")

                    h1 = None
                    try:
                        if page.locator("h1").count() > 0:
                            t = page.locator("h1").first.inner_text().strip()
                            h1 = t or None
                            logger.info(f"  📌 H1: {h1[:60] if h1 else 'N/A'}...")
                    except Exception as e:
                        logger.debug(f"  H1 не найден: {e}")

                    first_paragraph = None
                    try:
                        paras = page.locator("p")
                        n = paras.count()
                        logger.debug(f"  Найдено абзацев: {n}")
                        for i in range(min(n, 50)):
                            text = paras.nth(i).inner_text().strip()
                            if len(text) > 50:
                                first_paragraph = text[:500]
                                logger.info(f"  📌 Первый абзац (p[{i}]): {first_paragraph[:60]}...")
                                break
                    except Exception as e:
                        logger.debug(f"  Абзацы: {e}")

                    logger.info("  📸 Создание скриншота...")
                    shot_start = time.perf_counter()
                    screenshot_bytes = page.screenshot(type="png", full_page=False)
                    shot_elapsed = time.perf_counter() - shot_start
                    screenshot_size_kb = len(screenshot_bytes) / 1024
                    logger.info(f"  ✓ Скриншот за {shot_elapsed:.2f} сек ({screenshot_size_kb:.1f} KB)")

                    total_elapsed = time.perf_counter() - total_start
                    logger.info(f"  ✅ ПАРСИНГ ЗАВЕРШЁН за {total_elapsed:.2f} сек")
                    logger.info("=" * 50)

                    return title, h1, first_paragraph, screenshot_bytes, None
                finally:
                    if context:
                        context.close()
                    browser.close()

        except PlaywrightTimeoutError:
            total_elapsed = time.perf_counter() - total_start
            logger.error(f"  ✗ TIMEOUT за {total_elapsed:.2f} сек")
            logger.error("=" * 50)
            return None, None, None, None, "Превышено время ожидания загрузки страницы"

        except PlaywrightError as e:
            total_elapsed = time.perf_counter() - total_start
            error_msg = str(e)
            logger.error(f"  ✗ Playwright ошибка за {total_elapsed:.2f} сек")
            logger.error(f"  Детали: {error_msg[:200]}")
            logger.error("=" * 50)

            if "ERR_NAME_NOT_RESOLVED" in error_msg:
                return None, None, None, None, "Не удалось найти сайт по указанному адресу"
            if "ERR_CONNECTION_REFUSED" in error_msg:
                return None, None, None, None, "Соединение отклонено сервером"
            if "ERR_CONNECTION_TIMED_OUT" in error_msg or "Timeout" in error_msg:
                return None, None, None, None, "Превышено время ожидания соединения"
            return None, None, None, None, f"Ошибка браузера: {error_msg[:200]}"

        except Exception as e:
            total_elapsed = time.perf_counter() - total_start
            logger.error(f"  ✗ Ошибка за {total_elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            return None, None, None, None, f"Ошибка при загрузке страницы: {str(e)[:200]}"

    async def parse_url(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        if not url.startswith(("http://", "https://")):
            original_url = url
            url = "https://" + url
            logger.info(f"  URL дополнен протоколом: {original_url} -> {url}")

        logger.info(f"🚀 Парсинг: {url}")
        return await asyncio.to_thread(self._parse_sync, url)

    def screenshot_to_base64(self, screenshot_bytes: bytes) -> str:
        base64_str = base64.b64encode(screenshot_bytes).decode("utf-8")
        logger.debug(f"Скриншот в base64: {len(base64_str)} символов")
        return base64_str

    async def close(self):
        logger.info("Parser сервис: close() — нет удерживаемых ресурсов")


logger.info("Создание глобального экземпляра Parser сервиса...")
parser_service = ParserService()
