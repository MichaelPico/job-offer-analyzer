import os
import time
import urllib
import random
from bs4 import BeautifulSoup
from typing import List, Optional, Dict

from utils.remote_llm.openai_job_analyser import OpenAIjobAnalyser
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

    Attributes:
        language_detector (LanguageDetector): Instance for detecting job listing languages
        positions (List[str]): List of job titles to search for
        job_location (str): Geographic region for job search
        job_type (str): Work arrangement type code from LinkedIn
        easy_apply (bool): Whether to filter for LinkedIn Easy Apply jobs
        max_jobs (int): Total maximum number of jobs to extract
        max_jobs_per_position (int): Maximum jobs to extract per job title
        experience_level (str): LinkedIn code for required experience level
        publish_timespan (str): LinkedIn code for job posting age filter
        less_than_ten_applicants (bool): Filter for jobs with few applicants
        used_tokens (int): Counter for API token usage
        job_listings (List[LinkedinJobListing]): Collected job listings
        should_analyze (bool): Whether to perform AI analysis on listings
        desired_language (str): Target language for job listings
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
        Initialize the LinkedIn job extractor with search parameters.

        Args:
            language_detector: Utility to detect languages in job listings
            positions: Comma-separated list of job titles to search
            location: Geographic region for job search
            type: Work arrangement type (Remote/On-site/Hybrid)
            easy_apply: Filter for LinkedIn's Easy Apply jobs
            max_jobs: Total maximum number of jobs to extract
            max_jobs_per_position: Maximum jobs to extract per job title
            experience_level: Required work experience level
            publish_timespan: Maximum job posting age to consider
            less_than_ten_applicants: Filter for low-competition jobs

        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        self.language_detector = language_detector
        
        # Handle environment variables with proper type conversion and validation
        self.positions = (os.getenv('JOB_SEARCH_POSITIONS') or positions).split(',')
        self.job_location = os.getenv('JOB_SEARCH_LOCATION') or location
        self.job_type = job_type_dict.get(os.getenv('JOB_TYPE') or type)
        if not self.job_type:
            raise ValueError(f"Invalid job type. Must be one of: {list(job_type_dict.keys())}")
            
        # Convert string environment variables to proper types
        self.easy_apply = str(os.getenv('LINKEDIN_EASY_APPLY')).lower() == 'true' if os.getenv('LINKEDIN_EASY_APPLY') else easy_apply
        self.max_jobs = int(os.getenv('LINKEDIN_MAX_JOBS')) if os.getenv('LINKEDIN_MAX_JOBS') else max_jobs
        self.max_jobs_per_position = int(os.getenv('LINKEDIN_MAX_JOBS_PER_POSITION')) if os.getenv('LINKEDIN_MAX_JOBS_PER_POSITION') else max_jobs_per_position
        
        self.experience_level = experience_level_dict.get(os.getenv('LINKEDIN_EXPERIENCE_LEVEL') or experience_level)
        if not self.experience_level:
            raise ValueError(f"Invalid experience level. Must be one of: {list(experience_level_dict.keys())}")
            
        self.publish_timespan = publish_timespan_dict.get(os.getenv('LINKEDIN_PUBLISH_TIMESPAN') or publish_timespan)
        if not self.publish_timespan:
            raise ValueError(f"Invalid publish timespan. Must be one of: {list(publish_timespan_dict.keys())}")
            
        self.less_than_ten_applicants = str(os.getenv('LINKEDIN_LESS_THAN_TEN_APPLICANTS')).lower() == 'true' if os.getenv('LINKEDIN_LESS_THAN_TEN_APPLICANTS') else less_than_ten_applicants
        
        self.used_tokens = 0
        self.job_listings: List[LinkedinJobListing] = []
        
        # AI analysis setup
        self.should_analyze = str(os.getenv("USE_AZURE_OPENAI", "false")).lower() == "true"
        self.desired_language = str(os.getenv("JOB_DESIRED_LANGUAGE", "")).lower()
        if self.should_analyze and not self.desired_language:
            raise ValueError("JOB_DESIRED_LANGUAGE must be set when USE_AZURE_OPENAI is enabled")
            
        if self.should_analyze:
            self.azure_openai_analyzer = OpenAIjobAnalyser()
        
    def build_job_list_url(self, start: int = 0, keywords: Optional[str] = None) -> str:
        """
        Construct a LinkedIn job search API URL with all configured filters.

        Args:
            start: Pagination offset for job listings
            keywords: Additional job search keywords

        Returns:
            Complete LinkedIn job search API URL with applied filters
        """
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        
        params = {
            "start": start,
            "location": self.job_location,
            "f_E": self.experience_level,
            "f_JT": self.job_type,
            "f_WT": 2  # Remote work type
        }
        
        if self.easy_apply:
            params["f_AL"] = "true"
        
        if keywords:
            params["keywords"] = keywords
        
        if self.less_than_ten_applicants:
            params["f_JIYN"] = "true"
        
        if self.publish_timespan:
            params["f_TPR"] = self.publish_timespan
            
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def build_job_information_url(self, job_id: str) -> str:
        """
        Generate URL for retrieving detailed job information.

        Args:
            job_id: Unique identifier for the job listing

        Returns:
            URL for fetching job details
        """
        return f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    
    def populate_job_details(self, job: LinkedinJobListing, job_description: str, job_details_soup: BeautifulSoup) -> None:
        """
        Extract and populate detailed job information from the job posting page.

        Args:
            job: Job listing object to populate
            job_description: Full text of the job description
            job_details_soup: BeautifulSoup object of the job details page
        """
        criteria_mapping = {
            'Seniority level': 'seniority_level',
            'Employment type': 'employment_type',
            'Job function': 'job_function',
            'Industries': 'industries'
        }
        
        criteria_section = job_details_soup.find("ul", class_="description__job-criteria-list")
        if criteria_section:
            for item in criteria_section.find_all("li"):
                try:
                    label = item.find(class_="description__job-criteria-subheader").get_text().strip()
                    value = item.find(class_="description__job-criteria-text").get_text().strip()
                    
                    if label in criteria_mapping:
                        setattr(job, criteria_mapping[label], value)
                except (AttributeError, KeyError):
                    continue
                
        # Set description language
        job.description_lang = self.language_detector.detect(job_description)
        
        # Perform AI analysis if enabled and language matches
        if (self.should_analyze and 
            job.description_lang.lower() == self.desired_language):
            job_ai_analysis = self.azure_openai_analyzer.extract_job_data(job_description)
            
            job.required_studies = job_ai_analysis.required_studies
            job.technologies_required = job_ai_analysis.technologies_required
            job.experience_years_needed = job_ai_analysis.experience_years_needed
            job.salary_offered = job_ai_analysis.salary_offered
            self.used_tokens += job_ai_analysis.token_cost
    
    def parse_job_listings(self, jobs_url: str) -> None:
        """
        Extract job listings from LinkedIn's search results page.

        Args:
            jobs_url: LinkedIn jobs search results URL

        Raises:
            requests.RequestException: If there's an error fetching the page
            ValueError: If the page structure is invalid
        """
        job_list_page_content = fetch_page(jobs_url)
        if not job_list_page_content:
            raise ValueError("Failed to fetch job listings page")
            
        job_list_soup = BeautifulSoup(job_list_page_content, 'html.parser')
        job_nodes = job_list_soup.select('li > div.base-card')

        for node in job_nodes:
            try:
                # Extract job ID first to avoid duplicate processing
                job_url = _get_href(node, '[class*=_full-link]')
                if not job_url:
                    continue
                    
                job_id = job_url.split('-')[-1].split('?')[0]
                
                # Skip if job already processed
                if any(listing.job_id == job_id for listing in self.job_listings):
                    continue
                
                # Create new job listing
                job = LinkedinJobListing(
                    title=_get_text(node, '[class*=_title]'),
                    url=job_url,
                    company=_get_text(node, '[class*=_subtitle]'),
                    location=_get_text(node, '[class*=_location]'),
                    posted_time=_get_text(node, '[class*=listdate]'),
                    job_id=job_id
                )
                
                # Set title language and check if it matches desired language
                job.title_lang = self.language_detector.detect(job.title)
                if job.title_lang.lower() != self.desired_language:
                    continue
                
                # Fetch and process job details
                job_details_url = self.build_job_information_url(job.job_id)
                job_details_page_content = fetch_page(job_details_url)
                if not job_details_page_content:
                    continue
                    
                job_details_soup = BeautifulSoup(job_details_page_content, 'html.parser')
                job_description = _get_text(job_details_soup, '[class*=description] > section > div')
                
                self.populate_job_details(job, job_description, job_details_soup)
                
                # Only add job if description language matches
                if job.description_lang.lower() == self.desired_language:
                    self.job_listings.append(job)
                    
            except AttributeError as e:
                print(f"Error parsing job listing: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error processing job listing: {e}")
                continue

    def scrape_jobs(self) -> List[LinkedinJobListing]:
        """
        Execute the job scraping process across all specified positions.

        Returns:
            List of scraped job listings matching the search criteria

        Notes:
            - Implements rate limiting through random delays
            - Tracks progress and token usage
            - Stops when reaching job limits
        """
        total_jobs = 0
        total_valid_jobs = 0

        for position in self.positions:
            if total_jobs >= self.max_jobs:
                break
                
            current_position_valid_jobs = 0
            page = 0

            while (current_position_valid_jobs < self.max_jobs_per_position and 
                   total_jobs < self.max_jobs):
                
                # Rate limiting
                time.sleep(random.uniform(2, 5))
                
                try:
                    jobs_list_url = self.build_job_list_url(page * 10, position)  # LinkedIn uses 10 jobs per page
                    initial_listing_count = len(self.job_listings)
                    
                    self.parse_job_listings(jobs_list_url)
                    
                    # Check if any new listings were found
                    new_listings_count = len(self.job_listings) - initial_listing_count
                    if new_listings_count == 0:
                        break
                    
                    # Update counters
                    total_jobs += new_listings_count
                    current_position_valid_jobs += new_listings_count
                    total_valid_jobs = len(self.job_listings)
                    
                    # Progress reporting
                    print(f"Extracted LinkedIn page {page + 1}")
                    print(f"Valid jobs: {total_valid_jobs}")
                    print(f"Total jobs processed: {total_jobs}")
                    if self.should_analyze:
                        print(f"Tokens used: {self.used_tokens}")
                    
                    page += 1
                    
                except Exception as e:
                    print(f"Error processing page {page} for position '{position}': {e}")
                    time.sleep(random.uniform(5, 10))  # Longer delay on error
                    continue

        return self.job_listings