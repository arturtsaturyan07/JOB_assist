"""
Indeed Jobs Scraper using Selenium with Headless Mode
Scrapes real Indeed job listings with apply links
Free alternative to JSearch API
"""
import asyncio
import logging
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
from models import Job
from schedule_inference import infer_schedule_from_title

logger = logging.getLogger(__name__)

class IndeedScraper:
    """Scrape Indeed jobs with Selenium (Headless mode)"""
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://www.indeed.com/jobs"
        
    def _init_driver(self):
        """Initialize Chrome driver with headless options and anti-detection"""
        if self.driver:
            return
            
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => false});'
            })
            logger.info("✅ Indeed scraper initialized (headless)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Indeed scraper: {e}")
            raise
    
    def _close_driver(self):
        """Close Chrome driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    async def search_jobs(
        self,
        query: str,
        location: str = "",
        results_per_page: int = 100
    ) -> List[Job]:
        """Search Indeed jobs and extract with apply links"""
        try:
            self._init_driver()
            
            # Build search URL
            search_url = f"{self.base_url}?q={query.replace(' ', '+')}"
            if location:
                search_url += f"&l={location.replace(' ', '+')}"
            
            logger.info(f"🔍 Scraping Indeed (headless): {search_url}")
            
            await asyncio.sleep(random.uniform(2, 4))
            self.driver.get(search_url)
            
            wait = WebDriverWait(self.driver, 15)
            try:
                wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.job_seen_beacon, div.jobsearch-SerpJobCard")
                ))
                logger.info("✅ Indeed job listings loaded")
            except TimeoutException:
                logger.warning("⏱️ Timeout waiting for Indeed listings")
                return []
            
            await asyncio.sleep(random.uniform(1, 2))
            
            # Scroll to load more jobs
            for i in range(10):
                self.driver.execute_script("window.scrollBy(0, 800)")
                await asyncio.sleep(random.uniform(1, 2))
            
            jobs = []
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon, div.jobsearch-SerpJobCard, td.resultContent")
            
            logger.info(f"📋 Found {len(job_cards)} Indeed job cards")
            
            for idx, card in enumerate(job_cards[:results_per_page]):
                try:
                    job = self._parse_job_card(card)
                    if job and job.apply_link:
                        jobs.append(job)
                        logger.info(f"✅ Job {idx+1}: {job.title}")
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                except Exception as e:
                    logger.debug(f"⚠️ Error parsing Indeed job card {idx+1}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(jobs)} jobs from Indeed")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Indeed scraping error: {e}")
            return []
        finally:
            self._close_driver()
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single Indeed job card"""
        try:
            # Title
            title_elem = card.find_element(By.CSS_SELECTOR, "h2.jobTitle, a.jcs-JobTitle")
            title = title_elem.text.strip()
            
            # Company
            try:
                company_elem = card.find_element(By.CSS_SELECTOR, "span.companyName, span[data-testid='company-name']")
                company = company_elem.text.strip()
            except:
                company = ""
            
            # Location
            try:
                location_elem = card.find_element(By.CSS_SELECTOR, "div.companyLocation, div[data-testid='text-location']")
                location = location_elem.text.strip()
            except:
                location = ""
            
            # Apply link
            try:
                link_elem = card.find_element(By.CSS_SELECTOR, "a.jcs-JobTitle, h2.jobTitle a")
                job_key = link_elem.get_attribute("href")
                if not job_key.startswith("http"):
                    job_key = f"https://www.indeed.com{job_key}"
                apply_link = job_key
            except:
                apply_link = ""
            
            # Salary
            hourly_rate = 25.0
            try:
                salary_elem = card.find_element(By.CSS_SELECTOR, "div.salary-snippet, span.salary-snippet")
                salary_text = salary_elem.text
                hourly_rate = self._parse_salary(salary_text)
            except:
                pass
            
            if not title or not apply_link:
                return None
            
            # Infer schedule from job title
            schedule_blocks, hours_per_week = infer_schedule_from_title(title, location)
            
            job = Job(
                job_id=f"indeed_{apply_link.split('jk=')[-1][:12] if 'jk=' in apply_link else hash(apply_link)}",
                title=title,
                company=company,
                location=location or "Remote",
                hourly_rate=hourly_rate,
                required_skills=[],
                hours_per_week=hours_per_week,
                schedule_blocks=schedule_blocks,
                apply_link=apply_link,
                description="",
                job_source="indeed",
                posted_date=""
            )
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing Indeed job card: {e}")
            return None
    
    def _parse_salary(self, salary_text: str) -> float:
        """Parse salary text to hourly rate"""
        try:
            import re
            salary_text = salary_text.replace("$", "").replace(",", "").strip()
            
            if "/hr" in salary_text.lower() or "hour" in salary_text.lower():
                match = re.search(r"(\d+\.?\d*)", salary_text)
                if match:
                    return float(match.group(1))
            
            if "year" in salary_text.lower() or "annual" in salary_text.lower():
                match = re.search(r"(\d+\.?\d*)", salary_text)
                if match:
                    annual = float(match.group(1))
                    if annual < 1000:
                        annual *= 1000
                    return annual / 2000
            
            match = re.search(r"(\d+\.?\d*)", salary_text)
            if match:
                return float(match.group(1))
                
        except Exception as e:
            logger.debug(f"Error parsing salary: {e}")
        
        return 25.0
