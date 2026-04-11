"""Abstract base class for stores"""
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseStore(ABC):
    """Abstract base class for all stores"""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url

    @abstractmethod
    def get_categories(self, driver) -> Dict[str, str]:
        """Get store categories by parsing the website"""
        pass

    @abstractmethod
    def parse_category(self, driver, category_url: str) -> List[Dict]:
        """Parse products from category"""
        pass

    @abstractmethod
    def get_category_prompt_hints(self) -> str:
        """Get hints for LLM category selection"""
        pass

    def get_cache_key(self, category_url: str) -> str:
        return f"{self.name}:{category_url}"

    def __repr__(self):
        return f"Store({self.name})"