import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatAPI } from '../services/api';
import type { ChatMessage } from '../services/api';

const MOCK_GRAPH = [
  ["高血压", "在健康告知中被要求如实告知", "护理险", "投保规则"],
  ["高血压", "通常作为除外责任", "医疗险", "理赔条款"],
  ["癌症", "等待期通常为", "90天", "投保规则"],
  ["护理险", "最高投保年龄", "65岁", "投保规则"],
  ["意外险", "支持投保年龄可达", "80岁", "投保规则"],
  ["社区卫生中心", "提供", "上门护理服务", "养老服务"],
  ["阿尔兹海默症", "适合入住", "城市医养结合机构", "养老匹配"],
  ["城市养老机构", "支持", "异地结算", "医保政策"],
  ["高血压", "需要长期服用", "降压药", "医学常识"],
  ["骨折", "术后需要", "康复", "医学常识"]
];

// 格式化三元组显示
const formatTriple = (cite: any) => {
  // 如果是新数据的数组格式
  if (Array.isArray(cite)) {
    // 格式：(主体) -- [谓语] --> (客体) 【来源】
    return `(${cite[0]}) -- [${cite[1]}] --> (${cite[2]})` + (cite[3] ? ` 【${cite[3]}】` : '');
  }
  return String(cite);
};

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: '您好！我是医保健康管理助手，请问有什么可以帮您？'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const username = localStorage.getItem('username') || '用户';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatAPI.ask(userMessage.content);
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        // 成功时：优先用后端返回的，否则用 Mock
        citations: response.citations?.length ? response.citations : MOCK_GRAPH,
        confidence: response.confidence
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error("请求失败:", error); // 建议打印错误以便调试
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '抱歉，请检查后端服务是否启动，或稍后再试。',
        // 【修改点】在这里也加上 citations，这样报错时也能看到按钮（用于测试 UI）
        citations: MOCK_GRAPH 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('username');
    navigate('/');
  };

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
        <span style={{ fontSize: 18, fontWeight: 'bold' }}>医保健康管理问答系统</span>
        <div>
          <span>欢迎，{username}</span>
          <button onClick={handleLogout} style={{ marginLeft: 16 }}>退出</button>
        </div>
      </div>

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
              <div style={{ flex: 1 }}>
                <div style={{
                  background: '#fff',
                  padding: '12px 16px',
                  borderRadius: 8,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                }}>
                  {item.content}
                </div>
                {/* 证据展示部分 - 仅 AI 消息显示 */}
                {item.role === 'assistant' && item.citations && item.citations.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <button
                      onClick={() => setExpandedEvidence(expandedEvidence === item.id ? null : item.id)}
                      style={{
                        background: '#6c757d',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 4,
                        padding: '4px 12px',
                        fontSize: 13,
                        cursor: 'pointer'
                      }}
                    >
                      {expandedEvidence === item.id ? '收起证据' : '查看证据'} (Graph Evidence)
                    </button>
                    {expandedEvidence === item.id && (
                      <div style={{
                        marginTop: 8,
                        padding: 12,
                        background: '#f8f9fa',
                        border: '1px solid #e9ecef',
                        borderRadius: 6,
                        fontSize: 13
                      }}>
                        <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#495057' }}>
                          知识图谱提取的三元组：
                        </div>
                        {item.citations.map((cite, idx) => (
                          <div key={idx} style={{
                            fontFamily: 'monospace',
                            color: '#495057',
                            margin: '4px 0'
                          }}>
                            {formatTriple(cite)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            AI 思考中...
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
          disabled={loading}
          style={{
            padding: '4px 16px',
            background: '#1890ff',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          发送
        </button>
      </div>
    </div>
  );
}
