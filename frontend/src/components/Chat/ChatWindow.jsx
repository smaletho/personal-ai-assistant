import React, { useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';
import ChatMessage from './ChatMessage';
import TypingIndicator from './TypingIndicator';

const ChatWindow = ({ messages = [], isTyping = false }) => {
  const messagesEndRef = useRef(null);
  const bgColor = useColorModeValue('gray.50', 'gray.700');
  
  // Scroll to bottom whenever messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  return (
    <Box 
      width="100%" 
      flex="1" 
      bg={bgColor} 
      borderRadius="md" 
      p={4}
      overflowY="auto"
    >
      {messages.length === 0 ? (
        <Box 
          display="flex" 
          alignItems="center" 
          justifyContent="center" 
          height="100%" 
          color="gray.500"
        >
          Start a conversation with your AI Calendar Assistant
        </Box>
      ) : (
        <VStack spacing={4} align="stretch">
          {messages.map((message) => (
            <ChatMessage 
              key={message.id} 
              message={message}
            />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </VStack>
      )}
    </Box>
  );
};

export default ChatWindow;
