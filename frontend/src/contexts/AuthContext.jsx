import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// Create the context
const AuthContext = createContext();

// Custom hook for using the auth context
export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  // Auth state
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(() => {
    // Initialize token from localStorage if available
    return localStorage.getItem('auth_token');
  });

  // Log localStorage status on component mount
  useEffect(() => {
    console.log('AuthProvider mounted - localStorage auth_token:', localStorage.getItem('auth_token') ? 'exists' : 'not found');
  }, []);
  
  // Extract token from URL fragment on mount
  useEffect(() => {
    const extractTokenFromHash = () => {
      // Check if URL has a hash and token
      if (window.location.hash) {
        console.log('URL hash detected:', window.location.hash.substring(0, 20) + '...');
        try {
          const hashParams = new URLSearchParams(
            window.location.hash.substring(1) // Remove the '#' character
          );
          
          const accessToken = hashParams.get('access_token');
          if (accessToken) {
            console.log('Found token in URL fragment - storing in localStorage');
            console.log('Token length:', accessToken.length, 'Preview:', accessToken.substring(0, 10) + '...');
            
            // Store token in localStorage
            localStorage.setItem('auth_token', accessToken);
            console.log('Token successfully stored in localStorage');
            
            // Update state
            setToken(accessToken);
            
            // Clean up URL to remove the token
            // This prevents token from staying in browser history
            window.history.replaceState({}, document.title, window.location.pathname);
            console.log('URL fragment cleaned up for security');
            
            return accessToken;
          } else {
            console.log('No access_token found in URL hash parameters');
            console.log('Available hash parameters:', Array.from(hashParams.keys()).join(', '));
          }
        } catch (error) {
          console.error('Error parsing URL hash:', error);
        }
      } else {
        console.log('No URL hash detected on page load');
      }
      return null;
    };
    
    // Try to extract token from URL fragment
    extractTokenFromHash();
  }, []);
  
  // Check if user is authenticated on mount or when token changes
  useEffect(() => {
    console.log('Auth check triggered - Current token state:', token ? `${token.substring(0, 10)}...` : 'null');
    const checkAuthStatus = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Try with localStorage token first if available
        if (token) {
          console.log('Attempting authentication with localStorage token');
          
          // Get user info from API using Authorization header
          const response = await fetch('/auth/user', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
            setIsAuthenticated(true);
            console.log('Authentication successful using localStorage token');
            return;
          } else {
            console.log('localStorage token authentication failed, will try cookie-based auth')
          }
        } else {
          console.log('No token in localStorage, will try cookie-based auth');
        }
        
        // Fallback to cookie-based authentication if localStorage token failed or doesn't exist
        console.log('Attempting cookie-based authentication');
        const response = await fetch('/auth/user', {
          credentials: 'include' // Important for cookies
        });
        
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          setIsAuthenticated(true);
          console.log('Authentication successful using cookies');
          
          // If cookie auth worked but no localStorage token, store the cookie token in localStorage for future use
          if (!token) {
            try {
              // Try to extract token from cookies
              const cookieToken = document.cookie
                .split('; ')
                .find(row => row.startsWith('session_token='))?.split('=')[1];
                
              if (cookieToken) {
                console.log('Saving cookie token to localStorage for consistent auth');
                try {
                  localStorage.setItem('auth_token', cookieToken);
                  setToken(cookieToken);
                  console.log('Successfully saved auth_token to localStorage for WebSocket auth');
                } catch (err) {
                  console.error('Failed to save token to localStorage:', err);
                }
              } else {
                // Look for token in the response headers
                const authHeader = response.headers.get('Authorization');
                if (authHeader && authHeader.startsWith('Bearer ')) {
                  const headerToken = authHeader.substring(7); // Remove 'Bearer ' prefix
                  console.log('Found token in Authorization header, saving to localStorage');
                  try {
                    localStorage.setItem('auth_token', headerToken);
                    setToken(headerToken);
                    console.log('Successfully saved header token to localStorage for WebSocket auth');
                  } catch (err) {
                    console.error('Failed to save header token to localStorage:', err);
                  }
                } else {
                  console.warn('No token found in cookies or headers');
                }
              }
            } catch (e) {
              console.error('Error extracting cookie token:', e);
            }
          }
        } else {
          // Neither method worked - user is not authenticated
          console.log('Both token and cookie authentication failed');
          localStorage.removeItem('auth_token');
          setToken(null);
          setUser(null);
          setIsAuthenticated(false);
        }
      } catch (err) {
        console.error('Error checking authentication status:', err);
        setError('Failed to check authentication status');
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuthStatus();
  }, [token]); // Re-run when token changes
  
  // Login function - redirects to Google OAuth
  const login = async () => {
    try {
      // Get the auth URL from the backend
      const response = await fetch('/auth/login');
      const data = await response.json();
      
      // Redirect to Google's OAuth page
      window.location.href = data.auth_url;
    } catch (err) {
      console.error('Login error:', err);
      setError('Failed to initiate login');
    }
  };
  
  // Logout function
  const logout = async () => {
    try {
      await fetch('/auth/logout', {
        credentials: 'include'
      });
      
      // Clear auth state
      setUser(null);
      setIsAuthenticated(false);
    } catch (err) {
      console.error('Logout error:', err);
      setError('Failed to logout');
    }
  };
  
  // Refresh user data
  const refreshUserData = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/auth/user', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        // Session might have expired
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.error('Error refreshing user data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Context value
  const value = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    refreshUserData
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
