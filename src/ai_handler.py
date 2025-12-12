import os
import requests
import google.generativeai as genai
import json

class AIHandler:
    def __init__(self, backend='gemini', model_name=None):
        self.backend = backend
        self.model_name = model_name
        
        if backend == 'gemini':
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")
            genai.configure(api_key=api_key)
            # Default to flash if not specified
            self.model = genai.GenerativeModel(self.model_name or 'gemini-1.5-flash')
            
        elif backend == 'ollama':
            # Default to llama3 or mistral if not specified
            self.model_name = self.model_name or 'llama3'
            self.api_url = "http://localhost:11434/api/generate"

    def generate(self, prompt):
        """
        Unified generation method.
        Returns the text response string.
        """
        if self.backend == 'gemini':
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Gemini Error: {e}")
                return ""
                
        elif self.backend == 'ollama':
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1  # Keep it factual
                    }
                }
                response = requests.post(self.api_url, json=payload)
                response.raise_for_status()
                return response.json().get('response', '')
            except Exception as e:
                print(f"Ollama Error (ensure Ollama is running): {e}")
                return ""
        
        return ""