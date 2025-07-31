/**
 * Base API service for handling HTTP requests
 * Provides centralized error handling and request configuration
 */
import axios from 'axios';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds timeout
});

// Request interceptor for handling auth tokens if needed
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed in the future
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response) {
      // Server responded with non-2xx status
      console.error('API Error Response:', error.response.data);
      
      // Handle specific status codes if needed
      switch (error.response.status) {
        case 401:
          console.error('Unauthorized access');
          // Could trigger authentication flow here
          break;
        case 403:
          console.error('Forbidden access');
          break;
        case 500:
          console.error('Server error');
          break;
        default:
          break;
      }
    } else if (error.request) {
      // Request was made but no response
      console.error('No response received:', error.request);
    } else {
      // Request setup error
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
