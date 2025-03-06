const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// 用户认证
export const loginUser = async (username: string, password: string) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await fetch(`${API_URL}/token`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('登录失败');
  }
  
  return response.json();
};

export const registerUser = async (username: string, password: string) => {
  const response = await fetch(`${API_URL}/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });
  
  if (!response.ok) {
    throw new Error('注册失败');
  }
  
  return response.json();
};

// 文档管理
export const fetchDocuments = async (token: string) => {
  const response = await fetch(`${API_URL}/documents`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('获取文档失败');
  }
  
  return response.json();
};

export const uploadDocument = async (file: File, token: string) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('上传文档失败');
  }
  
  return response.json();
};

// 对话管理
export const fetchConversations = async (token: string) => {
  const response = await fetch(`${API_URL}/conversations`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('获取对话失败');
  }
  
  return response.json();
};

export const fetchConversation = async (conversationId: string, token: string) => {
  const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('获取对话消息失败');
  }
  
  return response.json();
};

export const sendQuestion = async (query: string, token: string, conversationId?: string) => {
  const response = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      conversation_id: conversationId,
    }),
  });
  
  if (!response.ok) {
    throw new Error('发送问题失败');
  }
  
  return response.json();
}; 