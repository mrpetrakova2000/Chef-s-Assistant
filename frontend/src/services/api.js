const API_BASE_URL = process.env.REACT_APP_API_URL || '';

export const sendQuery = async (question) => {
  // 1. Создаём задачу
  const createResponse = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!createResponse.ok) {
    throw new Error(`Failed to create task: ${createResponse.status}`);
  }

  const { task_id } = await createResponse.json();

  // 2. Ждём результат (опрашиваем)
  let attempts = 0;
  const maxAttempts = 12000; // 2 минуты

  while (attempts < maxAttempts) {
    const statusResponse = await fetch(`${API_BASE_URL}/task/${task_id}`);

    if (!statusResponse.ok) {
      throw new Error(`Failed to get task status: ${statusResponse.status}`);
    }

    const taskData = await statusResponse.json();

    if (taskData.status === 'completed') {
      // 3. Удаляем задачу
      await fetch(`${API_BASE_URL}/task/${task_id}`, { method: 'DELETE' });
      return taskData.result;
    }

    if (taskData.status === 'failed') {
      await fetch(`${API_BASE_URL}/task/${task_id}`, { method: 'DELETE' });
      throw new Error(taskData.error || 'Task failed');
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
    attempts++;
  }

  throw new Error('Request timeout');
};

export const getStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/status`);
  return response.json();
};