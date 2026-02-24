import axios, { AxiosError } from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: (string[] | { head: string; relation: string; tail: string })[];
  confidence?: string;
  isError?: boolean;
}

// 解析后端返回的错误信息
function parseErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    // 后端返回的 HTTPException 错误
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    // 网络错误
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请稍后再试';
    }
    if (!axiosError.response) {
      return '无法连接到服务器，请检查后端服务是否启动';
    }
    return `请求失败 (${axiosError.response.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '未知错误，请稍后再试';
}

export const chatAPI = {
  ask: async (question: string): Promise<{
    answer: string;
    citations: (string[] | { head: string; relation: string; tail: string })[];
    confidence: string;
  }> => {
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      question,
      hop: 2,
      limit: 20,
    }, {
      timeout: 10000
    });
    return response.data;
  },

  health: async () => {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};

// 导出错误解析函数供组件使用
export { parseErrorMessage };
