import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Stack,
  Text,
  Textarea,
  useColorModeValue,
  useToast
} from '@chakra-ui/react';
import { CalendarIcon, CheckIcon, CloseIcon, EditIcon } from '@chakra-ui/icons';
import { calendarService } from '../../services/calendarService';

/**
 * CalendarEventCard displays event information with confirmation options 
 * for proposed calendar operations from the agent
 */
const CalendarEventCard = ({ operationData, onConfirm, onCancel }) => {
  const toast = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [eventData, setEventData] = useState(operationData?.details || {});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('blue.500', 'blue.300');
  
  // Format dates for display
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      hour12: true
    });
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setEventData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleConfirm = async () => {
    try {
      setIsSubmitting(true);
      
      // Send the confirmed operation to the backend
      const response = await calendarService.executeConfirmedOperation({
        operation: operationData.operation,
        details: eventData
      });
      
      toast({
        title: "Success",
        description: response.message || "Calendar event has been confirmed!",
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      
      if (onConfirm) {
        onConfirm(response);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error.message || "Failed to process calendar operation",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (!operationData) return null;
  
  const { action_title, summary, display } = operationData;
  
  return (
    <Card 
      borderLeft="4px solid"
      borderColor={borderColor}
      bg={bgColor}
      boxShadow="md"
      mb={4}
      maxW="600px"
    >
      <CardHeader pb={2}>
        <Heading size="md">
          <CalendarIcon mr={2} color={borderColor} />
          {action_title || "Calendar Event"}
        </Heading>
        <Text fontSize="sm" color="gray.500">Confirmation required</Text>
      </CardHeader>
      
      <CardBody pt={0}>
        {isEditing ? (
          <Stack spacing={4}>
            <FormControl>
              <FormLabel>Event Title</FormLabel>
              <Input 
                name="summary" 
                value={eventData.summary || ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>Start Time</FormLabel>
              <Input 
                name="start_time" 
                type="datetime-local"
                value={eventData.start_time ? new Date(eventData.start_time).toISOString().slice(0, 16) : ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>End Time</FormLabel>
              <Input 
                name="end_time" 
                type="datetime-local"
                value={eventData.end_time ? new Date(eventData.end_time).toISOString().slice(0, 16) : ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>Location</FormLabel>
              <Input 
                name="location" 
                value={eventData.location || ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>Description</FormLabel>
              <Textarea 
                name="description" 
                value={eventData.description || ''} 
                onChange={handleChange} 
              />
            </FormControl>
          </Stack>
        ) : (
          <Stack spacing={2}>
            <Text fontWeight="bold">{display.title || "Untitled Event"}</Text>
            <Text>{display.date}</Text>
            <Text>{display.time}</Text>
            {display.location && <Text><strong>Location:</strong> {display.location}</Text>}
            {display.description && (
              <Text>
                <strong>Description:</strong> {display.description}
              </Text>
            )}
            <Text fontSize="sm" color="gray.500">{summary}</Text>
          </Stack>
        )}
      </CardBody>
      
      <CardFooter pt={2} justifyContent="space-between">
        <Button
          leftIcon={<CloseIcon />}
          colorScheme="red"
          variant="outline"
          size="sm"
          onClick={onCancel}
        >
          Cancel
        </Button>
        
        <Box>
          <Button
            leftIcon={isEditing ? <CheckIcon /> : <EditIcon />}
            colorScheme="blue"
            variant="outline"
            size="sm"
            mr={2}
            onClick={() => isEditing ? setIsEditing(false) : setIsEditing(true)}
          >
            {isEditing ? "Done Editing" : "Edit"}
          </Button>
          
          <Button
            colorScheme="green"
            size="sm"
            isLoading={isSubmitting}
            onClick={handleConfirm}
          >
            Confirm
          </Button>
        </Box>
      </CardFooter>
    </Card>
  );
};

export default CalendarEventCard;
