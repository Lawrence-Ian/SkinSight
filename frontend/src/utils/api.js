// src/utils/api.js
import axios from 'axios'

const getAPIUrl = () => {
  const storedUrl = typeof window !== 'undefined' ? localStorage.getItem('sk_api_url') : ''

  // Optional environment override for local or mobile builds.
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL
  // Runtime override for local testing.
  if (storedUrl) return storedUrl

  // Local development: use the same origin so Vite's dev proxy can forward /api requests.
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) return ''

  // Keep the browser on the local origin when no override is configured.
  return ''
}

const api = axios.create({ baseURL: getAPIUrl(), timeout: 120000 })

const isTransientNetworkError = (err) => {
  return err?.code === 'ECONNABORTED' || err?.message === 'Network Error' || !err?.response
}

const withRetry = async (requestFn, retries = 1) => {
  try {
    return await requestFn()
  } catch (err) {
    if (retries > 0 && isTransientNetworkError(err)) {
      await new Promise(resolve => setTimeout(resolve, 1500))
      return withRetry(requestFn, retries - 1)
    }
    throw err
  }
}

api.interceptors.request.use(cfg => {
  const t = localStorage.getItem('sk_token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})
api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401 && window.location.pathname !== '/auth') {
    sessionStorage.removeItem('sk_chat_session_id')
    localStorage.clear()
    window.location.href = '/auth'
  }
  if (err.message === 'Network Error' && !getAPIUrl()) { console.error('API URL not configured. Set VITE_API_URL environment variable.') }
  return Promise.reject(err)
})

export default api
export const authAPI     = {
  signup: d => withRetry(() => api.post('/api/auth/signup', d), 1),
  login: d => withRetry(() => api.post('/api/auth/login', d), 1),
  me: () => api.get('/api/auth/me'),
  updateProfile: d => api.patch('/api/auth/profile', d)
}
export const analysisAPI = { scanFrame: frame => api.post('/api/analysis/scan', { frame, source: 'live_camera' }) }
export const historyAPI  = { getAll: () => api.get('/api/history/'), get: id => api.get(`/api/history/${id}`), delete: id => api.delete(`/api/history/${id}`) }
export const chatAPI     = {
  message: (message, sessionId) => api.post('/api/chat/message', { message, session_id: sessionId }),
  listSessions: () => api.get('/api/chat/sessions'),
  getSession: id => api.get(`/api/chat/sessions/${id}`),
  deleteSession: id => api.delete(`/api/chat/sessions/${id}`)
}
export const routineAPI  = {
  getProgress: scanId => api.get(`/api/history/${scanId}/routine-progress`),
  saveProgress: (scanId, progress) => api.put(`/api/history/${scanId}/routine-progress`, progress)
}
export const locationsAPI = { 
  nearby: (lat, lng, radius = 100) => api.get('/api/locations/nearby', { params: { lat, lng, radius_km: radius } }),
  all: () => api.get('/api/locations/all')
}
