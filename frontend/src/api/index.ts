import axios from 'axios';

// 生产环境和开发环境的API配置
const isDevelopment = import.meta.env.DEV;
const api = axios.create({
  baseURL: isDevelopment ? 'http://localhost:8001' : '',
  timeout: 30000,
});

// 请求拦截器：添加 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：处理 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// 认证相关
export const authApi = {
  login: (data: { username: string; password: string }) => api.post('/auth/login', data),
  register: (data: { username: string; password: string }) => api.post('/auth/register', data),
  logout: (token: string) => api.post('/auth/logout', { token }),
  verify: (token: string) => api.get(`/auth/verify?token=${token}`),
  checkInit: () => api.get('/auth/check-init'),
};

// 账号相关
export const accountApi = {
  list: () => api.get('/accounts/'),
  create: (data: { username: string; api_key: string }) => api.post('/accounts/', data),
  get: (id: number) => api.get(`/accounts/${id}`),
  refresh: (id: number) => api.post(`/accounts/${id}/refresh`),
  delete: (id: number) => api.delete(`/accounts/${id}`),
};

// 种子相关
export const torrentApi = {
  search: (params: {
    account_id: number;
    page?: number;
    page_size?: number;
    mode?: string;
    keyword?: string;
    discount?: string;
    min_size_gb?: number;
    max_size_gb?: number;
    min_seeders?: number;
  }) => api.post('/torrents/search', params),
  getDetail: (id: string, accountId: number) => 
    api.get(`/torrents/${id}?account_id=${accountId}`),
  getDownloadUrl: (id: string, accountId: number) =>
    api.get(`/torrents/${id}/download-url?account_id=${accountId}`),
  download: (id: string, accountId: number) =>
    api.post(`/torrents/${id}/download?account_id=${accountId}`, {}, { responseType: 'blob' }),
};

// 规则相关
export const ruleApi = {
  list: (accountId?: number) => api.get('/rules/', { params: { account_id: accountId } }),
  create: (data: any) => api.post('/rules/', data),
  get: (id: number) => api.get(`/rules/${id}`),
  update: (id: number, data: any) => api.put(`/rules/${id}`, data),
  delete: (id: number) => api.delete(`/rules/${id}`),
  toggle: (id: number) => api.post(`/rules/${id}/toggle`),
};

// 下载器相关
export const downloaderApi = {
  list: () => api.get('/downloaders/'),
  create: (data: any) => api.post('/downloaders/', data),
  test: (id: number) => api.post(`/downloaders/${id}/test`),
  delete: (id: number) => api.delete(`/downloaders/${id}`),
  getTags: (id: number) => api.get(`/downloaders/${id}/tags`),
};

// 历史相关
export const historyApi = {
  list: (params?: { account_id?: number; page?: number; page_size?: number }) =>
    api.get('/history/', { params }),
  delete: (id: number) => api.delete(`/history/${id}`),
  clear: (accountId?: number) => api.delete('/history/', { params: { account_id: accountId } }),
  syncStatus: () => api.post('/history/sync-status'),
  getStatusMapping: () => api.get('/history/status-mapping'),
  uploadTorrent: (formData: FormData) => api.post('/history/upload-torrent', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getDownloaderTags: (downloaderId: number) => api.get(`/history/downloader-tags/${downloaderId}`),
};

// 设置相关
export const settingsApi = {
  getAutoDelete: () => api.get('/settings/auto-delete'),
  updateAutoDelete: (data: {
    enabled: boolean;
    delete_scope: 'all' | 'normal' | 'adult';
    check_tags: boolean;
  }) => api.put('/settings/auto-delete', data),
  
  // 刷新间隔设置
  getRefreshIntervals: () => api.get('/settings/refresh-intervals'),
  updateRefreshIntervals: (data: {
    account_refresh_interval: number;
    torrent_check_interval: number;
    expired_check_interval: number;
  }) => api.put('/settings/refresh-intervals', data),
  
  // 调度器管理
  getSchedulerStatus: () => api.get('/settings/scheduler-status'),
  restartScheduler: () => api.post('/settings/restart-scheduler'),
  
  getAllSettings: () => api.get('/settings/'),
  getSetting: (key: string) => api.get(`/settings/${key}`),
  updateSetting: (key: string, data: { value: any; description?: string }) => 
    api.put(`/settings/${key}`, data),
  deleteSetting: (key: string) => api.delete(`/settings/${key}`),
};

// 仪表盘相关
export const dashboardApi = {
  getDashboardData: () => api.get('/dashboard/'),
  getAccountStats: (accountId: number) => api.get(`/dashboard/accounts/${accountId}/stats`),
};

export default api;
