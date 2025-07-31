import React from 'react';
import {
  Box,
  VStack,
  Text,
  Badge,
  Card,
  CardBody,
  Heading,
  HStack,
  IconButton,
  Tooltip,
  useColorModeValue,
  Alert,
  AlertIcon,
  useToast,
} from '@chakra-ui/react';
import { DeleteIcon, EditIcon } from '@chakra-ui/icons';
import { format, parseISO } from 'date-fns';
import { calendarService } from '../../services/calendarService';

const EventList = ({ events = [], onRefresh }) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return '';
    try {
      const date = parseISO(dateTimeStr);
      return format(date, 'MMM d, yyyy h:mm a');
    } catch (error) {
      console.error('Error parsing date:', error);
      return dateTimeStr;
    }
  };

  const toast = useToast();
  
  const deleteEvent = async (eventId, calendarId) => {
    if (!window.confirm('Are you sure you want to delete this event?')) {
      return;
    }
    
    try {
      await calendarService.deleteEvent(eventId, calendarId);
      
      // Show success toast
      toast({
        title: 'Event deleted',
        description: 'The event has been successfully deleted',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      // Refresh the events list
      onRefresh();
    } catch (error) {
      console.error('Error deleting event:', error);
      
      // Show error toast
      toast({
        title: 'Error',
        description: 'Failed to delete event',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  if (events.length === 0) {
    return (
      <Alert status="info" borderRadius="md">
        <AlertIcon />
        No upcoming events found.
      </Alert>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {events.map((event) => (
        <Card 
          key={event.id} 
          bg={cardBg}
          borderColor={borderColor}
          borderWidth="1px"
          shadow="sm"
        >
          <CardBody>
            <HStack justify="space-between" mb={2}>
              <Heading size="sm">{event.summary}</Heading>
              <HStack>
                <Tooltip label="Edit event">
                  <IconButton
                    icon={<EditIcon />}
                    size="sm"
                    variant="ghost"
                    aria-label="Edit event"
                  />
                </Tooltip>
                <Tooltip label="Delete event">
                  <IconButton
                    icon={<DeleteIcon />}
                    size="sm"
                    variant="ghost"
                    aria-label="Delete event"
                    onClick={() => deleteEvent(event.id, event.calendarId || 'primary')}
                  />
                </Tooltip>
              </HStack>
            </HStack>
            
            <VStack align="start" spacing={2}>
              <HStack>
                <Badge colorScheme="blue">
                  {formatDateTime(event.start?.dateTime || event.start?.date)}
                </Badge>
                <Text fontSize="sm">to</Text>
                <Badge colorScheme="green">
                  {formatDateTime(event.end?.dateTime || event.end?.date)}
                </Badge>
              </HStack>
              
              {event.location && (
                <HStack>
                  <Text fontSize="sm" fontWeight="bold">Location:</Text>
                  <Text fontSize="sm">{event.location}</Text>
                </HStack>
              )}
              
              {event.description && (
                <Box mt={2}>
                  <Text fontSize="sm" fontWeight="bold">Description:</Text>
                  <Text fontSize="sm">{event.description}</Text>
                </Box>
              )}
            </VStack>
          </CardBody>
        </Card>
      ))}
    </VStack>
  );
};

export default EventList;
