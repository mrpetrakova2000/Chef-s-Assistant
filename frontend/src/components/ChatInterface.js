import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';
import Message from './Message';
import LoadingDots from './LoadingDots';
import { FaPaperPlane, FaUtensils } from 'react-icons/fa';
import { sendQuery } from '../services/api';

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: "👋 Здравствуйте! Я Шеф-помощник. Скажите, что вы хотите приготовить, и я найду лучшие цены на все ингредиенты!\n\nПопробуйте: **\"Салат Цезарь на 4 порции\"** или **\"Борщ на 2 порции\"**",
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input.trim(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendQuery(input.trim());

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.markdown_text,
        data: response,
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: "❌ Извините, не удалось обработать запрос. Пожалуйста, попробуйте позже.",
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const suggestions = [
    "Салат Цезарь на 4 порции",
    "Борщ на 2 порции",
    "Оливье на 6 порций",
  ];

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="message-avatar">
              <FaUtensils />
            </div>
            <div className="message-content loading">
              <LoadingDots />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length <= 1 && !isLoading && (
        <div className="suggestions">
          <p>Попробуйте спросить:</p>
          <div className="suggestion-buttons">
            {suggestions.map((s, i) => (
              <button
                key={i}
                className="suggestion-btn"
                onClick={() => setInput(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Что вы хотите приготовить? (например, Салат Цезарь на 4 порции)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={1}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!input.trim() || isLoading}
        >
          <FaPaperPlane />
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;