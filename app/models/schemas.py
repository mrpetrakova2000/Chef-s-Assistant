"""Pydantic schemas for data validation"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class Product(BaseModel):
    """Product model"""
    link: str
    description: str
    price: str
    store: str


class StoreOffer(BaseModel):
    """Store offer model"""
    store: str
    product: Optional[Product] = None
    success: bool = False
    category: str = ""
    found_count: int = 0
    error: Optional[str] = None


class IngredientResult(BaseModel):
    """Ingredient search result"""
    ingredient: str
    success: bool
    offers: List[StoreOffer] = []
    selected_offer: Optional[StoreOffer] = None
    category: str = ""
    found_count: int = 0


class PlanItem(BaseModel):
    """Plan item (ingredient)"""
    name: str


class State(BaseModel):
    """Graph state"""
    question: str
    skip_execution: bool = False
    dish_name: Optional[str] = ""
    portions: Optional[int] = 0
    plan: List[PlanItem] = []

    current_ingredient_index: int = 0
    current_store_index: int = 0
    current_ingredient: str = ""
    current_store: str = ""

    current_category_name: str = ""
    current_category_url: str = ""
    current_products: List[Product] = []
    current_selected_product: Optional[Product] = None

    current_ingredient_offers: List[StoreOffer] = []

    search_results: List[IngredientResult] = []
    total_price: float = 0.0
    final_response: str = ""
    finished: bool = False


class StateUpdate(BaseModel):
    """Partial state update"""
    question: Optional[str] = None
    skip_execution: Optional[bool] = None
    dish_name: Optional[str] = None
    portions: Optional[int] = None
    plan: Optional[List[PlanItem]] = None
    current_ingredient_index: Optional[int] = None
    current_store_index: Optional[int] = None
    current_ingredient: Optional[str] = None
    current_store: Optional[str] = None
    current_category_name: Optional[str] = None
    current_category_url: Optional[str] = None
    current_products: Optional[List[Product]] = None
    current_selected_product: Optional[Product] = None
    current_ingredient_offers: Optional[List[StoreOffer]] = None
    search_results: Optional[List[IngredientResult]] = None
    total_price: Optional[float] = None
    final_response: Optional[str] = None
    finished: Optional[bool] = None


class ParseCategoryInput(BaseModel):
    category_url: str
    store: str


class GeneratePlanInput(BaseModel):
    question: str


class RouteIngredientInput(BaseModel):
    product_name: str
    dish_name: str
    store: str
    all_categories: Dict[str, str]


class SelectProductInput(BaseModel):
    products: List[Product]
    target_product: str
    dish_name: str


class CompareOffersInput(BaseModel):
    ingredient: str
    offers: List[StoreOffer]
    dish_name: str


class GenerateReportInput(BaseModel):
    dish_name: str
    portions: int
    search_results: List[IngredientResult]