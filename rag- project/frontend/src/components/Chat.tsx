import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchConversation, sendQuestion } from '../services/api';
import './Chat.css';

interface Message {
  id: string;
  content: string;
  is_user: boolean;
  timestamp: string;
}

const Chat: React.FC = () => {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<string[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 加载对话历史
  useEffect(() => {
    if (conversationId && token) {
      loadConversation();
    } else {
      setMessages([]);
    }
  }, [conversationId, token]);
  
  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const loadConversation = async () => {
    try {
      setLoading(true);
      const data = await fetchConversation(conversationId!, token!);
      setMessages(data);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSendQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) return;
    
    try {
      setLoading(true);
      
      // 立即添加用户消息到界面
      const userMessage: Message = {
        id: Date.now().toString(),
        content: question,
        is_user: true,
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, userMessage]);
      const questionText = question;
      setQuestion('');
      
      // 发送到API
      const response = await sendQuestion(
        questionText, 
        token!, 
        conversationId
      );
      
      // 添加AI回复
      const aiMessage: Message = {
        id: Date.now().toString() + '-ai',
        content: response.answer,
        is_user: false,
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, aiMessage]);
      setSources(response.sources || []);
      
      // 如果是新对话，导航到新的对话URL
      if (!conversationId && response.conversation_id) {
        navigate(`/chat/${response.conversation_id}`, { replace: true });
      }
    } catch (error) {
      console.error('Failed to send question:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };
  
  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.length === 0 && !loading ? (
          <div className="empty-state">
            <p>开始一个新的对话！提问任何与您文档相关的问题。</p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`message ${message.is_user ? 'user-message' : 'ai-message'}`}
              >
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-author">{message.is_user ? '您' : 'AI助手'}</span>
                    <span className="message-time">{formatTimestamp(message.timestamp)}</span>
                  </div>
                  <div className="message-text">{message.content}</div>
                </div>
              </div>
            ))}
            
            {sources.length > 0 && (
              <div className="sources-container">
                <h4>参考来源:</h4>
                <ul>
                  {sources.map((source, index) => (
                    <li key={index}>{source}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
        
        {loading && <div className="loading">思考中...</div>}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="question-form" onSubmit={handleSendQuestion}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入您的问题..."
          disabled={loading}
          rows={3}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          发送
        </button>
      </form>
    </div>
  );
};

export default Chat; 