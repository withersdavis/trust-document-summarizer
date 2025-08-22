import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv

class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        load_dotenv()
        
        self.provider = provider or os.getenv('LLM_PROVIDER', 'anthropic')
        
        if self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'openai':
            self._init_openai()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _init_anthropic(self):
        import anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        # Simple initialization without proxies parameter
        self.client = anthropic.Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
    
    def _init_openai(self):
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    def process_document(self, system_prompt: str, user_content: str) -> Dict:
        """
        Process document with LLM and return parsed JSON response
        """
        if self.provider == 'anthropic':
            return self._process_with_anthropic(system_prompt, user_content)
        else:
            return self._process_with_openai(system_prompt, user_content)
    
    def _process_with_anthropic(self, system_prompt: str, user_content: str) -> Dict:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )
            
            response_text = response.content[0].text
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            raise Exception(f"Error processing with Anthropic: {str(e)}")
    
    def _process_with_openai(self, system_prompt: str, user_content: str) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt + "\n\nYou must respond with valid JSON."},
                    {"role": "user", "content": user_content}
                ]
            )
            
            response_text = response.choices[0].message.content
            return json.loads(response_text)
                
        except Exception as e:
            raise Exception(f"Error processing with OpenAI: {str(e)}")