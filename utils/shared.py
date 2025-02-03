from dataclasses import dataclass
from datetime import datetime
from typing import List

###########
# Classes #
###########
@dataclass

class LinkedinJobListing:
    """
    Represents a job listing from LinkedIn.

    Attributes:
        title (str): The job title. Defaults to an empty string.
        url (str): The URL of the job posting. Defaults to an empty string.
        company (str): The company offering the job. Defaults to an empty string.
        location (str): The job location. Defaults to an empty string.
        posted_time (datetime): The time the job was posted. Defaults to None.
        seniority_level (str): The seniority level required for the job. Defaults to an empty string.
        employment_type (str): The type of employment (e.g., full-time, part-time). Defaults to an empty string.
        job_function (str): The primary job function. Defaults to an empty string.
        industries (str): The industries relevant to the job. Defaults to an empty string.
        required_studies (str): The required educational qualifications. Defaults to an empty string.
        technologies_required (List[str]): A list of technologies required for the job. Defaults to an empty list.
        experience_years_needed (int): The number of years of experience needed. Defaults to 0.
        job_id (str): A unique identifier for the job. Defaults to an empty string.
        title_lang (str): The detected language of the job title. Defaults to an empty string.
        description_lang (str): The detected language of the job description. Defaults to an empty string.
    """

    def __init__(
        self, 
        title: str = "", 
        url: str = "", 
        company: str = "", 
        location: str = "", 
        posted_time: datetime = None, 
        seniority_level: str = "", 
        employment_type: str = "", 
        job_function: str = "", 
        industries: str = "", 
        required_studies: str = "", 
        technologies_required: List[str] = [], 
        experience_years_needed: int = 0, 
        salary_offered: int = 0,
        job_id: str = "", 
        title_lang: str = "", 
        description_lang: str = ""
    ):
        self.title = title
        self.url = url
        self.company = company
        self.location = location
        self.posted_time = posted_time
        self.job_id = job_id
        self.title_lang = title_lang
        self.description_lang = description_lang
        
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