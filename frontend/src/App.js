import React, { useState, useEffect } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import { FaDatabase, FaCheckCircle, FaUtensils } from 'react-icons/fa';
import { getStatus } from './services/api';

function App() {
  const [stats, setStats] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');

  const fetchStats = async () => {
    try {
      const data = await getStatus();
      setStats(data.stats);
      setBackendStatus('connected');
    } catch (error) {
      console.error('Не удалось получить статистику:', error);
      setBackendStatus('error');
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <FaUtensils className="logo-icon" />
            <h1>Chef's Assistant</h1>
            {backendStatus === 'error' && (
              <span className="backend-status error">⚠️ Нет связи с сервером</span>
            )}
            {backendStatus === 'checking' && (
              <span className="backend-status">🔄 Подключение...</span>
            )}
          </div>
          <div className="header-subtitle">
            Умный помощник для составления списка покупок
          </div>
        </div>
        {stats && (
          <div className="stats-bar">
            <div className="stat-item">
              <FaDatabase />
              <span>{stats.total_products || 0} товаров</span>
            </div>
            <div className="stat-item">
              <FaCheckCircle />
              <span>{((stats.success_rate || 0) * 100).toFixed(0)}% успешно</span>
            </div>
          </div>
        )}
      </header>

      <main className="app-main">
        {backendStatus === 'error' ? (
          <div className="error-banner">
            <p>⚠️ Не удалось подключиться к серверу. Убедитесь, что сервер запущен.</p>
            <button onClick={fetchStats}>🔄 Повторить</button>
          </div>
        ) : (
          <ChatInterface />
        )}
      </main>

      <footer className="app-footer">
        <p>Спросите любой рецепт и получите список покупок с ценами!</p>
      </footer>
    </div>
  );
}

export default App;