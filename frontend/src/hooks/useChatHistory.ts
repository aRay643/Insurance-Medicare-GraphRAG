import { useState, useEffect, useCallback } from 'react';
import type { ChatMessage } from '../services/api';

// 根据用户名生成不同的存储 key
const getStorageKey = (username: string) => `chat_history_${username}`;

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [isLoaded, setIsLoaded] = useState(false);

  const username = localStorage.getItem('username') || 'guest';
  const storageKey = getStorageKey(username);

  // 从 localStorage 加载历史
  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setSessions(parsed.sessions || []);
        setCurrentSessionId(parsed.currentSessionId || '');
      } catch (e) {
        console.error('Failed to load chat history:', e);
      }
    }
    setIsLoaded(true);
  }, [storageKey]);

  // 保存到 localStorage
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(storageKey, JSON.stringify({ sessions, currentSessionId }));
    }
  }, [sessions, currentSessionId, isLoaded, storageKey]);

  // 创建新会话
  const createSession = useCallback(() => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [{
        id: '1',
        role: 'assistant',
        content: '您好！我是医保健康管理助手，请问有什么可以帮您？'
      }],
      createdAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    return newSession.id;
  }, []);

  // 获取当前会话的消息（返回副本）
  const getCurrentMessages = useCallback((): ChatMessage[] => {
    const session = sessions.find(s => s.id === currentSessionId);
    return session ? [...session.messages] : [];
  }, [sessions, currentSessionId]);

  // 更新当前会话消息
  const updateCurrentMessages = useCallback((messages: ChatMessage[]) => {
    setSessions(prev => prev.map(s => {
      if (s.id === currentSessionId) {
        // 更新标题为第一个用户消息
        const userMsg = messages.find(m => m.role === 'user');
        const title = userMsg ? userMsg.content.slice(0, 20) + (userMsg.content.length > 20 ? '...' : '') : s.title;
        return { ...s, messages, title };
      }
      return s;
    }));
  }, [currentSessionId]);

  // 删除会话
  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    if (currentSessionId === sessionId) {
      const remaining = sessions.filter(s => s.id !== sessionId);
      setCurrentSessionId(remaining[0]?.id || '');
    }
  }, [currentSessionId, sessions]);

  // 清空所有历史
  const clearAllHistory = useCallback(() => {
    setSessions([]);
    setCurrentSessionId('');
    // 自动创建一个新会话
    setTimeout(() => createSession(), 0);
  }, [createSession]);

  // 切换会话
  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
  }, []);

  // 初始化：如果没有会话，创建一个
  useEffect(() => {
    if (isLoaded && sessions.length === 0) {
      createSession();
    } else if (isLoaded && !currentSessionId && sessions.length > 0) {
      setCurrentSessionId(sessions[0].id);
    }
  }, [isLoaded, sessions.length, currentSessionId, createSession]);

  return {
    sessions,
    currentSessionId,
    getCurrentMessages,
    updateCurrentMessages,
    createSession,
    deleteSession,
    clearAllHistory,
    switchSession,
    isLoaded
  };
}
