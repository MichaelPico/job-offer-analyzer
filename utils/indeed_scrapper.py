from datetime import datetime
import json
import re
from typing import List, Optional
import urllib
from utils.remote_llm.openai_job_analyser import OpenAIjobAnalyser
from utils.chrome_scrapper import ChromeScrapper
from utils.local_llm.language_detector import LanguageDetector
from utils.base_scrapper import fetch_page, _get_href, _get_text
from .shared import JobListing, html_to_text, job_type_dict, experience_level_dict, publish_timespan_dict

class IndeedExtractor:
    """
    A comprehensive Indeed job scraping utility that extracts and processes job listings.

    This class provides functionality to scrape job listings from Indeed.com with configurable
    filters and processing options. It supports multi-language job detection, AI-powered 
    analysis, and customizable search parameters for targeted job searches.

    Attributes:
        language_detector (LanguageDetector): Detects language of job listings
        chrome_scrapper (ChromeScrapper): Handles web scraping operations
        base_url (str): Base URL for Indeed job searches (e.g., fr.indeed.com/jobs)
        positions (List[str]): List of job titles to search for
        job_location (str): Target geographic location for job search
        hybrid (bool): Flag to include hybrid work positions
        easy_apply (bool): Flag to filter for Indeed Easy Apply jobs
        max_jobs (int): Maximum total number of jobs to extract
        max_jobs_per_position (int): Maximum jobs to extract per job title
        publish_timespan (int): Maximum age of job postings in days
        used_tokens (int): Counter for API token usage in AI analysis
        job_listings (List[JobListing]): Storage for extracted job listings
        should_analyze (bool): Flag to enable AI analysis of listings
        desired_language (str): Target language for filtering job listings
        azure_openai_analyzer (OpenAIjobAnalyser): Handles AI-powered job analysis
        execution_started_datetime (datetime): Timestamp of extraction start
    """

    def __init__(
        self,
        language_detector: LanguageDetector,
        chrome_scrapper: ChromeScrapper,
        search_positions: str = "Software Developer",
        target_location: str = "France",
        include_hybrid: bool = False,
        only_easy_apply: bool = True,
        max_total_jobs: int = 300,
        max_jobs_per_position: int = 100,
        max_posting_age: int = 7,
        enable_ai_analysis: bool = False,
        target_language: str = "",
        azure_openai_analyzer: Optional[OpenAIjobAnalyser] = None,
        existing_job_listings: Optional[List[JobListing]] = None,
        indeed_base_url: str = "https://fr.indeed.com"
    ) -> None:
        """
        Initialize the IndeedExtractor with search parameters and configuration.

        Args:
            language_detector (LanguageDetector): Instance for job listing language detection
            chrome_scrapper (ChromeScrapper): Instance for Chrome-based web scraping
            search_positions (str, optional): Comma-separated job titles to search. Defaults to "Software Developer"
            target_location (str, optional): Geographic location for job search. Defaults to "France"
            include_hybrid (bool, optional): Include hybrid work positions. Defaults to False
            only_easy_apply (bool, optional): Filter for Easy Apply jobs only. Defaults to True
            max_total_jobs (int, optional): Maximum total jobs to extract. Defaults to 300
            max_jobs_per_position (int, optional): Max jobs per search position. Defaults to 100
            max_posting_age (int, optional): Maximum age of job postings in days. Defaults to 7
            enable_ai_analysis (bool, optional): Enable AI-powered analysis. Defaults to False
            target_language (str, optional): Desired language for job listings. Defaults to ""
            azure_openai_analyzer (OpenAIjobAnalyser, optional): Custom AI analyzer instance
            existing_job_listings (List[JobListing], optional): Pre-existing job listings
            indeed_base_url (str, optional): Indeed base URL. Defaults to "https://fr.indeed.com/jobs"

        Raises:
            ValueError: If AI analysis is enabled without specifying target language
        """
        self.language_detector = language_detector
        self.chrome_scrapper = chrome_scrapper
        self.base_url = indeed_base_url

        self.positions = search_positions.split(',') if search_positions else ["Software Developer"]
        self.job_location = target_location if target_location else "France"
        self.hybrid = include_hybrid
        self.easy_apply = only_easy_apply
        self.max_jobs = max_total_jobs if max_total_jobs else 300
        self.max_jobs_per_position = max_jobs_per_position if max_jobs_per_position else 100
        self.publish_timespan = max_posting_age if max_posting_age else 7
        
        self.used_tokens = 0
        self.job_listings = existing_job_listings if existing_job_listings is not None else []

        self.should_analyze = enable_ai_analysis
        self.desired_language = target_language.lower()
        if self.should_analyze and not self.desired_language:
            raise ValueError("Target language must be specified when AI analysis is enabled")
            
        self.azure_openai_analyzer = azure_openai_analyzer if azure_openai_analyzer is not None else OpenAIjobAnalyser()
        self.execution_started_datetime = datetime.now()

    def build_indeed_job_list_url(self, job_title: str, location: str, max_age_days: int = 3, remote_only: bool = True) -> str:
        """
        Constructs a search URL for Indeed job listings.

        Builds a properly encoded Indeed search URL with filters for job title,
        location, posting age, and remote work preferences.

        Args:
            job_title (str): Job title or keywords to search for
            location (str): Geographic location for job search
            max_age_days (int, optional): Maximum posting age in days. Defaults to 3
            remote_only (bool, optional): Filter for remote positions only. Defaults to True

        Returns:
            str: Fully qualified Indeed search URL with encoded parameters

        Example:
            >>> extractor.build_indeed_job_list_url("Python Developer", "Paris", 7, True)
            'https://fr.indeed.com/jobs?q=Python+Developer&l=Paris&fromage=7&sc=0kf...'
        """
        search_params = {
            "q": job_title,
            "l": location,
            "fromage": max_age_days, 
        }
        
        search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(search_params)}"
        
        if remote_only:
            search_url += "&sc=0kf%3Aattr%285QWDV%7CCF3CP%252COR%29attr%28DSQF7%29%3B"
        
        return search_url
    
    def build_indeed_job_details_url(self, job_id: str) -> str:
        """
        Creates a URL for accessing a specific job listing's details.

        Args:
            job_id (str): Indeed's unique job identifier (jk parameter)

        Returns:
            str: Complete URL for the job details page

        Example:
            >>> extractor.build_indeed_job_details_url("abc123")
            'https://fr.indeed.com/viewjob?jk=abc123'
        """
        return f'{self.base_url}/viewjob?jk={job_id}'
    
    def parse_indeed_search_page(self, search_url: str) -> dict:
        """
        Extracts job listings from an Indeed search results page.

        Fetches and parses the search results page to extract job listings and metadata
        from Indeed's client-side data structure ('window.mosaic.providerData').

        Args:
            search_url (str): Complete Indeed search URL to fetch results from

        Returns:
            dict: Dictionary containing:
                - results: List of job listings with detailed information
                - meta: Search result metadata and statistics

        Note:
            The results contain comprehensive job data including:
            - Job title and company name
            - Location and job types
            - Salary information when available
            - Easy Apply status
            - Requirements and qualifications
        """
        page_html = self.chrome_scrapper.fetch_page(search_url)
        data = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', page_html)
        data = json.loads(data[0])
        return {
            "results": data["metaData"]["mosaicProviderJobCardsModel"]["results"],
            "meta": data["metaData"]["mosaicProviderJobCardsModel"]["tierSummaries"],
        }
        
    def extract_job_listing_data(self, job_data: dict) -> JobListing:
        """
        Converts Indeed's job data into a standardized JobListing object.

        Processes raw Indeed job data to extract relevant information and create
        a structured JobListing object with normalized fields.

        Args:
            job_data (dict): Raw job listing data from Indeed's search results

        Returns:
            JobListing: Standardized job listing object with extracted information

        Example:
            >>> raw_data = {"displayTitle": "Senior Developer", "company": "TechCorp", ...}
            >>> job = extractor.extract_job_listing_data(raw_data)
            >>> print(f"{job.title} at {job.company}")
            'Senior Developer at TechCorp'
        """
        job_listing = JobListing()

        job_listing.title = job_data['displayTitle']
        job_listing.company = job_data['company']
        job_listing.location = job_data['formattedLocation']
        job_listing.posted_time = datetime.utcfromtimestamp(job_data['pubDate']/ 1000)
        job_listing.employment_type = ", ".join(job_data['jobTypes']) if 'jobTypes' in job_data else None
        job_listing.technologies_required = job_data["jobSeekerMatchSummaryModel"]["sortedMisMatchingEntityDisplayText"]
        job_listing.salary_offered = f"{job_data['extractedSalary']['min']} - {job_data['extractedSalary']['max']} {job_data['extractedSalary']['type']}" if 'extractedSalary' in job_data else None
        job_listing.job_id = job_data['jobkey']
        job_listing.easy_apply = job_data['indeedApplyEnabled']
        job_listing.source = "Indeed"

        job_listing.title_lang = self.language_detector.detect(job_listing.title)
        job_listing.url = self.build_indeed_job_details_url(job_listing.job_id)
        
        job_listing.date_analyzed = self.execution_started_datetime
        
        return job_listing
            
    def parse_indeed_details_page(self, details_url: str) -> dict:
        """
        Retrieves and parses detailed job information from a specific listing.

        Fetches and extracts comprehensive job details from Indeed's job listing page,
        including full description, requirements, and company information.

        Args:
            details_url (str): URL of the job details page to parse

        Returns:
            dict: Complete job information including:
                - Full job description
                - Detailed requirements
                - Company information
                - Benefits and perks
                - Application instructions

        Note:
            Some fields like seniority_level, job_function, industries,
            experience_years_needed, and required_studies may not be directly
            available in Indeed's data structure.
        """
        page_html = self.chrome_scrapper.fetch_page(details_url)
        data = re.findall(r"_initialData=(\{.+?\});", page_html)
        data = json.loads(data[0])
        return data["jobInfoWrapperModel"]["jobInfoModel"]
    
    def extract_job_details_data(self, job: JobListing, job_details_data: dict) -> None:
        clean_description = html_to_text(job_details_data["sanitizedJobDescription"])
        job.description_lang = self.language_detector.detect(clean_description)
        
        if(self.should_analyze and job.description_lang.lower() == self.desired_language):
            job_ai_analysis = self.azure_openai_analyzer.extract_job_data(clean_description, False, False)
            job.experience_years_needed = job_ai_analysis.experience_years_needed
            job.required_studies = job_ai_analysis.required_studies
            
        
    
        
    
    
    #missing job_listing.description_lang = "fr"  # Based on job details
    # job_listing.seniority_level = None  # No direct key available
    # job_listing.job_function = None  # No direct key available
    # job_listing.industries = None  # No direct key available
    # job_listing.experience_years_needed = None  # No direct key available
    # job_listing.required_studies = None  # No direct key available