"""
Scraper for Collegedunia.com — Uttarakhand colleges, careers, exams, scholarships.
Collegedunia uses JS-heavy rendering with lazy-loaded tabs and Load More pagination.
"""
import logging
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from scraper.base_scraper import BaseScraper
from scraper.config import (
    COLLEGEDUNIA_LISTING, COLLEGEDUNIA_EXTRA_LISTINGS,
    COLLEGEDUNIA_CAREERS,
    COLLEGEDUNIA_EXAMS, COLLEGEDUNIA_SCHOLARSHIPS,
)

logger = logging.getLogger("scraper.collegedunia")


class CollegeduniaScraper(BaseScraper):
    def __init__(self):
        super().__init__("collegedunia")

    # ------------------------------------------------------------------ #
    #  COLLEGES
    # ------------------------------------------------------------------ #
    async def scrape_colleges(self) -> list[dict]:
        page = await self.new_page()
        colleges = []
        try:
            profile_urls = await self._collect_college_urls(page)
            logger.info(f"[collegedunia] Found {len(profile_urls)} college URLs")

            pbar = tqdm(profile_urls, desc="Scraping colleges", unit="college", ncols=80)
            for url in pbar:
                try:
                    college = await self._extract_college(page, url)
                    if college and college.get("college_name"):
                        colleges.append(college)
                        pbar.set_postfix(found=len(colleges), errors=self.stats["errors"])
                except Exception as e:
                    logger.warning(f"[collegedunia] Failed {url}: {e}")
                    self.stats["errors"] += 1
                    pbar.set_postfix(found=len(colleges), errors=self.stats["errors"])
        finally:
            await page.context.close()
        return colleges

    # Sub-page suffixes to strip from URLs so we only visit the base college page
    _URL_SUB_PAGES = [
        "/fees", "/courses", "/reviews", "/ranking", "/placement",
        "/cutoff", "/admission", "/scholarship", "/gallery", "/hostel",
        "/contact", "/faculty", "/infrastructure", "/results",
        "/courses-fees", "/news", "/articles",
    ]

    def _normalize_college_url(self, url: str) -> str:
        """Strip sub-page paths and course-specific suffixes from college URLs.
        e.g. '.../college/123-xyz-dehradun/btech-fees' → '.../college/123-xyz-dehradun'
        """
        url = url.split("?")[0].split("#")[0]
        # Strip known sub-page suffixes
        for suffix in self._URL_SUB_PAGES:
            if url.endswith(suffix):
                url = url[: -len(suffix)]
                break
        # Strip course-specific sub-paths like /btech-computer-science, /mba-fees, etc.
        # College base URLs look like /college/12345-college-name-city
        # Sub-pages add extra path segments after the base
        parts = url.rstrip("/").split("/")
        # Find the /college/XXXXX part and keep only up to that
        for i, part in enumerate(parts):
            if part == "college" and i + 1 < len(parts):
                # The base college slug is the next segment (e.g. "12345-college-name-city")
                base_slug = parts[i + 1]
                # If there are more segments after the slug, it's a sub-page
                url = "/".join(parts[: i + 2])
                break
        return url

    async def _collect_college_urls(self, page) -> list[str]:
        urls_set = set()

        # All listing URLs: main listing + category-specific pages
        all_listings = [COLLEGEDUNIA_LISTING] + COLLEGEDUNIA_EXTRA_LISTINGS

        for listing_base in all_listings:
            page_num = 1
            while page_num <= 8:  # up to 8 pages per listing
                listing_url = listing_base if page_num == 1 else f"{listing_base}{'&' if '?' in listing_base else '?'}page={page_num}"
                if not await self.safe_goto(page, listing_url):
                    break

                # Try clicking "Load More" if present
                for _ in range(2):
                    try:
                        load_more = await page.query_selector("button:has-text('Load More'), a:has-text('Load More')")
                        if load_more:
                            await load_more.click()
                            await page.wait_for_timeout(1500)
                        else:
                            break
                    except Exception:
                        break

                html = await page.content()
                soup = BeautifulSoup(html, "lxml")

                links = set()
                for a in soup.select("a[href*='/college/']"):
                    href = a.get("href", "")
                    if href and "/college/" in href:
                        if not href.startswith("http"):
                            href = f"https://collegedunia.com{href}"
                        base_url = self._normalize_college_url(href)
                        links.add(base_url)

                if not links:
                    break

                before = len(urls_set)
                urls_set.update(links)
                # No new URLs found on this page — stop paginating this listing
                if len(urls_set) == before:
                    break
                page_num += 1

            logger.info(f"[collegedunia] After {listing_base.split('/')[-1] or 'main'}: {len(urls_set)} unique URLs")

        logger.info(f"[collegedunia] Total deduplicated: {len(urls_set)} unique college URLs")
        return list(urls_set)

    async def _extract_college(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".clg-name", ".college-header h1", "[class*='collegeName']"]:
            tag = soup.select_one(sel)
            if tag:
                name = tag.get_text(strip=True)
                break
        if not name:
            return {}
        # Clean page-title suffixes
        name = self._clean_college_name(name)

        city = self._extract_city(soup, url=url, name=name)
        inst_type, ownership, subtype = self._extract_type_full(soup)
        courses, fees = self._extract_courses_fees(soup)
        # Try extracting total fees from the main page
        total_fees = self._extract_total_fees(soup)
        if total_fees:
            for course, amount in total_fees.items():
                fees[course] = amount

        placement_rate, avg_pkg, high_pkg = self._extract_placements(soup)
        ranking = self._extract_ranking(soup)

        # If no valid ranking found, try the /ranking sub-page (quick check, no retry)
        if ranking == "Not Available":
            ranking_url = url.rstrip("/") + "/ranking"
            if await self.safe_goto_once(page, ranking_url):
                ranking_html = await page.content()
                ranking_soup = BeautifulSoup(ranking_html, "lxml")
                ranking = self._extract_ranking(ranking_soup)
        exams = self._extract_exams(soup)
        facilities = self._extract_facilities(soup)
        website = self._extract_website(soup)
        phone, email = self._extract_contact(soup)
        # If no phone/email found, try visiting the /contact sub-page
        if not phone or not email:
            contact_url = url.rstrip("/") + "/contact"
            if await self.safe_goto_once(page, contact_url):
                contact_html = await page.content()
                contact_soup = BeautifulSoup(contact_html, "lxml")
                cp, ce = self._extract_contact(contact_soup)
                if not phone and cp:
                    phone = cp
                if not email and ce:
                    email = ce
                # Also try to get website from contact page
                if not website:
                    website = self._extract_website(contact_soup)
        eligibility = self._extract_eligibility(soup, courses)
        admission_process = self._extract_admission_process(soup)
        admission_open, deadline = self._extract_admission_dates(soup)

        return {
            "college_name": name,
            "city": city or "Not Available",
            "institution_type": inst_type or "Not Available",
            "institution_subtype": subtype or "Not Available",
            "ownership": ownership or "Not Available",
            "courses_offered": courses if courses else [],
            "fees": fees if fees else {},
            "eligibility": eligibility or "Not Available",
            "admission_process": admission_process or "Not Available",
            "entrance_exam": exams if exams else [],
            "placement_rate": placement_rate,
            "average_package": avg_pkg,
            "highest_package": high_pkg,
            "ranking": ranking or "Not Available",
            "facilities": facilities if facilities else [],
            "website": website or "Not Available",
            "phone_number": phone or "Not Available",
            "email": email or "Not Available",
            "admission_open_date": admission_open or "Not Available",
            "application_deadline": deadline or "Not Available",
        }

    @staticmethod
    def _clean_college_name(name: str) -> str:
        """Strip course names, ranking suffixes, review tags from page titles."""
        # Strip course-name + everything after (e.g., "B.Tech Computer Science...: Fees 2026")
        name = re.sub(
            r'\s+(?:B\.?\s*Tech|M\.?\s*Tech|MBA|BBA|BCA|MCA|MBBS|BDS|B\.?\s*Sc|M\.?\s*Sc|'
            r'B\.?\s*Com|M\.?\s*Com|B\.?\s*Arch|LLB|LLM|B\.?\s*Pharm|M\.?\s*Pharm|B\.?\s*Ed|'
            r'BPT|MPT|Ph\.?\s*D|Diploma|PGDM|BA\b|MA\b|B\.?\s*Des|M\.?\s*Des|'
            r'B\.?\s*Voc|M\.?\s*Voc|B\.?\s*Sc\s+Nursing|Advanced\s+Diploma)\b.*$',
            '', name, flags=re.IGNORECASE
        )
        # Strip "Placement 2026: Highest Package, Average Package, Top Recruiters"
        name = re.sub(r'\s+Placement\s+\d{4}.*$', '', name, flags=re.IGNORECASE)
        # Strip "Ranking 2024/2025/2026" anywhere
        name = re.sub(r'\s+Ranking\s+\d{4}.*$', '', name, flags=re.IGNORECASE)
        # Strip "Reviews on Placements, Faculty and Facilities"
        name = re.sub(r'\s+Reviews?\s+on\s+.*$', '', name, flags=re.IGNORECASE)
        # Strip "Courses & Fees 2026" pattern
        name = re.sub(r'\s+Courses?\s*&?\s*Fees.*$', '', name, flags=re.IGNORECASE)
        # Strip "Admission 2026, Fees, Courses, Cutoff, Ranking, Placement"
        name = re.sub(r'\s+Admission\s+\d{4}.*$', '', name, flags=re.IGNORECASE)
        # Strip ": Fees 2026, Course Duration, Dates, Eligibility"
        name = re.sub(
            r'\s*[:\|]\s*(?:Admission|Fees|Courses|Reviews|Cutoff|Ranking|Placement|'
            r'Eligibility|Scholarships|Course|Fee|Rank|Result|Overview|Hostel|'
            r'Highest\s+Package|Average\s+Package|Top\s+Recruiters).*$',
            '', name, flags=re.IGNORECASE
        )
        # Strip "Online Dehradun Courses & Fees 2026" — catches "XYZ University Online City..."
        name = re.sub(r'\s+Online\s+\w+\s+Courses.*$', '', name, flags=re.IGNORECASE)
        # Strip trailing year like "2025" or "2026"
        name = re.sub(r'\s+20\d{2}\s*$', '', name)
        # Strip trailing special chars
        name = name.strip(" -–—|,:")
        return name

    # Uttarakhand cities/towns for matching (comprehensive list)
    _UK_CITIES = [
        "Dehradun", "Roorkee", "Haridwar", "Haldwani", "Nainital",
        "Rishikesh", "Kashipur", "Srinagar", "Pauri", "Almora",
        "Rudrapur", "Bhimtal", "Pithoragarh", "Kotdwar", "Mussoorie",
        "Pantnagar", "Chamoli", "Champawat", "Tehri", "Uttarkashi",
        "Bageshwar", "Ramnagar", "Selaqui", "Jolly Grant", "Doiwala",
        "Lalkuan", "Sitarganj", "Jaspur", "Kichha", "Bazpur",
        "Rudraprayag", "Gopeshwar", "Vikasnagar", "Herbertpur",
        "Clement Town", "Prem Nagar", "Tanakpur", "Dwarahat",
        "Ranikhet", "Lansdowne", "Chamba", "New Tehri",
        "Udham Singh Nagar", "Pauri Garhwal", "Tehri Garhwal",
        "Chamoli Garhwal", "Augustmuni", "Srinagar Garhwal",
    ]

    # Sub-locality → nearest main city mapping
    # ONLY for small localities that are PART of a bigger city
    # Do NOT map cities that are their own place (Pantnagar, Kashipur, Roorkee etc.)
    _DISTRICT_TO_CITY = {
        "clement town": "Dehradun",
        "prem nagar": "Dehradun",
        "jolly grant": "Dehradun",
        "doiwala": "Dehradun",
        "selaqui": "Dehradun",
        "vikasnagar": "Dehradun",
        "herbertpur": "Dehradun",
        "new tehri": "Tehri",
        "augustmuni": "Rudraprayag",
        "gopeshwar": "Chamoli",
        "dwarahat": "Almora",
        "ranikhet": "Almora",
        "lansdowne": "Pauri",
        "lalkuan": "Haldwani",
        "srinagar garhwal": "Srinagar",
        "pauri garhwal": "Pauri",
        "tehri garhwal": "Tehri",
        "chamoli garhwal": "Chamoli",
        "udham singh nagar": "Rudrapur",
    }

    def _match_city(self, text: str) -> str:
        """Match text against UK cities list. Returns the canonical city name."""
        text_lower = text.lower()
        # Check sub-locality mappings first (longer names match first)
        for district, city in self._DISTRICT_TO_CITY.items():
            if district in text_lower:
                return city
        # Then check direct city names — return as-is (they ARE the city)
        for city in self._UK_CITIES:
            if city.lower() in text_lower:
                return city
        return ""

    def _extract_city(self, soup: BeautifulSoup, url: str = "", name: str = "") -> str:
        # PRIORITY 1: College name (most reliable — "XYZ College Dehradun")
        if name:
            city = self._match_city(name)
            if city:
                return city

        # PRIORITY 2: URL slug (e.g., /college/xyz-dehradun-1234)
        if url:
            # Only check the college slug part of URL, not the whole domain
            slug = url.split("/college/")[-1] if "/college/" in url else url
            city = self._match_city(slug.replace("-", " "))
            if city:
                return city

        # PRIORITY 3: Specific location elements on the page
        for sel in [".location", ".clg-location", "[class*='location']",
                    "[class*='address']", "span[class*='city']",
                    "[class*='headerLocation']"]:
            tag = soup.select_one(sel)
            if tag:
                city = self._match_city(tag.get_text(strip=True))
                if city:
                    return city

        # PRIORITY 4: Meta tags
        for meta in soup.select("meta[property*='locality'], meta[name*='locality'], meta[name*='city']"):
            city = self._match_city(meta.get("content", ""))
            if city:
                return city

        # PRIORITY 5: Breadcrumb only (NOT full page text — too noisy)
        breadcrumb = soup.select_one(".breadcrumb, [class*='breadcrumb']")
        if breadcrumb:
            city = self._match_city(breadcrumb.get_text(strip=True))
            if city:
                return city

        # DO NOT fall back to full page text — it picks up random city mentions
        # from ads, related colleges, navigation links etc.
        return ""

    def _extract_type_full(self, soup: BeautifulSoup) -> tuple[str, str, str]:
        """Extract institution type, ownership, and subtype."""
        # Search in key info sections first, then fall back to full text
        search_text = ""
        for sel in [".college-info", "[class*='keyInfo']", "[class*='overview']",
                    "table", ".info-table", "[class*='detail']"]:
            for tag in soup.select(sel):
                search_text += " " + tag.get_text()
        if not search_text:
            search_text = soup.get_text()[:5000]

        text = search_text.lower()
        inst_type = "Private"
        ownership = "Private"
        subtype = ""

        if "government" in text or "govt" in text:
            inst_type = "Government"
            if "central government" in text or "central govt" in text:
                ownership = "Central Government"
            elif "state government" in text or "state govt" in text:
                ownership = "State Government"
            else:
                ownership = "State Government"
        elif "deemed" in text:
            inst_type = "Deemed"
            ownership = "Deemed University"
        elif "autonomous" in text:
            inst_type = "Autonomous"

        # Subtype detection
        if "institute of national importance" in text or "ini" in text:
            subtype = "Institute of National Importance"
        elif "iit" in text:
            subtype = "IIT"
        elif "nit" in text:
            subtype = "NIT"
        elif "iiit" in text:
            subtype = "IIIT"
        elif "aiims" in text:
            subtype = "AIIMS"
        elif "central university" in text:
            subtype = "Central University"
        elif "state university" in text:
            subtype = "State University"
        elif "deemed university" in text or "deemed-to-be" in text:
            subtype = "Deemed University"
        elif "affiliated" in text:
            subtype = "Affiliated College"

        return inst_type, ownership, subtype

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

        # Try parsing fee tables
        for row in soup.select("tr, .fee-row, [class*='feeRow']"):
            row_text = row.get_text()
            for course in known_courses:
                if course.lower() in row_text.lower():
                    fee_val = self._parse_fee_from_text(row_text)
                    if fee_val:
                        fees[course] = fee_val
                        courses.add(course)

        return list(courses), fees

    def _extract_total_fees(self, soup: BeautifulSoup) -> dict:
        """Extract total course fees from the /courses-fees page.
        Collegedunia shows tables with 'Total Fees' or 'Course Fee' columns.
        We look for the highest fee per course (total > annual).
        """
        total_fees = {}
        known_courses = [
            "B.Tech", "M.Tech", "MBA", "BBA", "BCA", "MCA", "MBBS", "BDS",
            "B.Sc", "M.Sc", "B.Com", "M.Com", "B.Arch", "LLB", "B.Pharm",
            "M.Pharm", "Ph.D", "BA", "MA", "B.Ed", "BPT", "B.Sc Nursing",
        ]

        # Strategy 1: Look for rows with "Total Fees" or "Total Course Fee" text
        for row in soup.select("tr, .fee-row, [class*='feeRow'], [class*='course-fee'], [class*='courseFee']"):
            row_text = row.get_text(" ", strip=True)
            # Check if this row mentions "total" fees
            has_total = bool(re.search(r'total\s*(?:fee|course\s*fee)', row_text, re.IGNORECASE))

            for course in known_courses:
                if course.lower() in row_text.lower():
                    # Find ALL fee values in this row
                    fee_matches = re.findall(
                        r'(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|crore|cr|K)?',
                        row_text, re.IGNORECASE
                    )
                    if not fee_matches:
                        # Also try plain number patterns like "4,50,000"
                        fee_matches = re.findall(
                            r'([\d,]+(?:\.\d+)?)\s*(lakh|lac|L|crore|cr|K)?',
                            row_text, re.IGNORECASE
                        )

                    best_fee = 0
                    for amount_str, unit in fee_matches:
                        try:
                            amount = float(amount_str.replace(",", ""))
                            unit_lower = (unit or "").lower()
                            if unit_lower in ("lakh", "lac", "l"):
                                amount *= 100_000
                            elif unit_lower in ("crore", "cr"):
                                amount *= 10_000_000
                            elif unit_lower == "k":
                                amount *= 1_000
                            # Valid fee range: 1K to 1 crore
                            if 1000 <= amount <= 10_000_000:
                                # If row mentions "total", take the largest value
                                # Otherwise take the largest as it's likely total
                                if amount > best_fee:
                                    best_fee = int(amount)
                        except ValueError:
                            continue

                    if best_fee > 0:
                        # Only update if this is larger than existing (total > annual)
                        if course not in total_fees or best_fee > total_fees[course]:
                            total_fees[course] = best_fee

        # Strategy 2: Look for specific "Total Fees" labeled elements
        for el in soup.select("[class*='totalFee'], [class*='total-fee'], .total_fees"):
            text = el.get_text(" ", strip=True)
            for course in known_courses:
                if course.lower() in text.lower():
                    fee_val = self._parse_fee_from_text(text)
                    if fee_val and (course not in total_fees or fee_val > total_fees[course]):
                        total_fees[course] = fee_val

        return total_fees

    def _parse_fee_from_text(self, text: str) -> int | None:
        match = re.search(
            r'(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr|K)?',
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

        # Placement rate patterns
        rate_patterns = [
            r'(\d{2,3})\s*%\s*(?:placement|placed)',
            r'placement\s*(?:rate|percentage|ratio)?\s*[:\-]?\s*(\d{2,3})\s*%',
            r'(\d{2,3})\s*%\s*(?:of\s+)?students?\s+(?:got\s+)?placed',
        ]
        for pattern in rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate = int(match.group(1))
                if 10 <= rate <= 100:
                    placement_rate = rate
                    break

        # Average package patterns - look for LPA format too (e.g., "4.5 LPA")
        avg_patterns = [
            r'(?:average|avg|median)\s*(?:package|salary|ctc|CTC)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)?',
            r'(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)\s*(?:average|avg)',
            r'(?:average|avg)\s*[:\-]?\s*([\d,\.]+)\s*(LPA|lakh|lac|L)',
            r'([\d,\.]+)\s*(LPA|lpa)\s*(?:average|avg)',
        ]
        for pattern in avg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                avg_pkg = self._parse_salary(match.group(1), match.group(2))
                if avg_pkg:
                    break

        # Highest package patterns
        high_patterns = [
            r'(?:highest|max|top|maximum)\s*(?:package|salary|ctc|CTC)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)?',
            r'(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA|crore|cr)\s*(?:highest|max|top)',
            r'(?:highest|max)\s*[:\-]?\s*([\d,\.]+)\s*(LPA|lakh|lac|L|crore|cr)',
        ]
        for pattern in high_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                high_pkg = self._parse_salary(match.group(1), match.group(2))
                if high_pkg:
                    break

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

        # NIRF patterns — must capture actual rank (1-500), NOT a year (2019-2030)
        nirf_patterns = [
            # "NIRF Ranking #45" or "NIRF Rank: 45"
            r'NIRF\s*(?:ranking|rank|rated?)?\s*[:\-#]?\s*#?\s*(\d+)',
            # "Ranked #45 by NIRF" or "Ranked 45 in NIRF"
            r'(?:ranked?|#)\s*(\d+)\s*(?:by|in)\s*NIRF',
            # "NIRF 2024: #45" or "NIRF 2025 Rank 45"
            r'NIRF\s*\d{4}\s*[:\-]?\s*(?:rank(?:ing)?\s*)?#?\s*(\d+)',
            # "NIRF 2024 Ranking: 45th"
            r'NIRF\s*\d{4}\s*ranking\s*[:\-]?\s*(\d+)',
        ]
        for pattern in nirf_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rank_num = int(match.group(1))
                # Filter out years (2000-2030) — real NIRF ranks are 1-500
                if 1 <= rank_num <= 500 and not (2000 <= rank_num <= 2030):
                    return f"NIRF #{rank_num}"

        # NAAC grade
        naac_match = re.search(r'NAAC\s*(?:grade|accredit(?:ed|ation))?\s*[:\-]?\s*([A-Za-z+]+(?:\+\+?)?)', text, re.IGNORECASE)
        if naac_match:
            grade = naac_match.group(1).strip().upper()
            if grade in ("A++", "A+", "A", "B++", "B+", "B", "C"):
                return f"NAAC {grade}"

        # NBA accredited
        if re.search(r'\bNBA\s+accredit', text, re.IGNORECASE):
            return "NBA Accredited"

        return "Not Available"

    def _extract_exams(self, soup: BeautifulSoup) -> list[str]:
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

    def _extract_website(self, soup: BeautifulSoup) -> str:
        # Try explicit "official website" links
        for a in soup.select("a[href*='http']"):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if "official" in text or "website" in text or "visit site" in text:
                if "collegedunia" not in href:
                    return href

        # Try links near "website" labels in tables/info sections
        for row in soup.select("tr, .info-row, [class*='detail']"):
            row_text = row.get_text(strip=True).lower()
            if "website" in row_text or "official" in row_text:
                link = row.select_one("a[href*='http']")
                if link:
                    href = link.get("href", "")
                    if "collegedunia" not in href:
                        return href

        # Try any .edu.in or .ac.in domain link on the page
        for a in soup.select("a[href*='.edu.in'], a[href*='.ac.in'], a[href*='.org.in']"):
            href = a.get("href", "")
            if href and "collegedunia" not in href:
                return href
        return ""

    def _extract_contact(self, soup: BeautifulSoup) -> tuple[str, str]:
        """Extract phone number and email from the page."""
        text = soup.get_text()
        phone = ""
        email = ""

        # Phone: look for Indian phone patterns
        phone_patterns = [
            r'(?:Phone|Tel|Contact|Call)[:\s]*(\+91[\s\-]?\d{5}[\s\-]?\d{5})',
            r'(?:Phone|Tel|Contact|Call)[:\s]*(0\d{2,4}[\s\-]?\d{6,8})',
            r'(?:Phone|Tel|Contact|Call)[:\s]*(\d{10})',
            r'(\+91[\s\-]?\d{5}[\s\-]?\d{5})',
            r'(0\d{3,4}[\s\-]\d{6,7})',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(1).strip()
                break

        # Email: look for email addresses
        email_match = re.search(
            r'(?:Email|Mail|Contact)[:\s]*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
            text, re.IGNORECASE
        )
        if not email_match:
            # Fallback: find any .edu.in or .ac.in email
            email_match = re.search(
                r'([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.(?:edu\.in|ac\.in|org\.in|com))',
                text, re.IGNORECASE
            )
        if email_match:
            email = email_match.group(1).strip()

        # Also check mailto: links
        if not email:
            for a in soup.select("a[href^='mailto:']"):
                href = a.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if email:
                    break

        # Also check tel: links
        if not phone:
            for a in soup.select("a[href^='tel:']"):
                href = a.get("href", "")
                phone = href.replace("tel:", "").strip()
                if phone:
                    break

        return phone, email

    def _extract_eligibility(self, soup: BeautifulSoup, courses: list[str]) -> dict:
        """Extract eligibility criteria per course."""
        eligibility = {}
        text = soup.get_text()

        # Try table rows that mention courses + eligibility
        for row in soup.select("tr"):
            row_text = row.get_text()
            for course in courses:
                if course.lower() in row_text.lower():
                    # Look for exam names or percentage requirements
                    elig_parts = []
                    for exam in ["JEE Main", "JEE Advanced", "NEET", "CAT", "MAT",
                                 "GATE", "CUET", "CLAT", "XAT", "CMAT", "UPCET"]:
                        if exam.lower() in row_text.lower():
                            elig_parts.append(exam)
                    pct_match = re.search(r'(\d{2,3})\s*%', row_text)
                    if pct_match:
                        elig_parts.append(f"Min {pct_match.group(1)}% in 12th")
                    if elig_parts:
                        eligibility[course] = " / ".join(elig_parts)

        # If no table-based extraction, try text patterns
        if not eligibility:
            for course in courses[:5]:  # limit to avoid noise
                pattern = rf'{re.escape(course)}.*?(?:eligib|criteria|requirement|qualify).*?([^\.]+\.)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    elig_text = match.group(1).strip()[:150]
                    if len(elig_text) > 10:
                        eligibility[course] = elig_text

        return eligibility

    def _extract_admission_process(self, soup: BeautifulSoup) -> str:
        """Extract admission process description."""
        text = soup.get_text()

        # Look for admission-related sections
        for sel in ["[class*='admission']", "#admission", "[id*='admission']"]:
            tag = soup.select_one(sel)
            if tag:
                content = tag.get_text(strip=True)
                if len(content) > 20:
                    return content[:300]

        # Regex for admission process text
        patterns = [
            r'(?:admission\s+process|how\s+to\s+apply|admission\s+procedure)[:\s]*([^\.]+(?:\.[^\.]+)?)',
            r'(?:admission|admit)\s+(?:is\s+)?(?:based\s+on|through|via)\s+([^\.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()[:300]
                if len(result) > 15:
                    return result
        return ""

    def _extract_admission_dates(self, soup: BeautifulSoup) -> tuple[str, str]:
        """Extract admission open date and application deadline."""
        text = soup.get_text()
        admission_open = ""
        deadline = ""

        months = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"

        # Admission open date
        open_patterns = [
            rf'(?:admission|application)\s+(?:open|start|begin)s?\s*[:\-]?\s*({months})\s*(\d{{4}})?',
            rf'(?:open|start)s?\s+(?:from|in)\s*[:\-]?\s*({months})\s*(\d{{4}})?',
        ]
        for pattern in open_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                admission_open = match.group(1).strip()
                if match.group(2):
                    admission_open += f" {match.group(2)}"
                break

        # Deadline
        deadline_patterns = [
            rf'(?:deadline|last\s+date|closing\s+date|application\s+deadline)\s*[:\-]?\s*(\d{{1,2}}\s*(?:{months})\s*\d{{4}})',
            rf'(?:deadline|last\s+date)\s*[:\-]?\s*({months})\s*(\d{{4}})?',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline = match.group(0).split(":")[-1].strip()[:50]
                break

        return admission_open, deadline

    # ------------------------------------------------------------------ #
    #  CAREERS
    # ------------------------------------------------------------------ #
    async def scrape_careers(self) -> list[dict]:
        page = await self.new_page()
        careers = []
        try:
            if not await self.safe_goto(page, COLLEGEDUNIA_CAREERS):
                return []

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            career_urls = []
            for a in soup.select("a[href*='/careers/']"):
                href = a.get("href", "")
                if href and "/careers/" in href:
                    if not href.startswith("http"):
                        href = f"https://collegedunia.com{href}"
                    career_urls.append(href.split("?")[0])

            career_urls = list(set(career_urls))[:30]

            for url in career_urls:
                try:
                    career = await self._extract_career(page, url)
                    if career and career.get("career_name"):
                        careers.append(career)
                except Exception as e:
                    logger.warning(f"[collegedunia] Failed career {url}: {e}")
        finally:
            await page.context.close()
        return careers

    async def _extract_career(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".career-name"]:
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

        exams = self._extract_exams(soup)

        # Try extracting salary info
        avg_entry = None
        sal_match = re.search(
            r'(?:entry|starting|fresher).*?(?:salary|package).*?(?:INR|Rs\.?|₹)\s*([\d,\.]+)\s*(lakh|lac|L|LPA)?',
            text, re.IGNORECASE
        )
        if sal_match:
            avg_entry = self._parse_salary(sal_match.group(1), sal_match.group(2))

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
            "avg_salary_entry_inr": avg_entry,
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
            if not await self.safe_goto(page, COLLEGEDUNIA_EXAMS):
                return []

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            exam_urls = []
            for a in soup.select("a[href*='/exams/']"):
                href = a.get("href", "")
                if href and "/exams/" in href:
                    if not href.startswith("http"):
                        href = f"https://collegedunia.com{href}"
                    exam_urls.append(href.split("?")[0])

            exam_urls = list(set(exam_urls))[:20]

            for url in exam_urls:
                try:
                    exam = await self._extract_exam(page, url)
                    if exam and exam.get("exam_name"):
                        exams.append(exam)
                except Exception as e:
                    logger.warning(f"[collegedunia] Failed exam {url}: {e}")
        finally:
            await page.context.close()
        return exams

    async def _extract_exam(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".exam-name"]:
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

        # Try to find mode
        mode = ""
        if "online" in text.lower() and "offline" in text.lower():
            mode = "Online & Offline"
        elif "online" in text.lower() or "cbt" in text.lower():
            mode = "Online (CBT)"
        elif "offline" in text.lower() or "pen and paper" in text.lower():
            mode = "Offline (Pen & Paper)"

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
    #  SCHOLARSHIPS
    # ------------------------------------------------------------------ #
    async def scrape_scholarships(self) -> list[dict]:
        page = await self.new_page()
        scholarships = []
        try:
            if not await self.safe_goto(page, COLLEGEDUNIA_SCHOLARSHIPS):
                return []

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            schol_urls = []
            for a in soup.select("a[href*='/scholarship']"):
                href = a.get("href", "")
                if href and "/scholarship" in href:
                    if not href.startswith("http"):
                        href = f"https://collegedunia.com{href}"
                    schol_urls.append(href.split("?")[0])

            schol_urls = list(set(schol_urls))[:15]

            for url in schol_urls:
                try:
                    s = await self._extract_scholarship(page, url)
                    if s and s.get("name"):
                        scholarships.append(s)
                except Exception as e:
                    logger.warning(f"[collegedunia] Failed scholarship {url}: {e}")
        finally:
            await page.context.close()
        return scholarships

    async def _extract_scholarship(self, page, url: str) -> dict:
        if not await self.safe_goto(page, url):
            return {}

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        name = ""
        for sel in ["h1", ".scholarship-name"]:
            tag = soup.select_one(sel)
            if tag:
                name = tag.get_text(strip=True)
                break
        if not name:
            return {}

        text = soup.get_text()
        amount = ""
        amount_match = re.search(
            r'(?:amount|award|value)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,\.]+\s*(?:lakh|lac|L|K)?(?:\s*(?:to|-)\s*[\d,\.]+\s*(?:lakh|lac|L|K)?)?)',
            text, re.IGNORECASE
        )
        if amount_match:
            amount = f"INR {amount_match.group(1).strip()}"

        return {
            "name": name,
            "type": "",
            "category": "",
            "amount": amount,
            "eligibility": "",
            "apply_at": url,
            "deadline": "",
        }


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    scraper = CollegeduniaScraper()
    result = asyncio.run(scraper.run())
    print(f"Colleges: {len(result['colleges'])}")
    for c in result["colleges"][:3]:
        print(f"  - {c['college_name']} ({c['city']})")
