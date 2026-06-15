"""LLM utility functions"""
import time
from langchain_mistralai import ChatMistralAI
from app.config import MISTRAL_API_KEY, LLM_MODEL, LLM_TEMPERATURE

_llm = None


def get_llm(temperature=None):
    global _llm
    if temperature is not None:
        return ChatMistralAI(model=LLM_MODEL, api_key=MISTRAL_API_KEY, temperature=temperature)
    if _llm is None:
        _llm = ChatMistralAI(model=LLM_MODEL, api_key=MISTRAL_API_KEY, temperature=LLM_TEMPERATURE)
    return _llm


def call_llm_with_retry(messages, max_retries=2, agent_name="LLM", temperature=None):
    for attempt in range(max_retries):
        try:
            llm = get_llm(temperature)
            response = llm.invoke(messages).content
            return response
        except Exception as e:
            print(f"    [{agent_name}] Attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    return None