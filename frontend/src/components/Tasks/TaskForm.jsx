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
  VStack,
  FormErrorMessage,
  useToast,
} from '@chakra-ui/react';
import { useFormik } from 'formik';
import * as Yup from 'yup';

const TaskForm = ({ isOpen, onClose, onSubmit }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // Validation schema
  const validationSchema = Yup.object({
    title: Yup.string().required('Title is required'),
    notes: Yup.string(),
    due_date: Yup.string(),
  });

  // Form handling
  const formik = useFormik({
    initialValues: {
      title: '',
      notes: '',
      due_date: '',
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
          title: 'Error creating task',
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

  // Set min date to today
  const getMinDate = () => {
    const now = new Date();
    return now.toISOString().slice(0, 10); // Format: YYYY-MM-DD
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Create New Task</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={formik.handleSubmit}>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl 
                isInvalid={formik.touched.title && formik.errors.title}
                isRequired
              >
                <FormLabel>Title</FormLabel>
                <Input 
                  name="title"
                  placeholder="Task title"
                  {...formik.getFieldProps('title')}
                />
                <FormErrorMessage>{formik.errors.title}</FormErrorMessage>
              </FormControl>

              <FormControl>
                <FormLabel>Notes</FormLabel>
                <Textarea 
                  name="notes"
                  placeholder="Task details"
                  {...formik.getFieldProps('notes')}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Due Date</FormLabel>
                <Input 
                  name="due_date"
                  type="date"
                  min={getMinDate()}
                  {...formik.getFieldProps('due_date')}
                />
              </FormControl>
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
              Create Task
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default TaskForm;
