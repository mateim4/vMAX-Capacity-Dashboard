import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for long-running collections
});

export const api = {
  // Status
  getStatus: async () => {
    const response = await axiosInstance.get('/api/status');
    return response.data;
  },

  // Trigger collection
  triggerCollection: async (forceRefresh = false) => {
    const response = await axiosInstance.post('/api/collect', { force_refresh: forceRefresh });
    return response.data;
  },

  // System capacity
  getSystemCapacity: async () => {
    const response = await axiosInstance.get('/api/system');
    return response.data;
  },

  // SRPs
  getSRPs: async () => {
    const response = await axiosInstance.get('/api/srps');
    return response.data;
  },

  // Storage Groups
  getStorageGroups: async (params?: { service_level?: string; srp_name?: string; limit?: number }) => {
    const response = await axiosInstance.get('/api/storage-groups', { params });
    return response.data;
  },

  // Volumes
  getVolumes: async (params?: { storage_group?: string; limit?: number; offset?: number }) => {
    const response = await axiosInstance.get('/api/volumes', { params });
    return response.data;
  },

  // Summary
  getSummary: async () => {
    const response = await axiosInstance.get('/api/summary');
    return response.data;
  },

  // Trends
  getServiceLevelBreakdown: async () => {
    const response = await axiosInstance.get('/api/trends/service-levels');
    return response.data;
  },

  getTopConsumers: async (limit = 10) => {
    const response = await axiosInstance.get(`/api/trends/top-consumers?limit=${limit}`);
    return response.data;
  },

  // Health
  health: async () => {
    const response = await axiosInstance.get('/api/health');
    return response.data;
  },
};
