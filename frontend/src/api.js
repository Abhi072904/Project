const BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
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
