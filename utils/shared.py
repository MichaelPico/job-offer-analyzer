from dataclasses import dataclass

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
        posted_time (str): The time the job was posted. Defaults to an empty string.
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
        posted_time: str = "", 
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