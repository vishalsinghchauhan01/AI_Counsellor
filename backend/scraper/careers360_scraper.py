"""
Scraper for Careers360.com — Uttarakhand colleges, careers, exams, scholarships.
Careers360 uses AJAX-based content loading and may have stricter anti-bot measures.
"""
import logging
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from scraper.base_scraper import BaseScraper
from scraper.config import (
    CAREERS360_LISTING, CAREERS360_CAREERS, CAREERS360_EXAMS,
)

logger = logging.getLogger("scraper.careers360")


class Careers360Scraper(BaseScraper):
    def __init__(self):
        super().__init__("careers360")

    # ------------------------------------------------------------------ #
    #  COLLEGES
    # ------------------------------------------------------------------ #
    async def scrape_colleges(self) -> list[dict]:
        # Disabled: Careers360 listing returns all-India colleges (2000+),
        # not just Uttarakhand. Collegedunia covers Uttarakhand colleges well.
        logger.info("[careers360] College scraping disabled — using Collegedunia only for colleges")
        return []

    def _is_uttarakhand_college(self, college: dict, url: str) -> bool:
        """Strictly verify this college is in Uttarakhand."""
        # Check if city matches an Uttarakhand city
        city = (college.get("city") or "").lower()
        if city and any(m in city for m in self._UK_MARKERS):
            return True
        # Check college name for Uttarakhand city names
        name = (college.get("college_name") or "").lower()
        if any(m in name for m in self._UK_MARKERS):
            return True
        # Check URL
        if any(m in url.lower() for m in self._UK_MARKERS):
            return True
        return False

    # Uttarakhand city/keyword markers to filter college URLs
    _UK_MARKERS = [
        "uttarakhand", "dehradun", "roorkee", "haridwar", "haldwani",
        "nainital", "rishikesh", "kashipur", "srinagar-garhwal", "pauri",
        "almora", "rudrapur", "pithoragarh", "kotdwar", "mussoorie",
        "pantnagar", "chamoli", "champawat", "tehri", "uttarkashi",
        "bageshwar", "ramnagar", "selaqui", "bhimtal",
    ]

    async def _collect_college_urls(self, page) -> list[str]:
        urls = []
        page_num = 1
        while page_num <= 10:
            listing_url = (
                CAREERS360_LISTING if page_num == 1
                else f"{CAREERS360_LISTING}?page={page_num}"
            )
            if not await self.safe_goto(page, listing_url):
                break

            # Scroll to trigger lazy loading
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(1000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            links = set()
            for a in soup.select("a[href*='/colleges/']"):
                href = a.get("href", "")
                if (href and "/colleges/" in href
                        and "uttarakhand-colleges" not in href
                        and "/colleges/exams" not in href):
                    if not href.startswith("http"):
                        href = f"https://www.careers360.com{href}"
                    clean_url = href.split("?")[0].split("#")[0]
                    # Only keep URLs containing Uttarakhand city/state markers
                    if any(m in clean_url.lower() for m in self._UK_MARKERS):
                        links.add(clean_url)

            if not links:
                break

            new_links = [l for l in links if l not in urls]
            if not new_links:
                break
            urls.extend(new_links)
            page_num += 1

        return urls

    async def _extract_college(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".college-name", ".clg-title", "[class*='collegeName']"]:
            tag = soup.select_one(sel)
            if tag:
                name = tag.get_text(strip=True)
                break
        if not name:
            return {}

        city = self._extract_city(soup)
        inst_type, ownership = self._extract_type(soup)
        courses, fees = self._extract_courses_fees(soup)
        placement_rate, avg_pkg, high_pkg = self._extract_placements(soup)
        ranking = self._extract_ranking(soup)
        exams = self._extract_exams_from_text(soup)
        facilities = self._extract_facilities(soup)

        return {
            "college_name": name,
            "city": city,
            "institution_type": inst_type,
            "institution_subtype": "",
            "ownership": ownership,
            "courses_offered": courses,
            "fees": fees,
            "eligibility": {},
            "admission_process": "",
            "entrance_exam": exams,
            "placement_rate": placement_rate,
            "average_package": avg_pkg,
            "highest_package": high_pkg,
            "ranking": ranking,
            "facilities": facilities,
            "website": "",
            "phone_number": "",
            "email": "",
            "admission_open_date": "",
            "application_deadline": "",
        }

    def _extract_city(self, soup: BeautifulSoup) -> str:
        uttarakhand_cities = [
            "Dehradun", "Roorkee", "Haridwar", "Haldwani", "Nainital",
            "Rishikesh", "Kashipur", "Srinagar", "Pauri", "Almora",
            "Rudrapur", "Bhimtal", "Pithoragarh", "Kotdwar",
        ]
        text = soup.get_text()
        for city in uttarakhand_cities:
            if city.lower() in text.lower():
                return city
        return ""

    def _extract_type(self, soup: BeautifulSoup) -> tuple[str, str]:
        text = soup.get_text().lower()
        inst_type = "Private"
        ownership = "Private"
        if "government" in text or "govt" in text:
            inst_type = "Government"
            ownership = "Central Government" if "central" in text else "State Government"
        elif "deemed" in text:
            inst_type = "Deemed"
        return inst_type, ownership

    def _extract_courses_fees(self, soup: BeautifulSoup) -> tuple[list[str], dict]:
        courses = set()
        fees = {}
        text = soup.get_text()
        known_courses = [
            "B.Tech", "M.Tech", "MBA", "BBA", "BCA", "MCA", "MBBS", "BDS",
            "B.Sc", "M.Sc", "B.Com", "M.Com", "B.Arch", "LLB", "B.Pharm",
            "M.Pharm", "Ph.D", "BA", "MA", "B.Ed", "BPT", "B.Sc Nursing",
        ]
        for course in known_courses:
            if course.lower() in text.lower():
                courses.add(course)

        # Parse fee from tables
        for row in soup.select("tr, [class*='fee']"):
            row_text = row.get_text()
            for course in known_courses:
                if course.lower() in row_text.lower():
                    fee = self._parse_fee(row_text)
                    if fee:
                        fees[course] = fee
                        courses.add(course)

        return list(courses), fees

    def _parse_fee(self, text: str) -> int | None:
        match = re.search(
            r'(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|crore|cr|K)?',
            text, re.IGNORECASE
        )
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
                unit = (match.group(2) or "").lower()
                if unit in ("lakh", "lac", "l"):
                    amount *= 100_000
                elif unit in ("crore", "cr"):
                    amount *= 10_000_000
                elif unit == "k":
                    amount *= 1_000
                if 1000 <= amount <= 5_000_000:
                    return int(amount)
            except ValueError:
                pass
        return None

    def _extract_placements(self, soup: BeautifulSoup) -> tuple:
        text = soup.get_text()
        placement_rate = None
        avg_pkg = None
        high_pkg = None

        rate_match = re.search(r'(\d{2,3})\s*%\s*(?:placement|placed)', text, re.IGNORECASE)
        if not rate_match:
            rate_match = re.search(r'placement.*?(\d{2,3})\s*%', text, re.IGNORECASE)
        if rate_match:
            rate = int(rate_match.group(1))
            if 0 <= rate <= 100:
                placement_rate = rate

        avg_match = re.search(
            r'(?:average|avg|median).*?(?:package|salary|ctc).*?(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)?',
            text, re.IGNORECASE
        )
        if avg_match:
            avg_pkg = self._parse_salary(avg_match.group(1), avg_match.group(2))

        high_match = re.search(
            r'(?:highest|max|top).*?(?:package|salary|ctc).*?(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)?',
            text, re.IGNORECASE
        )
        if high_match:
            high_pkg = self._parse_salary(high_match.group(1), high_match.group(2))

        return placement_rate, avg_pkg, high_pkg

    def _parse_salary(self, amount_str: str, unit: str | None) -> int | None:
        try:
            amount = float(amount_str.replace(",", ""))
            unit = (unit or "").lower()
            if unit in ("lakh", "lac", "l", "lpa"):
                amount *= 100_000
            elif unit in ("crore", "cr"):
                amount *= 10_000_000
            if 10_000 <= amount <= 100_000_000:
                return int(amount)
        except ValueError:
            pass
        return None

    def _extract_ranking(self, soup: BeautifulSoup) -> str:
        text = soup.get_text()
        nirf_match = re.search(r'NIRF.*?(?:rank|#)\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if nirf_match:
            return f"NIRF #{nirf_match.group(1)}"
        return ""

    def _extract_exams_from_text(self, soup: BeautifulSoup) -> list[str]:
        exams = set()
        text = soup.get_text()
        known = [
            "JEE Main", "JEE Advanced", "NEET UG", "NEET PG", "CAT", "MAT",
            "GATE", "CUET", "CLAT", "XAT", "CMAT", "UPCET",
        ]
        for exam in known:
            if exam.lower() in text.lower():
                exams.add(exam)
        return list(exams)

    def _extract_facilities(self, soup: BeautifulSoup) -> list[str]:
        facilities = set()
        text = soup.get_text().lower()
        known = [
            "Hostel", "Library", "Labs", "Sports", "WiFi", "Medical",
            "Cafeteria", "Gym", "Auditorium", "Playground",
        ]
        for f in known:
            if f.lower() in text:
                facilities.add(f)
        return list(facilities)

    # ------------------------------------------------------------------ #
    #  CAREERS
    # ------------------------------------------------------------------ #
    async def scrape_careers(self) -> list[dict]:
        page = await self.new_page()
        careers = []
        try:
            if not await self.safe_goto(page, CAREERS360_CAREERS):
                return []

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            career_urls = []
            for a in soup.select("a[href*='/careers/']"):
                href = a.get("href", "")
                if href and "/careers/" in href:
                    if not href.startswith("http"):
                        href = f"https://www.careers360.com{href}"
                    career_urls.append(href.split("?")[0])

            career_urls = list(set(career_urls))[:30]

            for url in career_urls:
                try:
                    career = await self._extract_career(page, url)
                    if career and career.get("career_name"):
                        careers.append(career)
                except Exception as e:
                    logger.warning(f"[careers360] Failed career {url}: {e}")
        finally:
            await page.context.close()
        return careers

    async def _extract_career(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".career-title"]:
            tag = soup.select_one(sel)
            if tag:
                name = tag.get_text(strip=True)
                break
        if not name:
            return {}

        text = soup.get_text()
        stream = ""
        if "pcm" in text.lower():
            stream = "PCM"
        elif "pcb" in text.lower():
            stream = "PCB"
        elif "commerce" in text.lower():
            stream = "Commerce"

        exams = self._extract_exams_from_text(soup)

        return {
            "career_name": name,
            "also_known_as": [],
            "category": "",
            "description": "",
            "required_stream_class_11_12": stream,
            "path_after_10th": "",
            "path_after_12th": "",
            "path_after_graduation": "",
            "key_entrance_exams": exams,
            "primary_degree": "",
            "alternative_degrees": [],
            "duration_years": None,
            "avg_salary_entry_inr": None,
            "avg_salary_mid_inr": None,
            "avg_salary_senior_inr": None,
            "top_companies": [],
            "uttarakhand_colleges_offering": [],
            "skills_required": [],
            "job_roles": [],
        }

    # ------------------------------------------------------------------ #
    #  EXAMS
    # ------------------------------------------------------------------ #
    async def scrape_exams(self) -> list[dict]:
        page = await self.new_page()
        exams = []
        try:
            if not await self.safe_goto(page, CAREERS360_EXAMS):
                return []

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            exam_urls = []
            for a in soup.select("a[href*='/exams/']"):
                href = a.get("href", "")
                if href and "/exams/" in href:
                    if not href.startswith("http"):
                        href = f"https://www.careers360.com{href}"
                    exam_urls.append(href.split("?")[0])

            exam_urls = list(set(exam_urls))[:20]

            for url in exam_urls:
                try:
                    exam = await self._extract_exam(page, url)
                    if exam and exam.get("exam_name"):
                        exams.append(exam)
                except Exception as e:
                    logger.warning(f"[careers360] Failed exam {url}: {e}")
        finally:
            await page.context.close()
        return exams

    async def _extract_exam(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".exam-title"]:
            tag = soup.select_one(sel)
            if tag:
                name = tag.get_text(strip=True)
                break
        if not name:
            return {}

        text = soup.get_text()
        conducting = ""
        body_match = re.search(r'(?:conducted|conducting)\s+(?:by|body)[:\s]*([^\.]+)', text, re.IGNORECASE)
        if body_match:
            conducting = body_match.group(1).strip()[:100]

        mode = ""
        if "online" in text.lower() and "offline" in text.lower():
            mode = "Online & Offline"
        elif "online" in text.lower() or "cbt" in text.lower():
            mode = "Online (CBT)"
        elif "offline" in text.lower():
            mode = "Offline"

        return {
            "exam_name": name,
            "full_name": "",
            "conducting_body": conducting,
            "for_courses": [],
            "for_colleges": "",
            "frequency": "",
            "eligibility": "",
            "exam_mode": mode,
            "total_marks": None,
            "duration_hours": None,
            "subjects": [],
            "official_website": "",
            "uttarakhand_colleges_using": [],
            "preparation_tips": "",
        }

    # ------------------------------------------------------------------ #
    #  SCHOLARSHIPS (Careers360 has limited scholarship pages)
    # ------------------------------------------------------------------ #
    async def scrape_scholarships(self) -> list[dict]:
        # Careers360 doesn't have a dedicated scholarships section
        return []


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    scraper = Careers360Scraper()
    result = asyncio.run(scraper.run())
    print(f"Colleges: {len(result['colleges'])}")
    for c in result["colleges"][:3]:
        print(f"  - {c['college_name']} ({c['city']})")
