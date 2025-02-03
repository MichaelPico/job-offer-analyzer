from dataclasses import asdict
from datetime import datetime
import os
import json

import pandas as pd
from utils.shared import LinkedinJobListing
from utils.remote_llm.openai_job_analyser import OpenAIjobAnalyser
from utils.linkedin_excel_exporter import LinkedinExcelExporter
from utils.local_llm.language_detector import LanguageDetector
# from utils.local_llm.deep_seek_local_job_parser import DeepSeekLocalJobParser 
from utils.linkedin_scrapper import LinkedinExtractor

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def save_jobs_to_json(jobs, filename="output/jobs.json"):
    job_dicts = [job.__dict__ for job in jobs]
    os.makedirs("output", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(job_dicts, f, ensure_ascii=False, indent=4, cls=DateTimeEncoder)
    print("Jobs saved to output/jobs.json")
    
    

def load_jobs_from_json(filename="output/jobs.json") -> list:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            job_dicts = json.load(f)

        jobs = []
        for job_dict in job_dicts:
            # 1. Handle posted_time conversion (as you were doing):
            if job_dict.get('posted_time'):
                job_dict['posted_time'] = datetime.fromisoformat(job_dict['posted_time'].replace('Z', '+00:00')) # added timezone handling

            # 2. Create a *new* dictionary with only the correct keys:
            valid_job_data = {}
            for field_name in asdict(LinkedinJobListing()).keys(): # Get all field names
                if field_name in job_dict:  # Check if the key exists in the dict
                    valid_job_data[field_name] = job_dict[field_name]

            # 3. Create the instance using the filtered dictionary:
            try:
                job = LinkedinJobListing(**valid_job_data)
                jobs.append(job)
            except TypeError as e:
                print(f"Error creating job from dict: {job_dict}")  # Print the problematic dict
                print(f"Error Details: {e}")
                # Option: You could continue or break here depending on your needs.
                # For Example, to skip the invalid jobs:
                # continue

        print(f"Loaded {len(jobs)} jobs from {filename}")
        return jobs

    except FileNotFoundError:
        print(f"No jobs file found at {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in file {filename}: {e}")
        return []
    except ValueError as e:  # Catch potential datetime conversion errors
        print(f"Error converting date in job data: {e}")
        return []
    
def main():
    linkedin_jobs = load_jobs_from_json()
    
    # Language local llm
    linkedin_job_extractor = LinkedinExtractor(
        language_detector=LanguageDetector(),
        positions=os.getenv('JOB_SEARCH_POSITIONS', 'Software Developer'),
        location=os.getenv('JOB_SEARCH_LOCATION', 'France'),
        type=os.getenv('JOB_TYPE', 'Remote'),
        easy_apply=str(os.getenv('LINKEDIN_EASY_APPLY', 'true')).lower() == 'true',
        max_jobs=int(os.getenv('LINKEDIN_MAX_JOBS', '300')),
        max_jobs_per_position=int(os.getenv('LINKEDIN_MAX_JOBS_PER_POSITION', '100')),
        experience_level=os.getenv('LINKEDIN_EXPERIENCE_LEVEL', 'Mid-Senior'),
        publish_timespan=os.getenv('LINKEDIN_PUBLISH_TIMESPAN', 'Week'),
        less_than_ten_applicants=str(os.getenv('LINKEDIN_LESS_THAN_TEN_APPLICANTS', 'true')).lower() == 'true',
        use_ai_analysis=str(os.getenv('USE_AZURE_OPENAI', 'false')).lower() == 'true',
        desired_language=os.getenv('JOB_DESIRED_LANGUAGE', ''),
        azure_openai_analyzer=OpenAIjobAnalyser() if str(os.getenv('USE_AZURE_OPENAI', 'false')).lower() == 'true' else None,
        job_listings=linkedin_jobs
    )
    linkedin_excel_exporter = LinkedinExcelExporter("output/jobs.xlsx")
    
    # Linkedin class to scrap jobs
    linkedin_jobs = linkedin_job_extractor.scrape_jobs()
    
    # Save jobs to JSON
    save_jobs_to_json(linkedin_jobs)
    
    # Generate Excel
    linkedin_excel_exporter.export_jobs(linkedin_jobs)
    
    

if __name__ == '__main__':
    main()