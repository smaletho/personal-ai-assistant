import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  VStack,
  FormErrorMessage,
  useToast,
} from '@chakra-ui/react';
import { useFormik } from 'formik';
import * as Yup from 'yup';

const EventForm = ({ isOpen, onClose, onSubmit, calendars = [] }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // Validation schema
  const validationSchema = Yup.object({
    summary: Yup.string().required('Title is required'),
    start_time: Yup.string().required('Start time is required'),
    end_time: Yup.string()
      .required('End time is required')
      .test('is-after-start', 'End time must be after start time', function (value) {
        const { start_time } = this.parent;
        if (!start_time || !value) return true;
        return new Date(value) > new Date(start_time);
      }),
    description: Yup.string(),
    location: Yup.string(),
    calendar_id: Yup.string(),
  });

  // Form handling
  const formik = useFormik({
    initialValues: {
      summary: '',
      start_time: '',
      end_time: '',
      description: '',
      location: '',
      calendar_id: calendars.length > 0 ? calendars[0].id : 'primary',
    },
    validationSchema,
    onSubmit: async (values) => {
      setIsSubmitting(true);
      try {
        await onSubmit(values);
        onClose();
        
        // Reset form
        formik.resetForm();
      } catch (error) {
        toast({
          title: 'Error creating event',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setIsSubmitting(false);
      }
    },
  });

  // Set min datetime to now for start time
  const getMinDateTime = () => {
    const now = new Date();
    return now.toISOString().slice(0, 16); // Format: YYYY-MM-DDThh:mm
  };

  // Set min datetime to start time for end time
  const getMinEndDateTime = () => {
    if (!formik.values.start_time) return getMinDateTime();
    return formik.values.start_time;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Create New Event</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={formik.handleSubmit}>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl 
                isInvalid={formik.touched.summary && formik.errors.summary}
                isRequired
              >
                <FormLabel>Title</FormLabel>
                <Input 
                  name="summary"
                  placeholder="Event title"
                  {...formik.getFieldProps('summary')}
                />
                <FormErrorMessage>{formik.errors.summary}</FormErrorMessage>
              </FormControl>

              <FormControl 
                isInvalid={formik.touched.start_time && formik.errors.start_time}
                isRequired
              >
                <FormLabel>Start Time</FormLabel>
                <Input 
                  name="start_time"
                  type="datetime-local"
                  min={getMinDateTime()}
                  {...formik.getFieldProps('start_time')}
                />
                <FormErrorMessage>{formik.errors.start_time}</FormErrorMessage>
              </FormControl>

              <FormControl 
                isInvalid={formik.touched.end_time && formik.errors.end_time}
                isRequired
              >
                <FormLabel>End Time</FormLabel>
                <Input 
                  name="end_time"
                  type="datetime-local"
                  min={getMinEndDateTime()}
                  {...formik.getFieldProps('end_time')}
                />
                <FormErrorMessage>{formik.errors.end_time}</FormErrorMessage>
              </FormControl>

              <FormControl>
                <FormLabel>Location</FormLabel>
                <Input 
                  name="location"
                  placeholder="Event location"
                  {...formik.getFieldProps('location')}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea 
                  name="description"
                  placeholder="Event description"
                  {...formik.getFieldProps('description')}
                />
              </FormControl>

              {calendars.length > 0 && (
                <FormControl>
                  <FormLabel>Calendar</FormLabel>
                  <Select 
                    name="calendar_id"
                    {...formik.getFieldProps('calendar_id')}
                  >
                    {calendars.map(calendar => (
                      <option key={calendar.id} value={calendar.id}>
                        {calendar.summary}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              )}
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button 
              colorScheme="brand" 
              type="submit"
              isLoading={isSubmitting}
            >
              Create Event
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default EventForm;
