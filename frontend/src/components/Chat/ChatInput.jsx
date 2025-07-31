import React, { useState } from 'react';
import {
  Box,
  Input,
  InputGroup,
  InputRightElement,
  IconButton,
  useColorModeValue,
  Tooltip,
} from '@chakra-ui/react';
import { ArrowUpIcon } from '@chakra-ui/icons';

const ChatInput = ({ onSendMessage, isConnected = true }) => {
  const [message, setMessage] = useState('');
  const inputBg = useColorModeValue('white', 'gray.700');
  const buttonColorScheme = 'brand';
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (message.trim() && isConnected) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <Box width="100%" as="form" onSubmit={handleSubmit}>
      <InputGroup size="md">
        <Input
          pr="4.5rem"
          placeholder="Type a message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          bg={inputBg}
          isDisabled={!isConnected}
          _hover={{ borderColor: 'brand.300' }}
          _focus={{ borderColor: 'brand.500', boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)' }}
        />
        <InputRightElement width="4.5rem">
          <Tooltip
            label={isConnected ? 'Send message' : 'Disconnected'}
            placement="top"
            hasArrow
          >
            <IconButton
              h="1.75rem"
              size="sm"
              colorScheme={buttonColorScheme}
              aria-label="Send message"
              icon={<ArrowUpIcon />}
              type="submit"
              isDisabled={!message.trim() || !isConnected}
            />
          </Tooltip>
        </InputRightElement>
      </InputGroup>
    </Box>
  );
};

export default ChatInput;
