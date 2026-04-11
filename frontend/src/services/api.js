const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const sendQuery = async (question) => {
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Ошибка API:', response.status, errorText);
      throw new Error(`Ошибка HTTP! статус: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Ошибка вызова API:', error);
    throw error;
  }
};

export const getStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/status`);
    if (!response.ok) {
      throw new Error(`Ошибка HTTP! статус: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Не удалось получить статус:', error);
    throw error;
  }
};

export const clearCache = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/clear-cache`, {
      method: 'POST',
    });
    return await response.json();
  } catch (error) {
    console.error('Не удалось очистить кэш:', error);
    throw error;
  }
};