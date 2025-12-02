#!/usr/bin/env python3
"""
Direct test of gpt-5-nano API behavior
"""

import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=False)

async def test_direct():
    api_key = os.getenv("LLM_BINDING_API_KEY")
    if not api_key:
        print("ERROR: LLM_BINDING_API_KEY not set")
        return
    
    client = AsyncOpenAI(api_key=api_key)
    
    print("Testing direct API call with gpt-5-nano...")
    
    response = await client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello"}
        ],
        max_completion_tokens=50
    )
    
    print(f"Response: {response}")
    print(f"Content: {response.choices[0].message.content}")

asyncio.run(test_direct())
