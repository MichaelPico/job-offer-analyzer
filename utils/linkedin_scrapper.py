from datetime import datetime, timedelta
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
    and extracting job details programmatically.

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
        positions: str = "Software Developer",
        location: str = "France",
        type: str = "Remote",
        easy_apply: bool = True,
        max_jobs: int = 300,
        max_jobs_per_position: int = 100,
        experience_level: str = "Mid-Senior",
        publish_timespan: str = "Week",
        less_than_ten_applicants: bool = True,
        use_ai_analysis: bool = False,
        desired_language: str = "",
        azure_openai_analyzer: Optional[OpenAIjobAnalyser] = None,
        job_listings: Optional[List[LinkedinJobListing]] = None
    ) -> None:
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
            use_ai_analysis: Whether to use AI analysis for job listings
            desired_language: Target language for job listings when using AI analysis
            azure_openai_analyzer: Optional instance of OpenAIjobAnalyser for AI analysis
            job_listings: Optional list of pre-existing job listings

        Raises:
            ValueError: If parameters are invalid
        """
        self.language_detector = language_detector

        # Handle basic parameters
        self.positions = positions.split(',')
        self.job_location = location
        self.job_type = job_type_dict.get(type)
        if not self.job_type:
            raise ValueError(f"Invalid job type. Must be one of: {list(job_type_dict.keys())}")

        # Set boolean and integer parameters directly
        self.easy_apply = easy_apply
        self.max_jobs = max_jobs
        self.max_jobs_per_position = max_jobs_per_position

        # Validate and set experience level
        self.experience_level = experience_level_dict.get(experience_level)
        if not self.experience_level:
            raise ValueError(f"Invalid experience level. Must be one of: {list(experience_level_dict.keys())}")

        # Validate and set publish timespan
        self.publish_timespan = publish_timespan_dict.get(publish_timespan)
        if not self.publish_timespan:
            raise ValueError(f"Invalid publish timespan. Must be one of: {list(publish_timespan_dict.keys())}")

        self.less_than_ten_applicants = less_than_ten_applicants

        self.used_tokens = 0
        self.job_listings = job_listings if job_listings is not None else []

        # AI analysis setup
        self.should_analyze = use_ai_analysis
        self.desired_language = desired_language.lower()
        if self.should_analyze and not self.desired_language:
            raise ValueError("desired_language must be set when use_ai_analysis is enabled")

        self.azure_openai_analyzer = azure_openai_analyzer if azure_openai_analyzer is not None else OpenAIjobAnalyser()

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

    def parse_job_listings(self, jobs_url: str) -> bool:
        """
        Extract job listings from LinkedIn's search results page.

        Args:
            jobs_url: LinkedIn jobs search results URL

        Returns:
            bool: True if valid jobs were found, False if the page was empty or invalid

        Raises:
            requests.RequestException: If there's an error fetching the page
            ValueError: If the page structure is invalid
        """
        job_list_page_content = fetch_page(jobs_url)
        if not job_list_page_content:
            raise ValueError("Failed to fetch job listings page")

        job_list_soup = BeautifulSoup(job_list_page_content, 'html.parser')
        job_nodes = job_list_soup.select('li > div.base-card')

        # Check if the page is empty
        if not job_nodes:
            return False

        found_valid_jobs = False
        for node in job_nodes:
            try:
                # Extract job ID, title and company first to avoid duplicate processing
                job_url = _get_href(node, '[class*=_full-link]')
                if not job_url:
                    continue

                job_id = job_url.split('-')[-1].split('?')[0]
                job_title = _get_text(node, '[class*=_title]')
                job_company = _get_text(node, '[class*=_subtitle]')

                # Skip if job already processed
                if any(
                    listing.job_id == job_id or
                    (job_title.strip().lower() == listing.title.strip().lower() and
                    job_company.strip().lower() == listing.company.strip().lower())
                    for listing in self.job_listings
                ):
                    continue

                # Convert relative time to actual date
                posted_time_text = _get_text(node, '[class*=listdate]')
                posted_date = datetime.now()
                
                if 'hour' in posted_time_text:
                    hours = int(''.join(filter(str.isdigit, posted_time_text)))
                    posted_date -= timedelta(hours=hours)
                elif 'day' in posted_time_text:
                    days = int(''.join(filter(str.isdigit, posted_time_text)))
                    posted_date -= timedelta(days=days)

                # Create new job listing
                job = LinkedinJobListing(
                    title=job_title,
                    url=job_url,
                    company=job_company,
                    location=_get_text(node, '[class*=_location]'),
                    posted_time=posted_date,
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
                    found_valid_jobs = True

            except AttributeError as e:
                print(f"Error parsing job listing: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error processing job listing: {e}")
                continue

        return found_valid_jobs

    def scrape_jobs(self) -> List[LinkedinJobListing]:
        """
        Execute the job scraping process across all specified positions.

        Returns:
            List of scraped job listings matching the search criteria

        Notes:
            - Implements rate limiting through random delays
            - Tracks progress and token usage
            - Stops when reaching job limits
            - Handles empty pages and moves to next position
        """
        total_jobs = 0
        total_valid_jobs = 0
        consecutive_empty_pages = 0
        MAX_EMPTY_PAGES = 5  # Maximum number of consecutive empty pages before moving to next position

        for position in self.positions:
            if total_jobs >= self.max_jobs:
                print(f"Reached maximum total jobs limit ({self.max_jobs}). Stopping.")
                break

            print(f"\nStarting search for position: {position}")
            current_position_valid_jobs = 0
            page = 0
            consecutive_empty_pages = 0

            while (current_position_valid_jobs < self.max_jobs_per_position and
                   total_jobs < self.max_jobs):

                # Rate limiting
                time.sleep(random.uniform(2, 5))

                try:
                    jobs_list_url = self.build_job_list_url(page * 10, position)  # LinkedIn uses 25 jobs per page
                    initial_listing_count = len(self.job_listings)

                    # Check if page has valid jobs
                    found_jobs = self.parse_job_listings(jobs_list_url)

                    if not found_jobs:
                        consecutive_empty_pages += 1
                        print(f"No new jobs found on page {page + 1} for '{position}'")

                        if consecutive_empty_pages >= MAX_EMPTY_PAGES:
                            print(f"No more jobs found for '{position}' after {MAX_EMPTY_PAGES} empty pages. Moving to next position.")
                            break

                        page += 1
                        continue

                    # Reset empty pages counter if we found jobs
                    consecutive_empty_pages = 0

                    # Update counters
                    new_listings_count = len(self.job_listings) - initial_listing_count
                    total_jobs += new_listings_count
                    current_position_valid_jobs += new_listings_count
                    total_valid_jobs = len(self.job_listings)

                    # Progress reporting
                    print(f"Extracted LinkedIn page {page + 1} for '{position}'")
                    print(f"Found {new_listings_count} new valid jobs")
                    print(f"Position progress: {current_position_valid_jobs}/{self.max_jobs_per_position}")
                    print(f"Total progress: {total_valid_jobs}/{self.max_jobs}")
                    if self.should_analyze:
                        print(f"Tokens used: {self.used_tokens}")

                    if current_position_valid_jobs >= self.max_jobs_per_position:
                        print(f"Reached maximum jobs for position '{position}' ({self.max_jobs_per_position}). Moving to next position.")
                        break

                    page += 1

                except Exception as e:
                    print(f"Error processing page {page} for position '{position}': {e}")
                    time.sleep(random.uniform(5, 10))  # Longer delay on error

                    # Move to next position if we encounter persistent errors
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= MAX_EMPTY_PAGES:
                        print(f"Encountered persistent errors for '{position}'. Moving to next position.")
                        break
                    continue

        print(f"\nScraping completed. Total jobs found: {len(self.job_listings)}")
        return self.job_listings
