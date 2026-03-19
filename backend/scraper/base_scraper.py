"""
Abstract base class for all site scrapers.
Provides Playwright browser management, throttling, retry, and user-agent rotation.
"""
import asyncio
import random
import logging
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
from scraper.config import USER_AGENTS, MIN_DELAY, MAX_DELAY, MAX_RETRIES, PAGE_TIMEOUT_MS

logger = logging.getLogger("scraper")


class BaseScraper(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self._playwright = None
        self.browser: Browser = None
        self.stats = {
            "pages_visited": 0,
            "colleges_extracted": 0,
            "careers_extracted": 0,
            "exams_extracted": 0,
            "scholarships_extracted": 0,
            "errors": 0,
            "retries": 0,
        }

    async def start_browser(self):
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=True)
        logger.info(f"[{self.source_name}] Browser started")

    async def stop_browser(self):
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"[{self.source_name}] Browser stopped")

    async def new_page(self) -> Page:
        context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            java_script_enabled=True,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )
        page = await context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT_MS)

        # Stealth: hide webdriver fingerprint
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
            window.chrome = { runtime: {} };
        """)
        return page

    async def throttle(self):
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        await asyncio.sleep(delay)

    async def safe_goto(self, page: Page, url: str) -> bool:
        for attempt in range(MAX_RETRIES):
            try:
                await self.throttle()
                response = await page.goto(url, wait_until="domcontentloaded")
                self.stats["pages_visited"] += 1
                if response and response.ok:
                    # Wait a bit for JS to render
                    await page.wait_for_timeout(2000)
                    return True
                logger.warning(
                    f"[{self.source_name}] HTTP {response.status if response else '?'} for {url}"
                )
            except Exception as e:
                self.stats["retries"] += 1
                logger.warning(
                    f"[{self.source_name}] Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}"
                )
                await asyncio.sleep(2 ** attempt)
        self.stats["errors"] += 1
        logger.error(f"[{self.source_name}] All retries exhausted for {url}")
        return False

    async def safe_get_text(self, page: Page, selector: str, default: str = "") -> str:
        try:
            el = await page.query_selector(selector)
            if el:
                return (await el.inner_text()).strip()
        except Exception:
            pass
        return default

    async def safe_get_texts(self, page: Page, selector: str) -> list[str]:
        try:
            elements = await page.query_selector_all(selector)
            texts = []
            for el in elements:
                t = (await el.inner_text()).strip()
                if t:
                    texts.append(t)
            return texts
        except Exception:
            return []

    async def safe_get_attr(self, page: Page, selector: str, attr: str, default: str = "") -> str:
        try:
            el = await page.query_selector(selector)
            if el:
                val = await el.get_attribute(attr)
                return val.strip() if val else default
        except Exception:
            pass
        return default

    @abstractmethod
    async def scrape_colleges(self) -> list[dict]:
        ...

    @abstractmethod
    async def scrape_careers(self) -> list[dict]:
        ...

    @abstractmethod
    async def scrape_exams(self) -> list[dict]:
        ...

    @abstractmethod
    async def scrape_scholarships(self) -> list[dict]:
        ...

    async def run(self) -> dict:
        try:
            await self.start_browser()
            logger.info(f"[{self.source_name}] Starting scrape")

            colleges = await self.scrape_colleges()
            self.stats["colleges_extracted"] = len(colleges)

            careers = await self.scrape_careers()
            self.stats["careers_extracted"] = len(careers)

            exams = await self.scrape_exams()
            self.stats["exams_extracted"] = len(exams)

            scholarships = await self.scrape_scholarships()
            self.stats["scholarships_extracted"] = len(scholarships)

            logger.info(
                f"[{self.source_name}] Scrape complete: "
                f"{len(colleges)} colleges, {len(careers)} careers, "
                f"{len(exams)} exams, {len(scholarships)} scholarships"
            )
            return {
                "source": self.source_name,
                "colleges": colleges,
                "careers": careers,
                "exams": exams,
                "scholarships": scholarships,
                "stats": dict(self.stats),
            }
        except Exception as e:
            logger.error(f"[{self.source_name}] Scraper crashed: {e}")
            raise
        finally:
            await self.stop_browser()
