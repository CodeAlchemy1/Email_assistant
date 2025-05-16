import requests
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable

# DeepSeek API configuration
DEEPSEEK_API_KEY = "secret"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class DeepSeekClient:
    """The DeepSeek API client handles the interaction with the AI model"""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        # Default system prompt words guide the AI to act as an email assistant
        self.system_prompt = """Always respond in English. You are a professional email assistant who can:
1. Correct grammar and spelling errors in emails.
2. Adjust tone and style (formal, friendly, professional, etc.).
3. Suggest rewrites for clarity and impact.
4. Translate emails into different languages.
5. Provide email templates for various scenarios.
6. Summarize long emails into concise key points.
7. Generate emails for specific use cases based on simple instructions.

Understand the user's intent and reply helpfully, maintaining context across multiple turns.
"""

    def generate_response(
        self, 
        user_message: str, 
        history: Optional[List[Dict[str, str]]] = None,
        model: str = "deepseek-chat"
    ) -> Dict[str, Any]:
        """
        Generate a single (non-streaming) AI response.
        
        Parameters:
            user_message: The latest user message to send.
            history:     List of previous {"role":…, "content":…} entries.
            model:       Which model name to use.

        Returns:
            A dict: {"code": int, "data": str (the AI's reply), "msg": str}
        """
        if history is None:
            history = []
        
        # Build a complete message list, including system prompts, 
        # history records and current user messages
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,  # To control creativity, a lower value makes the response more definite
                "max_tokens": 2000,  # Limit reply length
                "stream": False      # Do not use stream response
            }
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "code": 200,
                    "data": result["choices"][0]["message"]["content"],
                    "msg": "Success"
                }
            else:
                return {
                    "code": 400,
                    "data": None,
                    "msg": f"API request failed: {response.status_code}, {response.text}"
                }
        except Exception as e:
            return {
                "code": 400,
                "data": None,
                "msg": f"An error occurred: {str(e)}"
            }
    
    async def generate_stream_response(
        self, 
        user_message: str, 
        history: Optional[List[Dict[str, str]]] = None,
        model: str = "deepseek-chat"
    ) -> AsyncGenerator[str, None]:
        """
        Generate an AI response in streaming mode.
        
        Parameters:
            user_message: The user's current message.
            history:      Conversation history as a list of messages.
            model:        The AI model to use.
            
        Returns:
            An async generator yielding chunks of the AI's streaming response.
        """
        if history is None:
            history = []
        
        # Build a complete message list
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": True  # Enable stream response
            }
            
            async def fetch_stream():
                session = requests.Session()
                response = session.post(
                    DEEPSEEK_API_URL,
                    headers=self.headers,
                    data=json.dumps(payload),
                    stream=True
                )
                
                if response.status_code != 200:
                    error_msg = f"API request failed: {response.status_code}, {response.text}"
                    yield json.dumps({"code": 400, "data": None, "msg": error_msg}) + "\n"
                    return
                
                # Analytical stream response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove the 'data: ' prefix
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if chunk['choices'][0]['finish_reason'] is not None:
                                    break
                                delta = chunk['choices'][0]['delta']
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    # Add a newline character as the delimiter for each JSON response
                                    yield json.dumps({
                                        "code": 200,
                                        "data": content,
                                        "full": full_response,
                                        "msg": "Success",
                                        "done": False
                                    }) + "\n"
                            except json.JSONDecodeError:
                                continue
                
                # Send the completion mark and add a newline character as well
                yield json.dumps({
                    "code": 200,
                    "data": "",
                    "full": full_response,
                    "msg": "Success",
                    "done": True
                }) + "\n"
            
            async for chunk in fetch_stream():
                yield chunk
                
        except Exception as e:
            yield json.dumps({
                "code": 400,
                "data": None,
                "msg": f"An error occurred: {str(e)}",
                "done": True
            }) + "\n"
    
    def analyze_email(self, email_content: str) -> Dict[str, Any]:
        """
        Analyze an email’s content, providing a summary and improvement suggestions.

        
        Parameters:
            email_content: The raw email text to analyze.
            
        Returns:
            A dict containing the analysis results.
        """
        prompt = f"""Please analyze the following email and provide:
1. A concise summary of its main points.
2. Corrections for any grammar or spelling errors.
3. Feedback on tone and style, with suggestions for improvement.
4. An evaluation of overall structure and clarity.

Email content:
{email_content}
"""
        return self.generate_response(prompt)
    
    async def analyze_email_stream(self, email_content: str):
        """
        Stream analysis of an email's content.
        """
        prompt = f"""Please analyze the following email and provide:
1. A concise summary of its main points.
2. Corrections for any grammar or spelling errors.
3. Feedback on tone and style, with suggestions for improvement.
4. An evaluation of overall structure and clarity.

Email content:
{email_content}
"""
        async for chunk in self.generate_stream_response(prompt):
            yield chunk
    
    def rewrite_email(self, email_content: str, requirements: str) -> Dict[str, Any]:
        """
        Rewrite an email according to specific requirements.
        
        Parameters:
            email_content: The original email text.
            requirements:  What to change (e.g., “more formal”, “friendlier”).
            
        Returns:
            A dict containing the rewritten email.
        """
        prompt = f"""Please rewrite the following email according to these requirements:
Requirements: {requirements}

Original email:
{email_content}

Please provide the fully rewritten email.
"""
        return self.generate_response(prompt)
    
    async def rewrite_email_stream(self, email_content: str, requirements: str):
        """
        Stream the rewrite_email operation.
        """
        prompt = f"""Please rewrite the following email according to these requirements:
Requirements: {requirements}

Original email:
{email_content}

Provide the fully rewritten email.
"""
        async for chunk in self.generate_stream_response(prompt):
            yield chunk
    
    def translate_email(self, email_content: str, target_language: str) -> Dict[str, Any]:
        """
        Translate an email into a specified language.
        
        Parameters:
            email_content: The original email text.
            target_language: The language to translate into (e.g. "English", "Japanese").
            
        Returns:
            A dict containing the translated email.
        """
        prompt = f"""Please translate the following email into {target_language}, preserving its meaning and tone:

Original email:
{email_content}

Translation into {target_language}:
"""
        return self.generate_response(prompt)
    
    async def translate_email_stream(self, email_content: str, target_language: str):
        """
        Stream the email translation.
        """
        prompt = f"""Please translate the following email into {target_language}, preserving its meaning and tone:

Original email:
{email_content}

Translation into {target_language}:
"""
        async for chunk in self.generate_stream_response(prompt):
            yield chunk
    
    def generate_email_template(self, scenario: str) -> Dict[str, Any]:
        """
        Generate a professional email template for a given scenario.
        
        Parameters:
            scenario: A description of the scenario, e.g. "meeting invitation", "customer complaint response", etc.
            
        Returns:
            A dict containing the generated template.
        """
        prompt = f"""Please generate a professional email template for the following scenario:
Scenario: {scenario}

Provide a complete email including a subject line and body. You may use placeholders like [Name], [Company], etc., for user-specific details.
"""
        return self.generate_response(prompt)
    
    async def generate_email_template_stream(self, scenario: str):
        """
        Stream a professional email template generation.
        """
        prompt = f"""Please generate a professional email template for the following scenario:
Scenario: {scenario}

Provide a complete email including a subject line and body. You may use placeholders like [Name], [Company], etc., for user-specific details.
"""
        async for chunk in self.generate_stream_response(prompt):
            yield chunk
    
    def generate_follow_up_email(self, previous_email: str, instruction: str) -> Dict[str, Any]:
        """
        Generate a follow-up email based on a previous message and an instruction.
        
        Parameters:
            previous_email: The content of the prior email.
            instruction: User instruction, e.g. "nudge for a reply", "thank them", etc.
            
        Returns:
            A dict containing the generated follow-up email.
        """
        prompt = f"""Based on the following prior email and the instruction "{instruction}", please craft an appropriate follow-up email:

Previous email:
{previous_email}

Please provide a complete follow-up email including subject line and body.
"""
        return self.generate_response(prompt)
    
    async def generate_follow_up_email_stream(self, previous_email: str, instruction: str):
        """
        Stream generation of a follow-up email.
        """
        prompt = f"""Based on the following previous email and the instruction "{instruction}", please generate an appropriate follow-up email:

Previous email:
{previous_email}

Please provide a complete follow-up email including subject line and body.
"""
        async for chunk in self.generate_stream_response(prompt):
            yield chunk 
