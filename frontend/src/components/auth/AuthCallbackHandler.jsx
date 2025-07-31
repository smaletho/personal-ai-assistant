import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Center, Spinner, Box, Text, VStack } from '@chakra-ui/react';
import { useAuth } from '../../contexts/AuthContext';

const AuthCallbackHandler = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { refreshUserData } = useAuth();
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get code and state from URL search params
        const searchParams = new URLSearchParams(location.search);
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        
        if (!code || !state) {
          throw new Error('Missing authorization code or state');
        }
        
        // To prevent reuse, check if we've already processed this code
        const processedCodes = JSON.parse(sessionStorage.getItem('processedAuthCodes') || '[]');
        
        if (processedCodes.includes(code)) {
          console.warn('Auth code has already been processed! Preventing reuse.');
          // Just try to refresh user data directly instead of reusing the code
          await refreshUserData();
          navigate('/', { replace: true });
          return;
        }
        
        // Mark this code as processed
        processedCodes.push(code);
        sessionStorage.setItem('processedAuthCodes', JSON.stringify(processedCodes));
        
        console.log('Received OAuth callback with code:', code.substring(0, 10) + '...');
        
        // Get the current URL's protocol and host to build proper backend URL
        const backendHost = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        
        // Instead of redirecting which causes the double-callback issue,
        // make a direct fetch request to the backend callback endpoint
        console.log(`Sending code to backend callback endpoint directly...`);
        
        try {
          // Show loading spinner while processing
          setError(null);
          
          // Send the auth code to the backend callback endpoint
          const response = await fetch(`${backendHost}/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`, {
            method: 'GET',
            credentials: 'include', // Important for cookies
            headers: {
              'Accept': 'application/json'
            }
          });
          
          if (!response.ok) {
            const errorData = await response.text();
            console.error('Backend auth error:', errorData);
            throw new Error(`Authentication failed: ${errorData}`);
          }
          
          // Parse the response JSON which should contain the token
          try {
            const data = await response.json();
            console.log('Received authentication data from backend');
            
            // Extract the token from the response
            if (data.token) {
              console.log('JWT token received from server, saving to localStorage');
              localStorage.setItem('auth_token', data.token);
              
              // Also extract any cookies that might be relevant
              // This is a fallback in case the browser didn't automatically handle the cookies
              const cookies = document.cookie.split(';').map(cookie => cookie.trim());
              console.log('Current cookies:', cookies);
              
              // Check if we have the auth_token cookie
              const authTokenCookie = cookies.find(c => c.startsWith('auth_token='));
              if (authTokenCookie && !localStorage.getItem('auth_token')) {
                const cookieValue = authTokenCookie.split('=')[1];
                console.log('Found auth_token in cookies, saving to localStorage');
                localStorage.setItem('auth_token', cookieValue);
              }
            } else {
              console.warn('No token received from server');
            }
          } catch (err) {
            console.warn('Error parsing JSON response from server:', err);
            // The response may not be JSON if the server redirects or returns HTML
            // In this case, we'll still try to use cookie-based authentication
          }
          
          // Wait a moment to allow the backend to process the callback
          await new Promise(resolve => setTimeout(resolve, 500));
          
          // Refresh user data in context
          await refreshUserData();
          
          // Redirect to homepage
          navigate('/', { replace: true });
        } catch (err) {
          console.error('Error handling authentication:', err);
          setError(err.message || 'Authentication failed.');
        }
      } catch (err) {
        console.error('Error processing authentication callback:', err);
        setError('Authentication failed. Please try again.');
        
        // Redirect to login after a delay
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 3000);
      }
    };

    handleCallback();
  }, [navigate, refreshUserData]);

  return (
    <Center h="100vh">
      <VStack spacing={4}>
        {error ? (
          <Box textAlign="center">
            <Text color="red.500">{error}</Text>
            <Text>Redirecting to login...</Text>
          </Box>
        ) : (
          <>
            <Spinner size="xl" />
            <Text>Completing authentication...</Text>
          </>
        )}
      </VStack>
    </Center>
  );
};

export default AuthCallbackHandler;
