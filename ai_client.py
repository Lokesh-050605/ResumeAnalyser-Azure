# import google.generativeai as genai
# import json
# import time
# from typing import Dict, Any

# class GeminiClient:
#     def __init__(self, api_key):
#         genai.configure(api_key=api_key)
#         self.model = genai.GenerativeModel("gemini-2.0-flash")
#         self.max_retries = 3
#         self.retry_delay = 2
    
#     def analyze_resume(self, resume_text: str, job_description: str = "") -> Dict[str, Any]:
#         """Analyze resume and return structured data"""
#         prompt = self._build_analysis_prompt(resume_text, job_description)
        
#         for attempt in range(self.max_retries):
#             try:
#                 response = self.model.generate_content(prompt)
                
#                 # Parse JSON from response
#                 result_text = response.text.strip()
                
#                 # Extract JSON if wrapped in markdown code blocks
#                 if result_text.startswith('```'):
#                     result_text = result_text.split('```')[1]
#                     if result_text.startswith('json'):
#                         result_text = result_text[4:]
#                     result_text = result_text.strip()
                
#                 analysis = json.loads(result_text)
                
#                 # Validate structure
#                 self._validate_analysis(analysis)
                
#                 return analysis
            
#             except json.JSONDecodeError as e:
#                 if attempt < self.max_retries - 1:
#                     time.sleep(self.retry_delay)
#                     continue
#                 else:
#                     # Return basic structure if parsing fails
#                     return self._get_default_analysis(str(e))
            
#             except Exception as e:
#                 if attempt < self.max_retries - 1:
#                     time.sleep(self.retry_delay)
#                     continue
#                 else:
#                     raise Exception(f"Failed to analyze resume: {str(e)}")
    
#     def _build_analysis_prompt(self, resume_text: str, job_description: str = "") -> str:
#         """Build prompt for Gemini API"""
#         base_prompt = f"""
# Analyze the following resume and extract structured information. Return ONLY valid JSON with no additional text.

# Resume Text:
# {resume_text}

# Extract and return JSON with the following structure:
# {{
#     "personal_info": {{
#         "name": "Full Name (or 'Not Found')",
#         "email": "Email address (or 'Not Found')",
#         "phone": "Phone number (or 'Not Found')",
#         "location": "Location/City (or 'Not Found')"
#     }},
#     "summary": "A professional 2-3 sentence summary of the candidate's profile",
#     "skills": ["skill1", "skill2", "skill3", ...],
#     "education": [
#         {{
#             "degree": "Degree name",
#             "institution": "University/College name",
#             "year": "Graduation year",
#             "details": "Additional details"
#         }}
#     ],
#     "experience": [
#         {{
#             "title": "Job title",
#             "company": "Company name",
#             "duration": "Time period",
#             "responsibilities": ["responsibility1", "responsibility2", ...]
#         }}
#     ],
#     "certifications": ["cert1", "cert2", ...],
#     "suggestions": [
#         "Specific suggestion 1 to improve resume",
#         "Specific suggestion 2 to improve resume",
#         "Specific suggestion 3 to improve resume"
#     ],
#     "overall_score": 75,
#     "strengths": ["strength1", "strength2", "strength3"],
#     "areas_for_improvement": ["area1", "area2"]
# """
        
#         if job_description:
#             base_prompt += f"""
#     ,
#     "job_match": {{
#         "score": 85,
#         "matching_skills": ["skill1", "skill2", ...],
#         "missing_skills": ["skill1", "skill2", ...],
#         "experience_match": "Brief explanation of how experience matches",
#         "recommendations": ["recommendation1", "recommendation2", ...]
#     }}
# }}

# Job Description:
# {job_description}

# Calculate job match score (0-100) based on:
# - Skills overlap (40% weight)
# - Experience relevance (30% weight)
# - Education match (20% weight)
# - Overall fit (10% weight)
# """
#         else:
#             base_prompt += "\n}"
        
#         base_prompt += "\n\nReturn ONLY the JSON object, no explanations or markdown."
        
#         return base_prompt
    
#     def _validate_analysis(self, analysis: Dict[str, Any]):
#         """Validate that analysis has required fields"""
#         required_fields = ['personal_info', 'summary', 'skills', 'education', 'experience', 'suggestions']
        
#         for field in required_fields:
#             if field not in analysis:
#                 raise ValueError(f"Missing required field: {field}")
    
#     def _get_default_analysis(self, error_msg: str) -> Dict[str, Any]:
#         """Return default analysis structure when parsing fails"""
#         return {
#             "personal_info": {
#                 "name": "Not Found",
#                 "email": "Not Found",
#                 "phone": "Not Found",
#                 "location": "Not Found"
#             },
#             "summary": "Unable to generate summary due to parsing error.",
#             "skills": [],
#             "education": [],
#             "experience": [],
#             "certifications": [],
#             "suggestions": [
#                 "Please try uploading the resume again",
#                 "Ensure the resume is in a readable format"
#             ],
#             "overall_score": 0,
#             "strengths": [],
#             "areas_for_improvement": ["Unable to analyze due to error"],
#             "error": error_msg
#         }






import json
import time
import requests
import os
from typing import Dict, Any

