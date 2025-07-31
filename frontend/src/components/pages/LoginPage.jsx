import React from 'react';
import {
  Box,
  Button,
  Center,
  Heading,
  Text,
  VStack,
  Image,
  useColorModeValue,
} from '@chakra-ui/react';
import { FcGoogle } from 'react-icons/fc';
import { useAuth } from '../../contexts/AuthContext';

const LoginPage = () => {
  const { login, isLoading, error } = useAuth();
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const cardBgColor = useColorModeValue('white', 'gray.700');

  return (
    <Center h="100%" bg={bgColor}>
      <Box
        p={8}
        maxW="md"
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
        bg={cardBgColor}
      >
        <VStack spacing={8} align="center">
          <Image
            src="/logo.png"
            alt="Personal AI Assistant"
            boxSize="100px"
            fallbackSrc="https://via.placeholder.com/100?text=AI"
          />
          
          <VStack spacing={2} textAlign="center">
            <Heading size="xl">Welcome</Heading>
            <Text>Sign in to your Personal AI Assistant</Text>
          </VStack>
          
          <Button
            w="full"
            h="50px"
            variant="outline"
            leftIcon={<FcGoogle />}
            onClick={login}
            isLoading={isLoading}
            loadingText="Redirecting..."
          >
            Sign in with Google
          </Button>
          
          {error && (
            <Text color="red.500" fontSize="sm">
              {error}
            </Text>
          )}
          
          <Text fontSize="xs" color="gray.500" textAlign="center">
            By signing in, you'll authorize this application to access your Google Calendar and Tasks.
          </Text>
        </VStack>
      </Box>
    </Center>
  );
};

export default LoginPage;
