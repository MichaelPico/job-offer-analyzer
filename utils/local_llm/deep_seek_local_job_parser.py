import json
import torch
from transformers import pipeline
import re

class DeepSeekLocalJobParser :
    def __init__(self):
        """Initialize the DeepSeek model pipeline"""
        device = 0 if torch.cuda.is_available() else -1  # Use GPU if available
        self.model = pipeline(
            "text-generation",
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
            max_length=1024,
            do_sample=True,
            device=device
        )
    
    def extract_technologies(self, job_description: str) -> str:
        """
        Extract programming languages and technologies from a job description.
        
        Args:
            job_description (str): The job description text to analyze
            
        Returns:
            str: Comma-separated list of technologies
        """
        messages = [
            {
                "role": "user", 
                "content": '''Extract the software related technologies/skills that you can identify in this job description. 
                          Answer me in json format like this: \"{{\"technologies\" : ["Java", "Kubernetes", "JavaScript"]}}\". 
                          Do not tell me anything else, just the json with one key "technologies".
                          Job description: {job_description}'''
            }
        ]
        
        try:
            # Generate response using the model
            response = self.model(messages)
            chat = response[0]['generated_text']
            last_assistant_response = chat[-1]['content']
            response_trimmed = re.sub(r"<think>.*?</think>\s*", "", last_assistant_response, flags=re.DOTALL)
            response_trimmed = re.sub(r"^```json\s*|\s*```$", "", response_trimmed, flags=re.DOTALL)
            response_trimmed = response_trimmed.replace('{{', '{').replace('}}', '}')
            response_trimmed = re.search(r"\{.*\}", response_trimmed, re.DOTALL)
            response_as_json = json.loads(response_trimmed.group(0))
            return response_as_json
        except Exception as e:
            print(f"Error extracting technologies: {e}")
            return {"technologies": []}
    
    