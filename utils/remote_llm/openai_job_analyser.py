import os
from dataclasses import dataclass
from typing import List
from openai import AzureOpenAI
from ..shared import JobAIanalysis

class OpenAIjobAnalyser:
    """
    A class to parse job descriptions using Azure OpenAI API
    """
   
    def __init__(self):
        """
        Initialize the OpenAIjobAnalyser with Azure OpenAI client using environment variables
       
        Required environment variables:
        - AZURE_OPENAI_ENDPOINT: The base URL for Azure OpenAI resource
        - AZURE_OPENAI_API_KEY: The API key for Azure OpenAI resource
        - AZURE_OPENAI_MODEL_NAME: The deployment name (e.g., "gpt-4")
        """
        self.api_version = '2024-08-01-preview'
       
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_version=self.api_version
        )
       
        self.model_name = os.getenv('AZURE_OPENAI_MODEL_NAME')
       
        
   
    def extract_job_data(self, job_description: str, extract_salary: bool = True, extract_techno: bool = True) -> JobAIanalysis:
        """
        Extract relevant information from a job description using Azure OpenAI API
       
        Args:
            job_description (str): The job description text to analyze
            extract_salary (bool): Whether to extract salary information (default: True)
            extract_techno (bool): Whether to extract technology requirements (default: True)
           
        Returns:
            JobAIanalysis: A JobAIanalysis object containing the extracted information and token usage
           
        Raises:
            ValueError: If required environment variables are missing
            Various OpenAI exceptions: For API-related errors
        """
        
        # Build the system prompt based on parameters
        base_prompt = """You are a job cataloger. Extract and return a JSON object
            with the following fields from the given software developer job description:
            - 'experience_years_needed': The number of years of experience required.
            - 'required_studies': The degree or education level required for the position (e.g., 'Bachelor's in Computer Science')."""
            
        techno_prompt = """
            - 'technologies_required': A list of programming languages, frameworks, or tools mentioned as required."""
            
        salary_prompt = """
            - 'salary_offered': The annual salary offered in integers (e.g., 80000). If a range is given, use the lower bound."""
            
        default_values = """
            If no explicit experience requirement is found, return 0.
            If no required studies are mentioned, return 'Not specified'."""
            
        if extract_techno:
            default_values += "\nIf no technologies are mentioned, return an empty list."
        if extract_salary:
            default_values += "\nIf no salary is mentioned, return 0."
            
        system_prompt = base_prompt
        if extract_techno:
            system_prompt += techno_prompt
        if extract_salary:
            system_prompt += salary_prompt
        system_prompt += default_values
        
        # Verify environment variables
        if not all([os.getenv('AZURE_OPENAI_ENDPOINT'),
                   os.getenv('AZURE_OPENAI_API_KEY'),
                   os.getenv('AZURE_OPENAI_MODEL_NAME')]):
            raise ValueError("Missing required environment variables")
       
        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": job_description}
                ]
            )
           
            # Extract result and token usage
            result = eval(response.choices[0].message.content)
            token_cost = response.usage.total_tokens
           
            # Set default values for optional fields
            if not extract_techno:
                result['technologies_required'] = []
            if not extract_salary:
                result['salary_offered'] = 0
           
            # Create and return JobAIanalysis object
            return JobAIanalysis(
                required_studies=result['required_studies'],
                technologies_required=result['technologies_required'],
                experience_years_needed=result['experience_years_needed'],
                salary_offered=result['salary_offered'],
                token_cost=token_cost
            )
           
        except Exception as e:
            # Log the error and re-raise it
            print(f"Error extracting job data: {str(e)}")
            raise