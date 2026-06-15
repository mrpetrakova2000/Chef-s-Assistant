"""Magnit store implementation"""
import time
import random
from typing import Dict, List
from bs4 import BeautifulSoup
from .base import BaseStore


class MagnitStore(BaseStore):
    """Magnit store parser"""

    def __init__(self):
        super().__init__("magnit.ru", "https://magnit.ru")
        self.article_tag = "article"
        self.description_selector = "div.product-card__title"
        self.price_selector = "div.product-card__price"

        self.category_container = "div.header-catalog-items"
        self.category_selector = "a.header-catalog-item__subitem"

        self.forbidden_categories = [
            'Стоит попробовать', 'Промокод', 'Покупайте с выгодой',
            'Акции', 'Скидки'
        ]
        self.shop_code = "783094"

    def get_categories(self, driver) -> Dict[str, str]:
        """
        Получает список категорий из header-catalog Магнита.
        Берем подкатегории (header-catalog-item__subitem) - это конечные категории!
        """
        driver.get(self.base_url)
        time.sleep(3)

        # Открываем каталог
        try:
            catalog_btn = driver.find_element("css selector", "[data-test-id='header-catalog-button']")
            if catalog_btn:
                catalog_btn.click()
                time.sleep(2)
        except:
            pass  # Если нет кнопки - пробуем и так

        soup = BeautifulSoup(driver.page_source, "html.parser")

        categories = {}

        # Ищем контейнер с категориями
        container = soup.select_one(self.category_container)
        if container:
            # Ищем все подкатегории
            for link in container.select(self.category_selector):
                if link and link.get('href'):
                    cat_name = link.text.strip()
                    cat_url = link['href']

                    if cat_name and cat_url:
                        forbidden = False
                        for fb in self.forbidden_categories:
                            if fb.lower() in cat_name.lower():
                                forbidden = True
                                break

                        if not forbidden:
                            categories[cat_name] = cat_url

        # Если не нашли через header - пробуем старый способ
        if not categories:
            print(f"    [Magnit] Категории не найдены в header, пробуем /catalog...")
            categories_url = f"{self.base_url}/catalog?shopCode={self.shop_code}&shopType=1"
            driver.get(categories_url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "html.parser")

            for link in soup.select("a.filters-category__item"):
                if link and link.get('href'):
                    cat_name = link.text.strip()
                    cat_url = link['href']
                    if cat_name and cat_url:
                        categories[cat_name] = cat_url

        print(f"    [Magnit] Найдено {len(categories)} категорий")
        if categories:
            sample = list(categories.keys())[:5]
            print(f"    [Magnit] Примеры: {', '.join(sample)}")

        return categories

    def parse_category(self, driver, category_url: str) -> List[Dict]:
        """
        Парсит товары из категории Магнит
        """
        all_items = []
        page = 1
        seen_links = set()

        # Формируем полный URL
        if category_url.startswith('/'):
            full_category_url = f"{self.base_url}{category_url}"
        elif category_url.startswith('http'):
            full_category_url = category_url
        else:
            full_category_url = f"{self.base_url}/{category_url}"

        # Добавляем shopCode
        if '?shopCode=' not in full_category_url:
            if '?' in full_category_url:
                full_category_url = f"{full_category_url}&shopCode={self.shop_code}&shopType=1"
            else:
                full_category_url = f"{full_category_url}?shopCode={self.shop_code}&shopType=1"

        print(f'    [Magnit] Парсинг: {full_category_url[:100]}...')

        while True:
            if '?' in full_category_url:
                url = f"{full_category_url}&page={page}"
            else:
                url = f"{full_category_url}?page={page}"

            print(f'    [Magnit] Стр {page}...', end=' ')

            time.sleep(random.uniform(1, 2))

            try:
                driver.get(url)
                time.sleep(2)
            except Exception as e:
                print(f'Ошибка: {type(e).__name__}')
                break

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Ищем товары
            articles = soup.find_all('article')
            if not articles:
                articles = soup.select('[data-test-id="product-card"]')
            if not articles:
                articles = soup.find_all('div', class_=lambda c: c and 'product' in str(c))

            if not articles:
                print('нет товаров')
                break

            new_items = []
            for article in articles[:20]:
                try:
                    link_tag = article.find('a')
                    if not link_tag:
                        continue
                    link = link_tag.get('href')
                    if not link:
                        continue

                    desc_elem = (
                        article.find('div', class_=lambda c: c and ('title' in str(c) or 'name' in str(c))) or
                        article.find('span', class_=lambda c: c and ('title' in str(c) or 'name' in str(c)))
                    )
                    description = desc_elem.text.strip() if desc_elem else ""

                    price_elem = (
                        article.find('div', class_=lambda c: c and 'price' in str(c)) or
                        article.find('span', class_=lambda c: c and 'price' in str(c))
                    )
                    price = price_elem.text.strip() if price_elem else "Нет цены"

                    if link.startswith('/'):
                        full_link = f"{self.base_url}{link}"
                    elif link.startswith('http'):
                        full_link = link
                    else:
                        full_link = f"{self.base_url}/{link}"

                    if full_link not in seen_links and description:
                        seen_links.add(full_link)
                        new_items.append({
                            'link': full_link,
                            'description': description,
                            'price': price,
                            'store': self.name
                        })

                except Exception:
                    continue

            print(f'{len(new_items)} товаров')

            if not new_items:
                break

            all_items.extend(new_items)
            page += 1

        print(f'    [Magnit] Всего: {len(all_items)} товаров')
        return all_items

    def get_category_prompt_hints(self) -> str:
        return """
        """