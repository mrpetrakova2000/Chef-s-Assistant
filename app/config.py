"""Configuration module"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY is required")

# Cache settings
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")
MAGNIT_SHOP_CODE = os.getenv("MAGNIT_SHOP_CODE", "783094")

# Stores to warmup on startup
WARMUP_STORES = os.getenv("WARMUP_STORES", "dixy.ru").split(",")

# LLM settings
LLM_MODEL = "mistral-large-latest"
LLM_TEMPERATURE = 0.1
LLM_MAX_RETRIES = 2

# Supported stores
SUPPORTED_STORES = ["dixy.ru", "magnit.ru", "vkusvill.ru"]