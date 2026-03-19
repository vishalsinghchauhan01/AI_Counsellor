import os

# ---------- Target URLs (Uttarakhand listings) ----------
COLLEGEDUNIA_LISTING = "https://collegedunia.com/uttarakhand-colleges"
CAREERS360_LISTING = "https://www.careers360.com/colleges/uttarakhand-colleges-fctp"

COLLEGEDUNIA_CAREERS = "https://collegedunia.com/careers"
CAREERS360_CAREERS = "https://www.careers360.com/courses-certifications/all-courses"

COLLEGEDUNIA_EXAMS = "https://collegedunia.com/exams"
CAREERS360_EXAMS = "https://www.careers360.com/exams"

COLLEGEDUNIA_SCHOLARSHIPS = "https://collegedunia.com/scholarships"

# ---------- Throttling ----------
MIN_DELAY = float(os.getenv("SCRAPER_MIN_DELAY", "3"))
MAX_DELAY = float(os.getenv("SCRAPER_MAX_DELAY", "10"))
MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
PAGE_TIMEOUT_MS = 60_000

# ---------- User-Agent rotation pool ----------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# ---------- Trust hierarchy (higher index = more trusted for conflicts) ----------
SOURCE_TRUST_ORDER = ["careers360", "collegedunia"]

# ---------- Scheduler ----------
SCRAPE_CRON_DAY = os.getenv("SCRAPE_CRON_DAY", "sun")
SCRAPE_CRON_HOUR = int(os.getenv("SCRAPE_CRON_HOUR", "2"))
SCRAPE_CRON_MINUTE = int(os.getenv("SCRAPE_CRON_MINUTE", "0"))
SCRAPER_ENABLED = os.getenv("SCRAPER_ENABLED", "true").lower() == "true"
