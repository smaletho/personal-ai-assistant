import React, { useState } from 'react';
import {
  Box,
  Heading,
  VStack,
  FormControl,
  FormLabel,
  Input,
  Button,
  Select,
  Switch,
  Text,
  useToast,
  Card,
  CardBody,
  CardHeader,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';

const SettingsPage = () => {
  const [sessionId, setSessionId] = useState(localStorage.getItem('chatSessionId') || '');
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const handleSessionReset = () => {
    setLoading(true);
    
    // Generate a new session ID
    const newSessionId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    
    // Save to local storage
    localStorage.setItem('chatSessionId', newSessionId);
    setSessionId(newSessionId);
    
    // Show toast
    toast({
      title: 'Session Reset',
      description: 'Your conversation history has been cleared.',
      status: 'success',
      duration: 5000,
      isClosable: true,
    });
    
    setLoading(false);
    
    // Reload the page to reconnect with the new session ID
    window.location.reload();
  };

  return (
    <Box>
      <Heading size="lg" mb={6}>Settings</Heading>
      
      <VStack spacing={8} align="stretch">
        <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
          <CardHeader>
            <Heading size="md">Chat Settings</Heading>
          </CardHeader>
          <Divider />
          <CardBody>
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Current Session ID</FormLabel>
                <Input value={sessionId} isReadOnly />
                <Text fontSize="sm" color="gray.500" mt={1}>
                  This is your unique conversation identifier. Your chat history is tied to this ID.
                </Text>
              </FormControl>
              
              <Button 
                colorScheme="red" 
                variant="outline" 
                onClick={handleSessionReset}
                isLoading={loading}
              >
                Reset Conversation History
              </Button>
            </VStack>
          </CardBody>
        </Card>
        
        <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
          <CardHeader>
            <Heading size="md">Display Settings</Heading>
          </CardHeader>
          <Divider />
          <CardBody>
            <VStack spacing={4} align="stretch">
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="dark-mode" mb="0">
                  Show Typing Indicator
                </FormLabel>
                <Switch id="typing-indicator" defaultChecked />
              </FormControl>
              
              <FormControl>
                <FormLabel>Message Display Format</FormLabel>
                <Select defaultValue="bubbles">
                  <option value="bubbles">Chat Bubbles</option>
                  <option value="blocks">Message Blocks</option>
                  <option value="compact">Compact View</option>
                </Select>
              </FormControl>
            </VStack>
          </CardBody>
        </Card>

        <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
          <CardHeader>
            <Heading size="md">Calendar Settings</Heading>
          </CardHeader>
          <Divider />
          <CardBody>
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Default Calendar</FormLabel>
                <Select defaultValue="primary">
                  <option value="primary">Primary Calendar</option>
                  <option value="work">Work Calendar</option>
                  <option value="personal">Personal Calendar</option>
                </Select>
              </FormControl>
              
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="notifications" mb="0">
                  Event Notifications
                </FormLabel>
                <Switch id="notifications" defaultChecked />
              </FormControl>
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Box>
  );
};

export default SettingsPage;
