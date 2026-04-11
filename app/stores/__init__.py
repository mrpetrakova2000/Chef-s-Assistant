"""Store implementations"""
from .base import BaseStore
from .dixy import DixyStore
from .magnit import MagnitStore
from .vkusvill import VkusvillStore

STORE_REGISTRY = {
    "dixy.ru": DixyStore(),
    "magnit.ru": MagnitStore(),
    "vkusvill.ru": VkusvillStore(),
}

__all__ = ["BaseStore", "DixyStore", "MagnitStore", "VkusvillStore", "STORE_REGISTRY"]