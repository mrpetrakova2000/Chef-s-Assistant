"""Cache agent - simple in-memory cache with TTL"""
import hashlib
import time
from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage


class CacheAgent:
    """Simple cache manager with TTL"""

    def __init__(self, ttl_hours: int = 6):
        self.products_cache: Dict[str, Dict] = {}
        self.categories_cache: Dict[str, Dict] = {}
        self.message_history_cache: Dict[str, Dict] = {}
        self.history: List[Dict] = []
        self.ttl = ttl_hours * 3600

    def clear(self):
        """Clear all caches"""
        self.products_cache.clear()
        self.categories_cache.clear()
        self.message_history_cache.clear()
        self.history.clear()
        print("    CacheAgent: All caches cleared")

    def get_cached_llm_response(self, messages: List[BaseMessage]) -> Optional[str]:
        """Get cached LLM response"""
        content = "".join([m.content for m in messages])
        key = hashlib.md5(content.encode()).hexdigest()
        if key in self.message_history_cache:
            entry = self.message_history_cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['response']
            else:
                del self.message_history_cache[key]
        return None

    def save_llm_response(self, messages: List[BaseMessage], response: str):
        """Save LLM response to cache"""
        content = "".join([m.content for m in messages])
        key = hashlib.md5(content.encode()).hexdigest()
        self.message_history_cache[key] = {
            'response': response,
            'timestamp': time.time()
        }

    def get_cached_products(self, store: str, category_url: str) -> Optional[List[Dict]]:
        """Get cached products"""
        cache_key = f"{store}:{category_url}"
        if cache_key in self.products_cache:
            entry = self.products_cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl:
                print(f'    Использую кэш для {store}')
                return entry['products']
            else:
                print(f'    Кэш устарел для {store}, удаляю.')
                del self.products_cache[cache_key]
        return None

    def save_products(self, store: str, category_url: str, products: List[Dict]):
        """Save products to cache"""
        cache_key = f"{store}:{category_url}"
        self.products_cache[cache_key] = {
            'products': products,
            'timestamp': time.time()
        }
        print(f'    Кэширую {len(products)} товаров для {store}')

    def get_cached_categories(self, store: str) -> Optional[Dict[str, str]]:
        """Get cached categories"""
        if store in self.categories_cache:
            entry = self.categories_cache[store]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['categories']
            else:
                del self.categories_cache[store]
        return None

    def save_categories(self, store: str, categories: Dict[str, str]):
        """Save categories to cache"""
        self.categories_cache[store] = {
            'categories': categories,
            'timestamp': time.time()
        }

    def log_search(self, product: str, store: str, category: str, success: bool):
        """Log search"""
        self.history.append({
            'product': product,
            'store': store,
            'category': category,
            'success': success,
            'time': time.time()
        })

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_products = sum(len(entry['products']) for entry in self.products_cache.values())
        return {
            'cached_categories': len(self.products_cache),
            'total_products': total_products,
            'cached_llm_responses': len(self.message_history_cache),
            'searches': len(self.history),
            'success_rate': sum(1 for h in self.history if h['success']) / len(self.history) if self.history else 0
        }