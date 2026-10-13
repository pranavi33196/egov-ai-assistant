import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

// CHANGED: one configurable backend URL (set VITE_API_URL in frontend/.env for deployment)
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
});

// ── Session handling ────────────────────────────────────────
const AUTH_FLOW_PATHS = [
  '/auth/login', '/auth/register', '/auth/verify-otp', '/auth/resend-otp',
  '/auth/forgot-password', '/auth/reset-password', '/auth/demo-login',
];

const isAuthFlow = (url = '') => AUTH_FLOW_PATHS.some((p) => url.startsWith(p));

const isTokenExpired = (token) => {
  try {
    const { exp } = jwtDecode(token);
    return typeof exp === 'number' && exp * 1000 <= Date.now();
  } catch {
    return true; // unreadable token = treat as expired
  }
};

const endSession = () => {
  localStorage.removeItem('token');
  if (window.location.pathname !== '/login') {
    window.location.assign('/login?error=session_expired');
  }
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    // CHANGED: stop sending expired tokens. Without this, /query silently treats an expired
    // user as anonymous and the conversation is no longer saved.
    if (!isAuthFlow(config.url) && isTokenExpired(token)) {
      endSession();
      return Promise.reject(new axios.CanceledError('Session expired'));
    }
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    // CHANGED: a 401 on a protected call (not on the login forms themselves) ends the session.
    if (error.response?.status === 401 && localStorage.getItem('token') && !isAuthFlow(error.config?.url)) {
      endSession();
    }
    return Promise.reject(error);
  }
);

export const auth = {
  register: async (payload) => (await api.post('/auth/register', payload)).data,
  verifyOTP: async (payload) => (await api.post('/auth/verify-otp', payload)).data,
  resendOTP: async (payload) => (await api.post('/auth/resend-otp', payload)).data,
  login: async (email, password, captcha_token = null) =>
    (await api.post('/auth/login', { email, password, captcha_token })).data,
  verify2FA: async (email, otp) => (await api.post('/auth/login/verify-2fa', { email, otp })).data,
  forgotPassword: async (email, captcha_token = null) =>
    (await api.post('/auth/forgot-password', { email, captcha_token })).data,
  resetPassword: async (email, otp, new_password) =>
    (await api.post('/auth/reset-password', { email, otp, new_password })).data,
  demoLogin: async () => (await api.post('/auth/demo-login')).data,
  getMe: async () => (await api.get('/auth/me')).data,
  updateProfile: async (payload) => (await api.put('/auth/profile', payload)).data,
};

export const conversations = {
  list: async () => (await api.get('/conversations')).data,
  create: async (title = 'New Conversation', language = 'en') =>
    (await api.post('/conversations', { title, language })).data,
  getMessages: async (conversationId) =>
    (await api.get(`/conversations/${conversationId}/messages`)).data,
  rename: async (conversationId, title) =>
    (await api.put(`/conversations/${conversationId}/rename`, { title })).data,
  delete: async (conversationId) => (await api.delete(`/conversations/${conversationId}`)).data,
};

export const query = {
  ask: async (question, language = 'en', conversation_id = null) =>
    (await api.post('/query', { question, language, conversation_id })).data,
};

export const system = {
  health: async () => (await api.get('/health')).data,
  status: async () => (await api.get('/system/status')).data,
};

// NEW: text-to-speech via POST (text in body, so long Telugu/Hindi answers work).
// Returns an object URL you can pass to `new Audio(url)`; call URL.revokeObjectURL(url) when done.
export const tts = {
  fetchAudioUrl: async (text, lang = 'en') => {
    const res = await api.post('/tts/speak', { text, lang }, { responseType: 'blob', timeout: 30000 });
    return URL.createObjectURL(res.data);
  },
};

export default api;
