import axios from 'axios';

const API_BASE_URL = '/api/v1';

// Mock 数据 - 用于后端未就绪时的兜底
const MOCK_RESPONSE = {
  answer: "（Mock数据）根据知识图谱检索，70岁高血压患者可以购买特定的防癌险，但需要注意免责条款中对既往症的限制。建议在投保时如实告知病情，等待期后可获得理赔。",
  citations: [
    ["高血压", "在健康告知中被要求如实告知", "护理险", "投保规则"],
    ["高血压", "通常作为除外责任", "医疗险", "理赔条款"],
    ["癌症", "等待期通常为", "90天", "投保规则"],
    ["护理险", "最高投保年龄", "65岁", "投保规则"],
  ],
  confidence: "高"
};

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[][];
  confidence?: string;
}

export const chatAPI = {
  ask: async (question: string): Promise<{
    answer: string;
    citations: string[][];
    confidence: string;
  }> => {
    try {
      // 设置请求超时（10秒）
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        question,
        hop: 2,
        limit: 20,
      }, {
        timeout: 10000
      });
      return response.data;
    } catch (error) {
      console.warn("API 请求失败，使用 Mock 数据兜底:", error);
      // 请求失败时返回 Mock 数据
      return MOCK_RESPONSE;
    }
  },

  health: async () => {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};
