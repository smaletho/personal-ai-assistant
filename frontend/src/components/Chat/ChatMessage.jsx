import React, { useState } from 'react';
import {
  Box,
  Flex,
  Text,
  Avatar,
  useColorModeValue,
  useToast
} from '@chakra-ui/react';
import { format } from 'date-fns';
import CalendarEventCard from '../Calendar/CalendarEventCard';
import TaskCard from '../Tasks/TaskCard';

const ChatMessage = ({ message, onOperationComplete }) => {
  const { content, role, timestamp, isError, operationData } = message;
  const isUser = role === 'user';
  const isSystem = role === 'system';
  const toast = useToast();
  const [operationCompleted, setOperationCompleted] = useState(false);
  
  // Check if this message contains a confirmation request
  const requiresConfirmation = !isUser && operationData && operationData.requires_confirmation;
  
  // Determine operation type (calendar or task)
  const isCalendarOperation = requiresConfirmation && operationData.operation.includes('event');
  const isTaskOperation = requiresConfirmation && operationData.operation.includes('task');
  
  // Color scheme based on message role and theme
  const userBubbleBg = useColorModeValue('brand.500', 'brand.600');
  const assistantBubbleBg = useColorModeValue('gray.100', 'gray.700');
  const systemBubbleBg = useColorModeValue('red.100', 'red.700');
  
  const bubbleBg = isUser 
    ? userBubbleBg 
    : isSystem || isError
      ? systemBubbleBg
      : assistantBubbleBg;
  
  const textColor = isUser ? 'white' : undefined;
  
  // Format timestamp if available
  const formattedTime = timestamp 
    ? format(new Date(timestamp), 'h:mm a')
    : '';
    
  // Handle confirmation success
  const handleConfirmSuccess = (result) => {
    setOperationCompleted(true);
    toast({
      title: "Success",
      description: result.message || "Operation completed successfully",
      status: "success",
      duration: 5000,
      isClosable: true,
    });
    
    if (onOperationComplete) {
      onOperationComplete(message.id, result);
    }
  };
  
  // Handle confirmation cancellation
  const handleCancel = () => {
    setOperationCompleted(true);
    toast({
      title: "Cancelled",
      description: "Operation was cancelled",
      status: "info",
      duration: 3000,
      isClosable: true,
    });
  };

  return (
    <Flex
      direction="column"
      alignItems={isUser ? 'flex-end' : 'flex-start'}
      mb={4}
      w="100%"
    >
      <Flex
        direction="row"
        justifyContent={isUser ? 'flex-end' : 'flex-start'}
        mb={requiresConfirmation ? 2 : 0}
        w="100%"
      >
        {!isUser && !isSystem && (
          <Avatar 
            size="sm" 
            name="AI Assistant" 
            bg="brand.500"
            color="white"
            mr={2} 
          />
        )}

        <Box>
          <Box
            maxW="80%"
            bg={bubbleBg}
            p={3}
            borderRadius="lg"
            color={textColor}
            boxShadow="sm"
          >
            <Text>{content}</Text>
          </Box>
          
          {timestamp && (
            <Text 
              fontSize="xs" 
              color="gray.500" 
              textAlign={isUser ? 'right' : 'left'}
              mt={1}
            >
              {formattedTime}
            </Text>
          )}
        </Box>

        {isUser && (
          <Avatar 
            size="sm" 
            name="You" 
            ml={2} 
          />
        )}
      </Flex>
      
      {/* Render confirmation cards when needed */}
      {requiresConfirmation && !operationCompleted && (
        <Box pl={!isUser ? 10 : 0} pr={isUser ? 10 : 0} mt={2} w="100%">
          {isCalendarOperation && (
            <CalendarEventCard 
              operationData={operationData}
              onConfirm={handleConfirmSuccess}
              onCancel={handleCancel}
            />
          )}
          
          {isTaskOperation && (
            <TaskCard
              operationData={operationData}
              onConfirm={handleConfirmSuccess}
              onCancel={handleCancel}
            />
          )}
        </Box>
      )}
    </Flex>
  );
};

export default ChatMessage;
