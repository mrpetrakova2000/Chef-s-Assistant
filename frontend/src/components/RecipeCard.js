import React from 'react';
import './RecipeCard.css';
import { FaCheckCircle, FaTimesCircle, FaExternalLinkAlt, FaDollarSign } from 'react-icons/fa';

function RecipeCard({ data }) {
  const { dish_name, portions, ingredients, total_price, success } = data;

  // Если ингредиентов нет - показываем сообщение
  if (!ingredients || ingredients.length === 0) {
    return (
      <div className="recipe-card empty-recipe">
        <div className="recipe-header">
          <h3>❌ Запрос не распознан</h3>
        </div>
        <div className="empty-message">
          <p>Извините, я могу помочь только с составлением списка покупок на основе рецептов.</p>
          <p className="try-again">Попробуйте спросить:</p>
          <ul>
            <li>🥗 "Салат Цезарь на 4 порции"</li>
            <li>🍲 "Борщ с говядиной на 2 порции"</li>
            <li>🥔 "Оливье на 6 персон"</li>
            <li>🍝 "Паста карбонара на 3 порции"</li>
          </ul>
        </div>
      </div>
    );
  }

  const foundIngredients = ingredients.filter(i => i.found);
  const notFoundIngredients = ingredients.filter(i => !i.found);

  return (
    <div className="recipe-card">
      <div className="recipe-header">
        <h3>🛒 {dish_name || 'Список покупок'}</h3>
        {portions && <span className="portions">{portions} порций</span>}
      </div>

      {foundIngredients.length > 0 && (
        <div className="ingredient-section">
          <h4>
            <FaCheckCircle className="icon-success" />
            Найдено ({foundIngredients.length})
          </h4>
          <div className="ingredient-list">
            {foundIngredients.map((item, index) => (
              <div key={index} className="ingredient-item found">
                <div className="ingredient-info">
                  <span className="ingredient-name">{item.name}</span>
                  <span className="ingredient-desc">{item.product_description}</span>
                </div>
                <div className="ingredient-price">
                  <span>{item.price}</span>
                  <span className="store-badge">{item.store}</span>
                </div>
                {item.link && (
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="product-link"
                  >
                    <FaExternalLinkAlt /> Открыть
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {notFoundIngredients.length > 0 && (
        <div className="ingredient-section">
          <h4>
            <FaTimesCircle className="icon-error" />
            Не найдено ({notFoundIngredients.length})
          </h4>
          <div className="ingredient-list">
            {notFoundIngredients.map((item, index) => (
              <div key={index} className="ingredient-item not-found">
                <span className="ingredient-name">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="recipe-footer">
        <div className="total-price">
          <FaDollarSign />
          <span>Итого: {total_price} ₽</span>
        </div>
        {!success && (
          <span className="error-badge">Частичные результаты</span>
        )}
      </div>
    </div>
  );
}

export default RecipeCard;