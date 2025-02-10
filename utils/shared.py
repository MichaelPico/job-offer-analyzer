from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import List, Optional

from bs4 import BeautifulSoup

###########
# Classes #
###########
@dataclass
class JobListing:
    """
    Represents a job listing from LinkedIn.

    Attributes:
        title (str): The job title.
        url (str): The URL of the job posting.
        company (str): The company offering the job.
        location (str): The job location.
        posted_time (Optional[datetime]): The time the job was posted.
        seniority_level (str): The seniority level required for the job.
        employment_type (str): The type of employment (e.g., full-time, part-time).
        job_function (str): The primary job function.
        industries (str): The industries relevant to the job.
        required_studies (str): The required educational qualifications.
        technologies_required (List[str]): A list of technologies required for the job.
        experience_years_needed (int): The number of years of experience needed.
        salary_offered (int): The salary offered for the job.
        job_id (str): A unique identifier for the job.
        title_lang (str): The detected language of the job title.
        description_lang (str): The detected language of the job description.
        date_analyzed (Optional[datetime]): The date when the job listing was analyzed.
        easy_apply (str): Whether the job listing supports easy application.
        source (str): The source of the job listing (e.g., LinkedIn).
    """
    title: str = ""
    url: str = ""
    company: str = ""
    location: str = ""
    posted_time: Optional[datetime] = None
    seniority_level: str = ""
    employment_type: str = ""
    job_function: str = ""
    industries: str = ""
    required_studies: str = ""
    technologies_required: List[str] = field(default_factory=list) # Use field for mutable defaults
    experience_years_needed: int = 0
    salary_offered: int = 0
    job_id: str = ""
    title_lang: str = ""
    description_lang: str = ""
    date_analyzed: Optional[datetime] = None
    easy_apply: str = 'No'
    source: str = "LinkedIn"
        
@dataclass
class JobAIanalysis:
    """
    Data class to store extracted job information and token usage
    
    Attributes:
        required_studies (str): Required education level for the position
        technologies_required (List[str]): List of required technologies
        experience_years_needed (int): Required years of experience
        token_cost (int): Total tokens used in the API call
    """
    required_studies: str
    technologies_required: List[str]
    experience_years_needed: int
    salary_offered: int
    token_cost: int


#################
# Dicttionaries #
#################

job_type_dict = {
    "On-site": 1,
    "Remote": 2,
    "Hybrid": 3
}

experience_level_dict = {
    "Intern": 1,
    "Assistant": 2,
    "Junior": 3,
    "Mid-Senior": 4,
    "Director": 5,
    "Executive": 6
}

publish_timespan_dict = {
    "None": "",
    "Day": "r86400",
    "Week": "r604800",
    "Month": "r2592000",
}



###########
# Methods #
###########

def html_to_text(html : str) -> str:
    """Clean and normalize HTML text content.
    This function takes HTML content, extracts the text, and normalizes whitespace.
    Args:
        html (str): Raw HTML content to be cleaned.
    Returns:
        str: Cleaned text with normalized whitespace.
    Example:
        >>> html = '<p>Hello  World!</p>\\n<div>More text</div>'
        >>> clean_text(html)
        'Hello World! More text'
    """
    # Parse HTML and extract text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    # Remove extra spaces, new lines, and redundant whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text