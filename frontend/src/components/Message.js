import React from 'react';
import './Message.css';
import ReactMarkdown from 'react-markdown';
import { FaUser, FaUtensils } from 'react-icons/fa';
import RecipeCard from './RecipeCard';

function Message({ message }) {
  const isUser = message.type === 'user';
  const hasRecipeData = message.data && message.data.ingredients !== undefined;
  const isEmptyRecipe = hasRecipeData && message.data.ingredients.length === 0;

  return (
    <div className={`message ${isUser ? 'user' : 'bot'}`}>
      <div className="message-avatar">
        {isUser ? <FaUser /> : <FaUtensils />}
      </div>
      <div className="message-content">
        {hasRecipeData ? (
          <RecipeCard data={message.data} />
        ) : (
          <ReactMarkdown
            components={{
              a: ({ node, ...props }) => (
                <a target="_blank" rel="noopener noreferrer" {...props} />
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
        {message.data && !isEmptyRecipe && (
          <div className="message-meta">
            <span className="elapsed-time">
              ⏱️ {message.data.elapsed_seconds} сек
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default Message;