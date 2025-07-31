import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Box, Flex } from '@chakra-ui/react';

// Components
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';

// Pages
import ChatPage from './components/pages/ChatPage';
import CalendarPage from './components/pages/CalendarPage';
import TasksPage from './components/pages/TasksPage';
import SettingsPage from './components/pages/SettingsPage';
import LoginPage from './components/pages/LoginPage';

// Auth
import AuthCallbackHandler from './components/auth/AuthCallbackHandler';

// Context Providers
import { ChatProvider } from './contexts/ChatContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Protected route wrapper
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <Box p={8}>Loading...</Box>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackHandler />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <ChatProvider>
                <Flex direction="column" h="100vh">
                  <Header />
                  <Flex flex="1" overflow="hidden">
                    <Sidebar />
                    <Box flex="1" p={4} overflowY="auto">
                      <Routes>
                        <Route path="/" element={<ChatPage />} />
                        <Route path="/calendar" element={<CalendarPage />} />
                        <Route path="/tasks" element={<TasksPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                      </Routes>
                    </Box>
                  </Flex>
                </Flex>
              </ChatProvider>
            </ProtectedRoute>
          } />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
