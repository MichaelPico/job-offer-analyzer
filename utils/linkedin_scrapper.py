import os
import time
import urllib
import random
from bs4 import BeautifulSoup
from typing import List, Optional

from utils.local_llm.language_detector import LanguageDetector
from utils.base_scrapper import fetch_page, _get_href, _get_text 
from .shared import LinkedinJobListing, job_type_dict, experience_level_dict, publish_timespan_dict

class LinkedinExtractor:
    """
    A comprehensive LinkedIn job scraping utility with flexible configuration options.
    
    This extractor allows for detailed job searches on LinkedIn with multiple configurable 
    parameters. It supports searching multiple job positions, applying various filters, 
    and extracting job details programmatically. The class uses environment variables 
    for configuration, with a fallback to constructor arguments.

    Key Features:
    - Multi-position job search
    - Configurable location, job type, and experience level filters
    - Language detection for job titles and descriptions
    - Pagination and job limit controls
    - Easy Apply and applicant count filtering
    """
    
    def __init__(
        self, 
        language_detector: LanguageDetector,
        positions: Optional[str] = "Software Developer",
        location: Optional[str] = "France", 
        type: Optional[str] = "Remote", 
        easy_apply: Optional[bool] = True, 
        max_jobs: Optional[int] = 300, 
        max_jobs_per_position: Optional[int] = 100, 
        experience_level: Optional[str] = "Mid-Senior",
        publish_timespan: Optional[str] = "Week",
        less_than_ten_applicants: Optional[bool] = True) -> None:
        """
        Initialize the LinkedIn job extractor with comprehensive search parameters.

        Configuration can be done through constructor arguments or environment variables.
        Environment variables take precedence over constructor arguments.

        Args:
            language_detector (LanguageDetector): Utility to detect languages in job listings
            positions (str, optional): Comma-separated list of job titles to search
            location (str, optional): Geographic region for job search
            type (str, optional): Work arrangement type (Remote/On-site/Hybrid)
            easy_apply (bool, optional): Filter for LinkedIn's Easy Apply jobs
            max_jobs (int, optional): Total maximum number of jobs to extract
            max_jobs_per_position (int, optional): Maximum jobs to extract per job title
            experience_level (str, optional): Minimum required work experience level
            publish_timespan (str, optional): Maximum job posting age to consider
            less_than_ten_applicants (bool, optional): Filter for low-competition jobs
        """
        self.language_detector = language_detector
        self.positions = (os.getenv('JOB_SEARCH_POSITIONS') or positions).split(',')
        self.job_location = os.getenv('JOB_SEARCH_LOCATION') or location
        self.job_type = job_type_dict[os.getenv('JOB_TYPE') or type]
        self.easy_apply = os.getenv('LINKEDIN_EASY_APPLY') or easy_apply
        self.max_jobs = int(os.getenv('LINKEDIN_MAX_JOBS')) or max_jobs
        self.max_jobs_per_position = int(os.getenv('LINKEDIN_MAX_JOBS_PER_POSITION')) or max_jobs_per_position
        self.experience_level = experience_level_dict[os.getenv('LINKEDIN_EXPERIENCE_LEVEL') or experience_level]
        self.publish_timespan = publish_timespan_dict[os.getenv('LINKEDIN_PUBLISH_TIMESPAN') or publish_timespan]
        self.less_than_ten_applicants = os.getenv('LINKEDIN_LESS_THAN_TEN_APPLICANTS') or less_than_ten_applicants
        
    def build_job_list_url(self, start: int = 0, keywords: Optional[str] = None) -> str:
        """
        Construct a precise LinkedIn job search API URL with multiple configurable filters.

        Dynamically builds a URL that includes all specified search parameters, 
        supporting pagination and keyword-based filtering.

        Args:
            start (int, optional): Pagination offset for job listings. Defaults to 0.
            keywords (str, optional): Additional job search keywords. Defaults to None.

        Returns:
            str: Fully constructed LinkedIn job search API URL with all applied filters
        """
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        
        params = []
        params.append(f"start={start}")
        
        if self.easy_apply:
            params.append("f_AL=true")
        
        if keywords:
            encoded_keywords = urllib.parse.quote(keywords)
            params.append(f"keywords={encoded_keywords}")
        
        params.append(f"location={urllib.parse.quote(self.job_location)}")
        
        params.append(f"f_E={self.experience_level}")
        params.append(f"f_JT={self.job_type}")
        params.append("f_WT=2")  # Remote work type
        
        if self.less_than_ten_applicants:
            params.append("f_JIYN=true")
        
        if self.publish_timespan:
            params.append(f"f_TPR={self.publish_timespan}")
        
        return f"{base_url}?{'&'.join(params)}"
    
    def buil_job_information_url(self, job_id: str) -> str:
        """
        Generate a direct URL to retrieve detailed information for a specific job.

        Args:
            job_id (str): Unique identifier for the job listing

        Returns:
            str: Complete URL for fetching comprehensive job details
        """
        return f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    
    def parse_job_listings(self, jobs_url: str) -> List[LinkedinJobListing]:
        """
        Extract and process job listings from LinkedIn's HTML response.

        Uses BeautifulSoup to parse HTML and extract detailed job information. 
        Performs additional processing like language detection and individual 
        job detail retrieval.

        Args:
            jobs_url (str): LinkedIn jobs search results URL

        Returns:
            List[LinkedinJobListing]: Comprehensive collection of parsed job listings

        Notes:
            - Handles potential parsing errors gracefully
            - Retrieves full job details for each listing
            - Detects languages for job titles and descriptions
        """
        job_list_page_content = fetch_page(jobs_url)
        job_list_soup = BeautifulSoup(job_list_page_content, 'html.parser')
        job_nodes = job_list_soup.select('li > div.base-card')
        jobs = []

        for node in job_nodes:
            try:
                job = LinkedinJobListing(
                    title=_get_text(node, '[class*=_title]'),
                    url=_get_href(node, '[class*=_full-link]'),
                    company=_get_text(node, '[class*=_subtitle]'),
                    location=_get_text(node, '[class*=_location]'),
                    posted_time=_get_text(node, '[class*=listdate]'),
                    job_id=_get_href(node, '[class*=_full-link]').split('-')[-1]
                )
                
                # Go to the job details to extract the description
                job_details_url = self.buil_job_information_url(job.job_id)
                job_details_page_content = fetch_page(job_details_url)
                job_details_soup = BeautifulSoup(job_details_page_content, 'html.parser')
                
                job_description = _get_text(job_details_soup, '[class*=description] > section > div')
                
                # Populate the language fields
                job.title_lang = self.language_detector.detect(job.title)
                job.description_lang = self.language_detector.detect(job_description)
                
                # TODO in the future I can use some sort of generation model 
                # like open ai or deep seek to extract more information from the description
                
                jobs.append(job)
            except AttributeError as e:
                print(f"Error parsing job listing: {e}")
                continue

        return jobs
    
    def scrape_jobs(self) -> List[LinkedinJobListing]:
        """
        Perform a comprehensive job scraping process across multiple positions.

        Orchestrates the entire job scraping workflow with built-in safeguards:
        - Respects maximum job and per-position limits
        - Implements random delays to avoid detection
        - Handles potential errors during scraping
        - Tracks and reports progress

        Returns:
            List[LinkedinJobListing]: Aggregated job listings from the search

        Notes:
            - Uses exponential backoff via random sleep intervals
            - Provides console logging for tracking extraction progress
            - Stops scraping when job limits are reached
        """
        job_listings = []
        total_jobs = 0

        for position in self.positions:
            if total_jobs >= self.max_jobs:
                break
                
            current_position_jobs = 0
            page = 0

            while (current_position_jobs < self.max_jobs_per_position and 
                total_jobs < self.max_jobs):
                
                time.sleep(random.uniform(2, 5)) # Sleep so linkedin doesn't detect too many requests
                jobs_list_url = self.build_job_list_url(page, position)
                
                try:
                    listings = self.parse_job_listings(jobs_list_url)
                    
                    # Break if no more listings found for this position
                    if not listings:
                        break
                    
                    for listing in listings:
                        # Check limits before adding each listing
                        if (current_position_jobs >= self.max_jobs_per_position or 
                            total_jobs >= self.max_jobs):
                            break
                            
                        job_listings.append(listing)
                        total_jobs += 1
                        current_position_jobs += 1
                    
                    print(f"A LinkedIn page was extracted, current jobs: {total_jobs}/{self.max_jobs}")
                    page += 1
                    
                except Exception as e:
                    print(f"Error fetching or parsing page {page} for position {position}: {e}")
                    break

        return job_listings