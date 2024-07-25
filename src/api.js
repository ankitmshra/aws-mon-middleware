import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

// Function to refresh the token
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  try {
    const response = await axios.post(`${API_BASE_URL}/api/token/refresh/`, {
      refresh: refreshToken
    });
    localStorage.setItem('accessToken', response.data.access);
    return response.data.access;
  } catch (error) {
    throw error;
  }
};

// Request interceptor
api.interceptors.request.use(
  async (config) => {
    let token = localStorage.getItem('accessToken');
    
    if (token) {
      // Check if the token is expired
      const decodedToken = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Math.floor(Date.now() / 1000);
      
      if (decodedToken.exp < currentTime) {
        // Token is expired, try to refresh
        try {
          token = await refreshToken();
        } catch (error) {
          // Refresh failed, redirect to login
          window.location.href = '/login';
          return Promise.reject(error);
        }
      }
      
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is 401 and we haven't retried yet
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const token = await refreshToken();
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const login = async (username, password) => {
  try {
    const response = await api.post('/api/token/', { username, password });
    localStorage.setItem('accessToken', response.data.access);
    localStorage.setItem('refreshToken', response.data.refresh);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAccountDetails = async () => {
  try {
    const response = await api.get('/api/rmon/account-details/');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getResourcesPerRegion = async () => {
  try {
    const response = await api.get('/api/rmon/resource-per-region/');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export default api;