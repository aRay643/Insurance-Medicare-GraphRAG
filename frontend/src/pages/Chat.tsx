import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatAPI, parseErrorMessage } from '../services/api';
import type { ChatMessage } from '../services/api';
import { useChatHistory } from '../hooks/useChatHistory';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// 错误消息组件
const ErrorMessage = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div style={{
    background: '#fff1f0',
    border: '1px solid #ffa39e',
    borderRadius: 8,
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8
  }}>
    <span style={{ fontSize: 18 }}>⚠️</span>
    <div style={{ flex: 1 }}>
      <div style={{ color: '#cf1322', marginBottom: 8 }}>
        {message}
      </div>
      <button
        onClick={onRetry}
        style={{
          background: '#fff',
          border: '1px solid #d9d9d9',
          borderRadius: 4,
          padding: '4px 12px',
          cursor: 'pointer',
          fontSize: 13
        }}
      >
        重新发送
      </button>
    </div>
  </div>
);

// Loading 动画组件 - 打字机风格
const TypingIndicator = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
    <span style={{ color: '#666', fontSize: 14 }}>AI 思考中</span>
    <div style={{ display: 'flex', gap: 2 }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#52c41a',
            animation: `bounce 1.4s ease-in-out ${i * 0.2}s infinite`
          }}
        />
      ))}
    </div>
    <style>{`
      @keyframes bounce {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-4px); }
      }
    `}</style>
  </div>
);

// 1. 全覆盖关系映射字典（已涵盖数据库所有关系词 + 容错变体）
const RELATION_MAP: Record<string, string> = {
  // ============ 保险产品相关 ============
  'BELONGS_TO_CATEGORY': '所属类别',
  'HAS_PAYOUT_LOGIC': '赔付逻辑',
  'HAS_TERM': '包含条款',
  'HAS TERM': '包含条款',           // 容错：防止后端漏掉下划线
  'COVERS': '保障范围',
  'HAS_EXCLUSION': '免责条款',
  'HAS_RIGHT': '享有权利',
  'ELIGIBILITY': '投保条件',
  'COVERED_BY': '可投保障',
  'COVERS_TREATMENT': '覆盖治疗',
  'COVERS_SERVICE': '覆盖服务',

  // ============ 养老机构相关 ============
  'LOCATED_IN': '位于',
  'BELONGS_TO': '属于',
  'PROVIDES_SERVICE': '提供服务',

  // ============ 药品相关 ============
  'HAS_TRADE_NAME': '药品商品名',
  'PRODUCED_BY': '生产商',
  'TREATS': '治疗',

  // ============ 其他常见关系（兜底） ============
  'SUITABLE_FOR': '适用人群',
  'RELATED_TO': '相关联',
  'IS_A': '属于',
  'PART_OF': '包含于',
};

// 2. 增强健壮性的数据解析函数
const parseTriple = (cite: any) => {
  let head = '', relation = '', tail = '', extra = '';

  // 提取原始数据
  if (cite && typeof cite === 'object' && !Array.isArray(cite)) {
    head = cite.head;
    relation = cite.relation;
    tail = cite.tail;
  } else if (Array.isArray(cite)) {
    head = cite[0];
    relation = cite[1];
    tail = cite[2];
    extra = cite[3] || '';
  } else {
    // 兜底：如果格式完全不认识，直接返回原字符串
    return { isRaw: true, content: String(cite) };
  }

  // 【核心修复点】：清洗关系字符串，消除不可见字符和大小写带来的匹配失败
  const cleanRelation = String(relation)
    .trim()          // 去除首尾可能存在的空格
    .toUpperCase(); // 统一转为大写以匹配字典

  // 查找字典，如果字典里没有，则作为最后的兜底显示清洗后的原词
  const finalRelation = RELATION_MAP[cleanRelation] || relation;

  return {
    isRaw: false,
    head: String(head).trim(),
    relation: finalRelation,
    tail: String(tail).trim(),
    extra: extra ? String(extra).trim() : ''
  };
};

