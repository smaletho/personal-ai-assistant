import React from 'react';
import {
  Box,
  VStack,
  Heading,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import ChatWindow from '../Chat/ChatWindow';
import ChatInput from '../Chat/ChatInput';
import { useChat } from '../../contexts/ChatContext';

const ChatPage = () => {
  const { messages, isConnected, isTyping, sendMessage } = useChat();
  const connectionBg = useColorModeValue('green.100', 'green.800');
  const disconnectedBg = useColorModeValue('red.100', 'red.800');

  return (
    <Box height="100%" display="flex" flexDirection="column">
      <Box p={3} mb={4} bg={isConnected ? connectionBg : disconnectedBg} borderRadius="md">
        <Text fontSize="sm" fontWeight="medium">
          {isConnected ? 'Connected to assistant' : 'Disconnected - reconnecting...'}
        </Text>
      </Box>
      
      <Heading as="h1" size="lg" mb={4}>
        AI Calendar Assistant
      </Heading>
      
      <VStack spacing={4} flex="1" overflow="hidden">
        <ChatWindow 
          messages={messages} 
          isTyping={isTyping} 
        />
        <ChatInput 
          onSendMessage={sendMessage} 
          isConnected={isConnected} 
        />
      </VStack>
    </Box>
  );
};

export default ChatPage;
