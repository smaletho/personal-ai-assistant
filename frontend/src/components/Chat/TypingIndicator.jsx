import React from 'react';
import {
  Box,
  Flex,
  Avatar,
  useColorModeValue,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';

const pulseKeyframes = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.6; }
  100% { transform: scale(1); opacity: 1; }
`;

const TypingIndicator = () => {
  const bgColor = useColorModeValue('gray.100', 'gray.700');
  const dotColor = useColorModeValue('gray.400', 'gray.400');
  const pulseAnimation = `${pulseKeyframes} 1.5s infinite`;
  
  return (
    <Flex align="center" maxW="60%">
      <Avatar 
        size="sm" 
        name="AI Assistant" 
        bg="brand.500" 
        color="white"
        mr={2}
      />
      <Box
        bg={bgColor}
        p={3}
        borderRadius="lg"
        boxShadow="sm"
      >
        <Flex>
          {[0, 1, 2].map(i => (
            <Box
              key={i}
              h="8px"
              w="8px"
              borderRadius="full"
              bg={dotColor}
              mx="1px"
              animation={pulseAnimation}
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </Flex>
      </Box>
    </Flex>
  );
};

export default TypingIndicator;
