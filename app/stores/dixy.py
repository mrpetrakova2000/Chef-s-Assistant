"""Dixy store implementation"""
import time
import random
from typing import Dict, List
from bs4 import BeautifulSoup
from .base import BaseStore


class DixyStore(BaseStore):
    """Dixy store parser"""

    def __init__(self):
        super().__init__("dixy.ru", "https://dixy.ru")
        self.article_tag = "article"
        self.description_selector = "div.card__info p"
        self.price_selector = 'div.card__action div[class*="card__price"] div.card__price-num'
        self.category_selector = "div.item-link a"
        self.forbidden_categories = [
            'Скидки по карте', 'Гигиена и косметика', 'Бытовая химия',
            'Товары для животных', 'Товары для детей'
        ]

    def get_categories(self, driver) -> Dict[str, str]:
        """
        Получает список всех основных категорий с главной страницы dixy.ru.
        Оставляет только категории с максимальной глубиной URL.
        """
        driver.get(self.base_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        categories = {}
        for div in soup.select('div.item-link'):
            link = div.select_one('a')
            if link and link.get('href'):
                categories[link.text.strip()] = link['href']

        # Определяем максимальную глубину URL
        all_depths = [len(url.strip('/').split('/')) for url in categories.values()]
        max_depth = max(all_depths) if all_depths else 0

        # Оставляем только категории с максимальной глубиной (последний уровень)
        valid_categories = {
            name: url for name, url in categories.items()
            if len(url.strip('/').split('/')) == max_depth
        }

        # Исключаем запрещенные категории
        final_categories = {
            k: v for k, v in valid_categories.items()
            if k not in self.forbidden_categories
        }

        # На всякий случай
        if not final_categories:
            final_categories = categories

        return final_categories

    def parse_category(self, driver, category_url: str) -> List[Dict]:
        """
        Парсит страницы категории на dixy.ru с пагинацией.
        """
        all_items = []
        page = 1
        seen_links = set()

        print(f'    Начинаю парсинг категории: {category_url}')

        while True:
            url = f"{self.base_url}{category_url}?page={page}"
            print(f'    Парсинг страницы {page}: {url}')

            random_wait = random.uniform(3, 5)
            time.sleep(random_wait)

            try:
                driver.get(url)
                time.sleep(10)
            except Exception as e:
                print(f'    Ошибка при загрузке страницы {url}: {e}')
                break

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles = soup.find_all(self.article_tag)

            new_items = []
            for article in articles:
                try:
                    link_tag = article.find('a')
                    link = link_tag['href'] if link_tag and link_tag.get('href') else None
                    if not link:
                        continue

                    desc_elem = article.select_one(self.description_selector)
                    description = desc_elem.text.strip() if desc_elem else ""

                    price_elem = article.select_one(self.price_selector)
                    price = price_elem.text.strip() if price_elem else "Нет цены"

                    full_link = f"{self.base_url}{link}" if link.startswith('/') else link

                    if full_link not in seen_links:
                        seen_links.add(full_link)
                        new_items.append({
                            'link': full_link,
                            'description': description,
                            'price': price,
                            'store': self.name
                        })

                except Exception:
                    continue

            if not new_items:
                print(f'    Больше нет новых товаров на странице {page}. Прекращаю.')
                break

            print(f'    Найдено {len(new_items)} новых товаров на странице {page}.')
            all_items.extend(new_items)
            page += 1

        print(f'    Завершено. Всего собрано {len(all_items)} уникальных товаров.')
        return all_items

    def get_category_prompt_hints(self) -> str:
        return """
        """