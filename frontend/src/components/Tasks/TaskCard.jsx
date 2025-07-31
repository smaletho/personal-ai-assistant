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
import { CheckIcon, CloseIcon, EditIcon } from '@chakra-ui/icons';
import { FaTasks } from 'react-icons/fa';
import { tasksService } from '../../services/tasksService';

/**
 * TaskCard displays task information with confirmation options 
 * for proposed task operations from the agent
 */
const TaskCard = ({ operationData, onConfirm, onCancel }) => {
  const toast = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [taskData, setTaskData] = useState(operationData?.details || {});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('green.500', 'green.300');
  
  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric', 
      year: 'numeric'
    });
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setTaskData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleConfirm = async () => {
    try {
      setIsSubmitting(true);
      
      // Send the confirmed operation to the backend
      const response = await tasksService.executeConfirmedOperation({
        operation: operationData.operation,
        details: taskData
      });
      
      toast({
        title: "Success",
        description: response.message || "Task operation has been confirmed!",
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
        description: error.message || "Failed to process task operation",
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
        <Heading size="md" display="flex" alignItems="center">
          <Box as={FaTasks} mr={2} color={borderColor} />
          {action_title || "Task Action"}
        </Heading>
        <Text fontSize="sm" color="gray.500">Confirmation required</Text>
      </CardHeader>
      
      <CardBody pt={0}>
        {isEditing ? (
          <Stack spacing={4}>
            <FormControl>
              <FormLabel>Task Title</FormLabel>
              <Input 
                name="title" 
                value={taskData.title || ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>Due Date</FormLabel>
              <Input 
                name="due_date" 
                type="date"
                value={taskData.due_date ? new Date(taskData.due_date).toISOString().slice(0, 10) : ''} 
                onChange={handleChange} 
              />
            </FormControl>
            
            <FormControl>
              <FormLabel>Notes</FormLabel>
              <Textarea 
                name="notes" 
                value={taskData.notes || ''} 
                onChange={handleChange} 
              />
            </FormControl>
          </Stack>
        ) : (
          <Stack spacing={2}>
            <Text fontWeight="bold">{display.title || "Untitled Task"}</Text>
            {display.due_date && (
              <Text>Due: {formatDate(display.due_date)}</Text>
            )}
            {display.notes && (
              <Text>
                <strong>Notes:</strong> {display.notes}
              </Text>
            )}
            {display.task_list && (
              <Text>
                <strong>List:</strong> {display.task_list}
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

export default TaskCard;