export default function Chat() {
  const {
    sessions,
    currentSessionId,
    getCurrentMessages,
    updateCurrentMessages,
    createSession,
    deleteSession,
    clearAllHistory,
    switchSession,
    isLoaded
  } = useChatHistory();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string>('');
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const username = localStorage.getItem('username') || '用户';

  // 从 hook 加载消息（仅在切换会话时触发）
  useEffect(() => {
    if (isLoaded && currentSessionId) {
      const loadedMessages = getCurrentMessages();
      // 使用函数式更新避免依赖 messages
      setMessages(() => [...loadedMessages]);
    }
  }, [isLoaded, currentSessionId]);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 保存消息到历史（仅当消息真正改变时）
  useEffect(() => {
    if (isLoaded && currentSessionId && messages.length > 0) {
      updateCurrentMessages([...messages]);
    }
  }, [isLoaded, currentSessionId, messages, updateCurrentMessages]);

  const handleSend = async (questionText?: string) => {
    const text = questionText || input.trim();
    if (!text || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text
    };

    if (!questionText) {
      setMessages(prev => [...prev, userMessage]);
      setInput('');
    }

    setLastQuestion(text);
    setLoading(true);

    try {
      const response = await chatAPI.ask(text);
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error("请求失败:", parseErrorMessage(error));
      const errorMsg = parseErrorMessage(error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorMsg,
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastQuestion) {
      handleSend(lastQuestion);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('username');
    navigate('/');
  };

  const handleNewChat = () => {
    createSession();
  };

  const handleClearHistory = () => {
    if (confirm('确定要清空所有对话历史吗？')) {
      clearAllHistory();
    }
  };

  // 格式化时间
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  if (!isLoaded) {
    return <div style={{ padding: 20 }}>加载中...</div>;
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '12px 24px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => setSidebarVisible(!sidebarVisible)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 18,
              padding: 4
            }}
          >
            ☰
          </button>
          <span style={{ fontSize: 18, fontWeight: 'bold' }}>医保健康管理问答系统</span>
        </div>
        <div>
          <span>欢迎，{username}</span>
          <button onClick={handleLogout} style={{ marginLeft: 16 }}>退出</button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Sidebar */}
        {sidebarVisible && (
          <div style={{
            width: 260,
            background: '#f7f7f7',
            borderRight: '1px solid #e8e8e8',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* New Chat Button */}
            <div style={{ padding: 12 }}>
              <button
                onClick={handleNewChat}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  background: '#1890ff',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 14,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8
                }}
              >
                <span>+</span> 新建对话
              </button>
            </div>

            {/* Session List */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              <div style={{
                padding: '8px 12px',
                fontSize: 12,
                color: '#999'
              }}>
                历史会话
              </div>
              {sessions.map(session => (
                <div
                  key={session.id}
                  onClick={() => switchSession(session.id)}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    background: session.id === currentSessionId ? '#e6f7ff' : 'transparent',
                    borderLeft: session.id === currentSessionId ? '3px solid #1890ff' : '3px solid transparent',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'background 0.2s'
                  }}
                >
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{
                      fontSize: 14,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {session.title}
                    </div>
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                      {formatTime(session.createdAt)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm('确定删除这个会话吗？')) {
                        deleteSession(session.id);
                      }
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#999',
                      cursor: 'pointer',
                      padding: '4px 8px',
                      fontSize: 12
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            {/* Clear History */}
            <div style={{ padding: 12, borderTop: '1px solid #e8e8e8' }}>
              <button
                onClick={handleClearHistory}
                style={{
                  width: '100%',
                  padding: '8px 16px',
                  background: '#fff',
                  color: '#ff4d4f',
                  border: '1px solid #ff4d4f',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 13
                }}
              >
                清空对话
              </button>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Messages */}
          <div style={{ flex: 1, overflow: 'auto', padding: 24, background: '#f5f5f5' }}>
            {messages.map((item) => (
              <div key={item.id} style={{
                display: 'flex',
                justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 16
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  maxWidth: '70%'
                }}>
                  {!item.isError && (
                    <div style={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      background: item.role === 'user' ? '#1890ff' : '#52c41a',
                      color: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginLeft: item.role === 'user' ? 8 : 0,
                      marginRight: item.role === 'user' ? 0 : 8,
                      flexShrink: 0
                    }}>
                      {item.role === 'user' ? 'U' : 'AI'}
                    </div>
                  )}
                  <div style={{ flex: 1 }}>
                    {item.isError ? (
                      <ErrorMessage message={item.content} onRetry={handleRetry} />
                    ) : (
                      <div style={{
                        background: '#fff',
                        padding: '12px 16px',
                        borderRadius: 8,
                        boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                        lineHeight: '1.6',
                        whiteSpace: item.role === 'user' ? 'pre-wrap' : 'normal',
                        wordBreak: 'break-word'
                      }}>
                        {item.role === 'assistant' ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({node, ...props}) => <p style={{ margin: '0 0 10px 0' }} {...props} />,
                              ul: ({node, ...props}) => <ul style={{ margin: '0 0 10px 0', paddingLeft: '20px' }} {...props} />,
                              ol: ({node, ...props}) => <ol style={{ margin: '0 0 10px 0', paddingLeft: '20px' }} {...props} />,
                            }}
                          >
                            {item.content}
                          </ReactMarkdown>
                        ) : (
                          item.content
                        )}
                      </div>
                    )}
                    {/* 证据展示部分 - 仅 AI 消息显示 */}
                    {item.role === 'assistant' && item.citations && item.citations.length > 0 && !item.isError && (
                      <div style={{ marginTop: 12 }}>
                        {/* 优化后的切换按钮 */}
                        <div
                          onClick={() => setExpandedEvidence(expandedEvidence === item.id ? null : item.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            color: '#1890ff',
                            fontSize: 13,
                            cursor: 'pointer',
                            userSelect: 'none',
                            padding: '4px 0'
                          }}
                        >
                          <span style={{
                            transform: expandedEvidence === item.id ? 'rotate(90deg)' : 'rotate(0deg)',
                            transition: 'transform 0.2s'
                          }}>
                            ▶
                          </span>
                          <span>{expandedEvidence === item.id ? '收起溯源证据' : '查看溯源证据'}</span>
                          <span style={{ color: '#8c8c8c', fontSize: 12 }}>(知识图谱)</span>
                        </div>

                        {/* 优化后的图谱展示区 */}
                        {expandedEvidence === item.id && (
                          <div style={{
                            marginTop: 8,
                            padding: '12px 16px',
                            background: '#fafafa',
                            border: '1px solid #f0f0f0',
                            borderRadius: 8,
                            fontSize: 13
                          }}>
                            <div style={{ fontWeight: 500, marginBottom: 12, color: '#595959' }}>
                              <span style={{ marginRight: 6 }}>📊</span>
                              提取的关键信息路径：
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                              {item.citations.map((cite, idx) => {
                                const parsed = parseTriple(cite);

                                // 非标准格式的兜底渲染
                                if (parsed.isRaw) {
                                  return (
                                    <div key={idx} style={{ color: '#595959', fontFamily: 'monospace' }}>
                                      {parsed.content}
                                    </div>
                                  );
                                }

                                // 标准三元组的美化渲染
                                return (
                                  <div key={idx} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    flexWrap: 'wrap',
                                    gap: 8,
                                    lineHeight: '1.5'
                                  }}>
                                    {/* 头实体 */}
                                    <span style={{
                                      color: '#262626',
                                      fontWeight: 500,
                                      background: '#fff',
                                      padding: '2px 8px',
                                      borderRadius: 4,
                                      border: '1px solid #d9d9d9'
                                    }}>
                                      {parsed.head}
                                    </span>

                                    {/* 关系标签 (Tag) */}
                                    <span style={{
                                      fontSize: 12,
                                      color: '#096dd9',
                                      background: '#e6f7ff',
                                      border: '1px solid #91d5ff',
                                      padding: '1px 8px',
                                      borderRadius: 12
                                    }}>
                                      {parsed.relation}
                                    </span>

                                    {/* 尾实体 */}
                                    <span style={{ color: '#595959' }}>
                                      {parsed.tail}
                                      {parsed.extra && (
                                        <span style={{ color: '#8c8c8c', marginLeft: 4 }}>
                                          ({parsed.extra})
                                        </span>
                                      )}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-start',
                marginBottom: 16
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', maxWidth: '70%' }}>
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    background: '#52c41a',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 8,
                    flexShrink: 0
                  }}>
                    AI
                  </div>
                  <div style={{
                    background: '#fff',
                    padding: '12px 16px',
                    borderRadius: 8,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                  }}>
                    <TypingIndicator />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={{ padding: 16, background: '#fff', borderTop: '1px solid #f0f0f0', display: 'flex', gap: 8 }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (!e.shiftKey && e.key === 'Enter') {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="请输入您的问题..."
              disabled={loading}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 4,
                border: '1px solid #d9d9d9',
                resize: 'none',
                minHeight: 36,
                fontFamily: 'inherit'
              }}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              style={{
                padding: '4px 16px',
                background: loading || !input.trim() ? '#d9d9d9' : '#1890ff',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer'
              }}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
