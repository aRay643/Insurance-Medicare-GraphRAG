import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

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
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      question,
      hop: 2,
      limit: 20,
    });
    return response.data;
  },

  health: async () => {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};
