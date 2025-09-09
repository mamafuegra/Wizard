# LLAMA INTEGRATION TEMPLATE
# Use this tomorrow when you're ready to add Llama AI

import os
import requests
from typing import Optional

async def ask_llama(question: str) -> Optional[str]:
    """Ask Llama AI using your preferred API endpoint"""
    
    # Option 1: LLM API Console (your current setup)
    llm_api_key = os.getenv('LLAMA_API_KEY')
    if llm_api_key:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm_api_key}"
            }
            
            data = {
                "model": "meta-llama/Llama-3.1-8B-Instruct:cerebras",  # or your preferred model
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant. Provide clear, concise answers."},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://api.apillm.com/v1/chat/completions", 
                headers=headers, 
                json=data, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"LLM API error: {e}")
    
    # Option 2: Together AI (free tier)
    together_api_key = os.getenv('TOGETHER_API_KEY')
    if together_api_key:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {together_api_key}"
            }
            
            data = {
                "model": "meta-llama/Llama-2-7b-chat-hf",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Together AI error: {e}")
    
    # Option 3: Local Llama (if running on your computer)
    local_llama_url = os.getenv('LLAMA_LOCAL_URL')
    if local_llama_url:
        try:
            data = {
                "model": "llama-2-7b-chat",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                f"{local_llama_url}/v1/chat/completions",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Local Llama error: {e}")
    
    return None

# To integrate this into your premium.py:
# 1. Replace the placeholder messages with actual Llama calls
# 2. Add this function to your Premium class
# 3. Update the ai_group command to use ask_llama()
# 4. Set your API keys in .env file

# Example usage in premium.py:
"""
@ai_group.command(name='llama')
async def ai_llama(self, ctx: commands.Context, *, question: str):
    response = await ask_llama(question)
    if response:
        await ctx.send(f"🦙 **Llama AI:**\n{response}")
    else:
        await ctx.send("Sorry, I couldn't get a response from Llama right now.")
"""
