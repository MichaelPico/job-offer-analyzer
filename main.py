import os
import json

import pandas as pd
from utils.linkedin_excel_exporter import LinkedinExcelExporter
from utils.local_llm.language_detector import LanguageDetector
# from utils.local_llm.deep_seek_local_job_parser import DeepSeekLocalJobParser 
from utils.linkedin_scrapper import LinkedinExtractor

def save_jobs_to_json(jobs, filename="output/jobs.json"):
    job_dicts = [job.__dict__ for job in jobs]
    os.makedirs("output", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(job_dicts, f, ensure_ascii=False, indent=4)
    print("Jobs saved to output/jobs.json")

def main():
    # Language local llm
    language_detector = LanguageDetector()
    linkedin_job_extractor = LinkedinExtractor(language_detector)
    linkedin_excel_exporter = LinkedinExcelExporter("output/jobs.xlsx")
    
    # Linkedin class to scrap jobs
    linkedin_jobs = linkedin_job_extractor.scrape_jobs()
    
    # Save jobs to JSON
    save_jobs_to_json(linkedin_jobs)
    
    # Generate Excel
    linkedin_excel_exporter.export_jobs(linkedin_jobs)
    
    

if __name__ == '__main__':
    main()