class GeminiClient:
    def __init__(self, api_key=None):
        # Check if using proxy
        self.proxy_url = os.getenv('GEMINI_PROXY_URL')
        
        if self.proxy_url:
            # Using proxy - no need for API key here
            self.use_proxy = True
            # Remove trailing slash if present
            self.proxy_url = self.proxy_url.rstrip('/')
            print(f"Using Gemini Proxy: {self.proxy_url}")
        else:
            # Direct API access (original behavior)
            self.use_proxy = False
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print("Using direct Gemini API access")
        
        self.max_retries = 3
        self.retry_delay = 2
    
    def analyze_resume(self, resume_text: str, job_description: str = "") -> Dict[str, Any]:
        """Analyze resume and return structured data"""
        prompt = self._build_analysis_prompt(resume_text, job_description)
        
        for attempt in range(self.max_retries):
            try:
                if self.use_proxy:
                    # Use proxy server
                    response_text = self._call_proxy(prompt)
                else:
                    # Direct API call
                    response = self.model.generate_content(prompt)
                    response_text = response.text
                
                # Parse JSON from response
                result_text = response_text.strip()
                
                # Extract JSON if wrapped in markdown code blocks
                if result_text.startswith('```'):
                    result_text = result_text.split('```')[1]
                    if result_text.startswith('json'):
                        result_text = result_text[4:]
                    result_text = result_text.strip()
                
                analysis = json.loads(result_text)
                
                # Validate structure
                self._validate_analysis(analysis)
                
                return analysis
            
            except json.JSONDecodeError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # Return basic structure if parsing fails
                    return self._get_default_analysis(str(e))
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Failed to analyze resume: {str(e)}")
    
    def _call_proxy(self, prompt: str) -> str:
        """Call the local proxy server"""
        try:
            url = f"{self.proxy_url}/analyze"
            
            payload = {
                "prompt": prompt,
                "model": "gemini-2.0-flash"
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60  # 60 seconds timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                return result['response']
            else:
                raise Exception(f"Proxy error: {result.get('error', 'Unknown error')}")
        
        except requests.exceptions.Timeout:
            raise Exception("Proxy request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to proxy server at {self.proxy_url}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Proxy request failed: {str(e)}")
    
    def _build_analysis_prompt(self, resume_text: str, job_description: str = "") -> str:
        """Build prompt for Gemini API"""
        base_prompt = f"""
Analyze the following resume and extract structured information. Return ONLY valid JSON with no additional text.

Resume Text:
{resume_text}

Extract and return JSON with the following structure:
{{
    "personal_info": {{
        "name": "Full Name (or 'Not Found')",
        "email": "Email address (or 'Not Found')",
        "phone": "Phone number (or 'Not Found')",
        "location": "Location/City (or 'Not Found')"
    }},
    "summary": "A professional 2-3 sentence summary of the candidate's profile",
    "skills": ["skill1", "skill2", "skill3", ...],
    "education": [
        {{
            "degree": "Degree name",
            "institution": "University/College name",
            "year": "Graduation year",
            "details": "Additional details"
        }}
    ],
    "experience": [
        {{
            "title": "Job title",
            "company": "Company name",
            "duration": "Time period",
            "responsibilities": ["responsibility1", "responsibility2", ...]
        }}
    ],
    "certifications": ["cert1", "cert2", ...],
    "suggestions": [
        "Specific suggestion 1 to improve resume",
        "Specific suggestion 2 to improve resume",
        "Specific suggestion 3 to improve resume"
    ],
    "overall_score": 75,
    "strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2"]
"""
        
        if job_description:
            base_prompt += f"""
    ,
    "job_match": {{
        "score": 85,
        "matching_skills": ["skill1", "skill2", ...],
        "missing_skills": ["skill1", "skill2", ...],
        "experience_match": "Brief explanation of how experience matches",
        "recommendations": ["recommendation1", "recommendation2", ...]
    }}
}}

Job Description:
{job_description}

Calculate job match score (0-100) based on:
- Skills overlap (40% weight)
- Experience relevance (30% weight)
- Education match (20% weight)
- Overall fit (10% weight)
"""
        else:
            base_prompt += "\n}"
        
        base_prompt += "\n\nReturn ONLY the JSON object, no explanations or markdown."
        
        return base_prompt
    
    def _validate_analysis(self, analysis: Dict[str, Any]):
        """Validate that analysis has required fields"""
        required_fields = ['personal_info', 'summary', 'skills', 'education', 'experience', 'suggestions']
        
        for field in required_fields:
            if field not in analysis:
                raise ValueError(f"Missing required field: {field}")
    
    def _get_default_analysis(self, error_msg: str) -> Dict[str, Any]:
        """Return default analysis structure when parsing fails"""
        return {
            "personal_info": {
                "name": "Not Found",
                "email": "Not Found",
                "phone": "Not Found",
                "location": "Not Found"
            },
            "summary": "Unable to generate summary due to parsing error.",
            "skills": [],
            "education": [],
            "experience": [],
            "certifications": [],
            "suggestions": [
                "Please try uploading the resume again",
                "Ensure the resume is in a readable format"
            ],
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": ["Unable to analyze due to error"],
            "error": error_msg
        }