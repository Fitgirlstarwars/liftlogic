/**
 * API Service - Centralized API client for LiftLogic backend.
 */
/// <reference types="vite/client" />

import axios, { AxiosInstance } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth tokens
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Search API - routes: /api/search
export const searchApi = {
  search: async (query: string, options?: { limit?: number; useRag?: boolean }) => {
    const { data } = await api.post('/api/search', {
      query,
      limit: options?.limit,
      use_rag: options?.useRag ?? false,
    });
    return data;
  },

  rag: async (query: string) => {
    const { data } = await api.post('/api/search', { query, use_rag: true });
    return data;
  },

  getFaultCode: async (code: string, manufacturer?: string) => {
    const { data } = await api.get(`/api/search/fault/${code}`, {
      params: { manufacturer },
    });
    return data;
  },
};

// Extraction API - routes: /api/extraction
export const extractionApi = {
  extractPdf: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/api/extraction/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  getStatus: async (jobId: string) => {
    const { data } = await api.get(`/api/extraction/status/${jobId}`);
    return data;
  },
};

// Diagnosis API - routes: /api/diagnosis
export const diagnosisApi = {
  diagnose: async (faultCode: string, options?: { manufacturer?: string; symptoms?: string[] }) => {
    const { data } = await api.post('/api/diagnosis/diagnose', {
      fault_code: faultCode,
      manufacturer: options?.manufacturer,
      symptoms: options?.symptoms,
    });
    return data;
  },

  safetyAnalysis: async (documentId: number) => {
    const { data } = await api.post('/api/diagnosis/analyze/safety', null, {
      params: { document_id: documentId },
    });
    return data;
  },

  maintenanceAnalysis: async (documentId: number) => {
    const { data } = await api.post('/api/diagnosis/analyze/maintenance', null, {
      params: { document_id: documentId },
    });
    return data;
  },
};

// Health API - route: /health (no /api prefix)
export const healthApi = {
  check: async () => {
    const { data } = await api.get('/health');
    return data;
  },
};

export default api;
