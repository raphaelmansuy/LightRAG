#!/usr/bin/env python3
"""
Test gpt-5-nano with different token limits and reasoning settings
"""

import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=False)

async def test_with_more_tokens():
    api_key = os.getenv("LLM_BINDING_API_KEY")
    if not api_key:
        print("ERROR: LLM_BINDING_API_KEY not set")
        return
    
    client = AsyncOpenAI(api_key=api_key)
    
    print("Test 1: With 200 max_completion_tokens (original: 50)")
    response = await client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello"}
        ],
        max_completion_tokens=200
    )
    print(f"Content: '{response.choices[0].message.content}'")
    print(f"Tokens used - Completion: {response.usage.completion_tokens}, Reasoning: {response.usage.completion_tokens_details.reasoning_tokens}")
    print()
    
    print("Test 2: With lower reasoning_effort='low'")
    response = await client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello"}
        ],
        max_completion_tokens=50,
        reasoning_effort="low"
    )
    print(f"Content: '{response.choices[0].message.content}'")
    print(f"Tokens used - Completion: {response.usage.completion_tokens}, Reasoning: {response.usage.completion_tokens_details.reasoning_tokens}")
    print()

asyncio.run(test_with_more_tokens())
