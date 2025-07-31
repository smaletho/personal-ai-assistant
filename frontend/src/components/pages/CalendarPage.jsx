import React, { useState, useEffect } from 'react';
import {
  Box,
  Heading,
  VStack,
  SimpleGrid,
  Button,
  useDisclosure,
  Spinner,
  Text,
  useToast
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import EventList from '../Calendar/EventList';
import EventForm from '../Calendar/EventForm';

const CalendarPage = () => {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [calendars, setCalendars] = useState([]);
  const [selectedCalendar, setSelectedCalendar] = useState('primary');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  // Fetch events from the API
  const fetchEvents = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/calendar/events?calendar_id=${selectedCalendar}&max_results=10`);
      const data = await response.json();
      setEvents(data.events || []);
    } catch (error) {
      console.error('Error fetching events:', error);
      toast({
        title: 'Error fetching events',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch available calendars
  const fetchCalendars = async () => {
    try {
      const response = await fetch('/calendar');
      const data = await response.json();
      setCalendars(data.calendars || []);
    } catch (error) {
      console.error('Error fetching calendars:', error);
    }
  };

  // Load data on mount and when selectedCalendar changes
  useEffect(() => {
    fetchCalendars();
    fetchEvents();
  }, [selectedCalendar]);

  // Create a new event
  const createEvent = async (eventData) => {
    try {
      const response = await fetch('/calendar/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...eventData,
          calendar_id: selectedCalendar,
        }),
      });
      
      const data = await response.json();
      
      // Refresh events
      fetchEvents();
      
      // Close the form
      onClose();
      
      // Show success message
      toast({
        title: 'Event created',
        description: 'Your event was successfully created.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      return data;
    } catch (error) {
      console.error('Error creating event:', error);
      
      toast({
        title: 'Error creating event',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      
      throw error;
    }
  };

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Heading size="lg">Calendar</Heading>
          <Button 
            leftIcon={<AddIcon />} 
            colorScheme="brand" 
            onClick={onOpen}
          >
            Add Event
          </Button>
        </Box>

        {isLoading ? (
          <Box textAlign="center" py={10}>
            <Spinner size="xl" />
            <Text mt={4}>Loading events...</Text>
          </Box>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 1, lg: 1 }} spacing={6}>
            <EventList 
              events={events} 
              onRefresh={fetchEvents} 
            />
          </SimpleGrid>
        )}
      </VStack>

      <EventForm
        isOpen={isOpen}
        onClose={onClose}
        onSubmit={createEvent}
        calendars={calendars}
      />
    </Box>
  );
};

export default CalendarPage;
