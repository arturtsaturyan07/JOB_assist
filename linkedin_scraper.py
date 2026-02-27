"""
LinkedIn Jobs Scraper using Selenium with Headless Mode
Scrapes real LinkedIn job listings with apply links
Uses headless browser to avoid detection
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
from models import Job
from schedule_inference import infer_schedule_from_title

logger = logging.getLogger(__name__)

class LinkedInScraper:
    """Scrape LinkedIn jobs with Selenium (Headless mode)"""
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://www.linkedin.com/jobs/search"
        
    def _init_driver(self):
        """Initialize Chrome driver with headless options and anti-detection"""
        if self.driver:
            return
            
        chrome_options = Options()
        
        # Headless mode - no visible window
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Realistic user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
        
        # Window size for headless
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Inject JavaScript to hide automation indicators
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                '''
            })
            logger.info("✅ Chrome driver initialized (headless mode)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            raise
    
    def _close_driver(self):
        """Close Chrome driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("✅ Chrome driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    async def search_jobs(
        self,
        query: str,
        location: str = "",
        results_per_page: int = 100  # Increased default from 10 to 100
    ) -> List[Job]:
        """
        Search LinkedIn jobs and extract with apply links
        
        Args:
            query: Job title or keywords
            location: Location to search
            results_per_page: Number of results to return
            
        Returns:
            List of Job objects with apply links
        """
        try:
            self._init_driver()
            
            # Build search URL
            search_url = f"{self.base_url}?keywords={query}"
            if location:
                search_url += f"&location={location}"
            
            logger.info(f"🔍 Scraping LinkedIn (headless): {search_url}")
            
            # Add random delay to avoid detection
            await asyncio.sleep(random.uniform(2, 4))
            
            self.driver.get(search_url)
            
            # Wait for job listings to load with longer timeout
            wait = WebDriverWait(self.driver, 15)
            try:
                wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.base-card")
                ))
                logger.info("✅ Job listings loaded")
            except TimeoutException:
                logger.warning("⏱️ Timeout waiting for job listings - LinkedIn may be blocking")
                return []
            
            # Random delay between actions
            await asyncio.sleep(random.uniform(1, 2))
            
            # Scroll to load more jobs (increased scrolling for more results)
            for i in range(10):  # Increased from 3 to 10 scrolls
                self.driver.execute_script("window.scrollBy(0, 800)")  # Scroll more per iteration
                await asyncio.sleep(random.uniform(1, 2))
            
            # Extract job listings
            jobs = []
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.base-card")
            
            logger.info(f"📋 Found {len(job_cards)} job cards")
            
            for idx, card in enumerate(job_cards[:results_per_page]):
                try:
                    job = self._parse_job_card(card)
                    if job and job.apply_link:  # Only include if has apply link
                        jobs.append(job)
                        logger.info(f"✅ Job {idx+1}: {job.title} - {job.apply_link[:50]}...")
                    
                    # Random delay between parsing
                    await asyncio.sleep(random.uniform(0.5, 1))
                except Exception as e:
                    logger.debug(f"⚠️ Error parsing job card {idx+1}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(jobs)} jobs with apply links from LinkedIn")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ LinkedIn scraping error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            self._close_driver()
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single job card"""
        try:
            # Extract basic info
            title_elem = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title")
            title = title_elem.text.strip()
            
            company_elem = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle")
            company = company_elem.text.strip()
            
            location_elem = card.find_element(By.CSS_SELECTOR, "span.job-search-card__location")
            location = location_elem.text.strip()
            
            # Get apply link (LinkedIn job URL)
            link_elem = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
            apply_link = link_elem.get_attribute("href")
            
            # Extract salary if available
            hourly_rate = 0.0
            try:
                salary_elem = card.find_element(By.CSS_SELECTOR, "span.job-search-card__salary-info")
                salary_text = salary_elem.text
                # Parse salary (e.g., "$25/hr" or "$50,000 - $70,000")
                hourly_rate = self._parse_salary(salary_text)
            except NoSuchElementException:
                hourly_rate = 25.0  # Default
            
            # Infer schedule from job title
            schedule_blocks, hours_per_week = infer_schedule_from_title(title, location)
            
            # Create Job object
            job = Job(
                job_id=apply_link.split("/")[-2] if apply_link else "",
                title=title,
                company=company,
                location=location,
                hourly_rate=hourly_rate,
                required_skills=[],
                hours_per_week=hours_per_week,
                schedule_blocks=schedule_blocks,
                apply_link=apply_link,
                description="",
                job_source="linkedin_scraper",
                posted_date=""
            )
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job card: {e}")
            return None
    
    def _parse_salary(self, salary_text: str) -> float:
        """Parse salary text to hourly rate"""
        try:
            import re
            
            # Remove currency symbols and spaces
            salary_text = salary_text.replace("$", "").replace(",", "").strip()
            
            # Check if hourly
            if "/hr" in salary_text.lower():
                match = re.search(r"(\d+\.?\d*)", salary_text)
                if match:
                    return float(match.group(1))
            
            # Check if annual salary
            if "K" in salary_text or "k" in salary_text:
                match = re.search(r"(\d+\.?\d*)", salary_text)
                if match:
                    annual = float(match.group(1)) * 1000
                    return annual / 2000  # Convert to hourly (2000 hours/year)
            
            # Try to extract any number
            match = re.search(r"(\d+\.?\d*)", salary_text)
            if match:
                return float(match.group(1))
                
        except Exception as e:
            logger.debug(f"Error parsing salary: {e}")
        
        return 25.0  # Default


# Async wrapper for easy integration
async def scrape_linkedin_jobs(
    query: str,
    location: str = "",
    results_per_page: int = 10
) -> List[Job]:
    """Async wrapper for LinkedIn scraping"""
    scraper = LinkedInScraper()
    return await scraper.search_jobs(query, location, results_per_page)
