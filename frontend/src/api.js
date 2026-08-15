const BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    // Auth is a cross-site session cookie (frontend and backend live on
    // different domains in production) - fetch does not send cookies
    // cross-origin by default, so this is required on every call.
    credentials: 'include',
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || `Request failed: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  signup: (email, password) =>
    request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) }),

  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  me: () => request('/auth/me'),

  getAnalyticsSummary: () => request('/analytics/summary'),

  getSubscriptions: (status) => request(`/subscriptions${status ? `?status=${status}` : ''}`),

  updateSubscription: (id, updates) =>
    request(`/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(updates) }),

  getInsights: () => request('/insights'),

  generateInsights: () => request('/insights/generate', { method: 'POST' }),

  uploadTransactions: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/transactions/upload', { method: 'POST', body: form });
  },
};
