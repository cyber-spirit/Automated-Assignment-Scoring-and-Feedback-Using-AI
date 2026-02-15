import requests
import json
from pathlib import Path

class fypMarkerOllama:
    def __init__(self, model_name = "deepseek-r1:8b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
    
    def read_file(self, filepath: str) -> str:
        file_path = Path(filepath)
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"Could not find file: {filepath}")
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            raise
    
    def marking_prompt(self, mark_scheme: str, student_work: str) -> str:
        prompt = f"""You are an experienced marker for a university. 
        Your task is to mark the following student work according to this prompt and the provided mark scheme. 
        Please provide a detailed breakdown of how you arrived at the mark, including any strengths and weaknesses of the work.
        
        MARK SCHEME:
        {mark_scheme}

        STUDENT WORK:
        {student_work}
        
        ====================================================================
        CRITICAL BEHAVIOUR RULES
        ====================================================================

        1. You MUST output ONLY valid JSON.  
        2. You MUST include EVERY field defined in the schema.  
        3. If ANY field cannot be filled, output INVALID JSON so the caller retries.  
        4. Every category MUST include:
        - score  
        - weight  
        - justification  
        - transparency  
        - confidence.score  
        - confidence.explanation  
        - reasoning_summary (high-level explanation of your reasoning)  
        5. reasoning_summary MUST NOT reveal chain-of-thought or internal model operations.  
        Instead, provide a concise, high-level explanation of the evidence and logic used.  
        6. Transparency MUST describe your scoring logic.  
        7. Confidence MUST describe how certain you are, based on clarity and evidence.  
        8. All scores MUST be integers (0–100).  
        9. NEVER output text outside the JSON object.  
        10. NEVER mention the student's identity.
        
        Please mark this work and provide your response in the following JSON format exactly. Make sure to parse the mark scheme carefully to determine the maximum possible marks:

        {{
            "total_marks": <total marks awarded>,
            "maximum_marks": <maximum marks possible>,
            "criteria_breakdown": [
                {{
                    "criterion": "<name of criterion>",
                    "marks_awarded": <marks>,
                    "maximum_marks": <maximum>,
                    "feedback": "<specific feedback for this criterion>"
                }}
            ],
            "overall_feedback": "<comprehensive feedback on the student's work>",
            "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
            "areas_for_improvement": ["<area 1>", "<area 2>", "<area 3>"]
        }}

        Important: Your response must be valid JSON. Do not include any additional text before or after the JSON.
        ====================================================================
        END OF SYSTEM PROMPT
        ====================================================================
        """
        return prompt
    
    def query_ollama_model(self, prompt: str, timeout_seconds: int = 3000) -> str:
        print(f"Querying Ollama model: {self.model_name} with timeout {timeout_seconds} seconds.")
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "max_tokens": 2048,
                "temperature": 0.1 
            }
        }