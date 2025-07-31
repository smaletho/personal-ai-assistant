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
  Checkbox,
  Tooltip,
  useColorModeValue,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { DeleteIcon, EditIcon } from '@chakra-ui/icons';
import { format, parseISO } from 'date-fns';

const TaskList = ({ tasks = [], onRefresh }) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = parseISO(dateStr);
      return format(date, 'MMM d, yyyy');
    } catch (error) {
      console.error('Error parsing date:', error);
      return dateStr;
    }
  };

  const handleStatusChange = async (taskId, tasklist_id, completed) => {
    try {
      const response = await fetch(`/tasks/${tasklist_id}/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: completed ? 'completed' : 'needsAction',
        }),
      });
      
      if (response.ok) {
        onRefresh();
      } else {
        console.error('Failed to update task status');
      }
    } catch (error) {
      console.error('Error updating task status:', error);
    }
  };

  const deleteTask = async (taskId, tasklist_id) => {
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }
    
    try {
      const response = await fetch(`/tasks/${tasklist_id}/${taskId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        onRefresh();
      } else {
        console.error('Failed to delete task');
      }
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  };

  if (tasks.length === 0) {
    return (
      <Alert status="info" borderRadius="md">
        <AlertIcon />
        No tasks found.
      </Alert>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {tasks.map((task) => {
        const isCompleted = task.status === 'completed';
        return (
          <Card 
            key={task.id} 
            bg={cardBg}
            borderColor={borderColor}
            borderWidth="1px"
            shadow="sm"
            opacity={isCompleted ? 0.7 : 1}
          >
            <CardBody>
              <HStack justify="space-between" mb={2} align="start">
                <HStack align="start" spacing={4}>
                  <Checkbox 
                    isChecked={isCompleted}
                    onChange={(e) => handleStatusChange(task.id, task.tasklist_id, e.target.checked)}
                    size="lg"
                    mt={1}
                  />
                  <Box>
                    <Heading size="sm" textDecoration={isCompleted ? 'line-through' : 'none'}>
                      {task.title}
                    </Heading>
                    {task.notes && (
                      <Text fontSize="sm" mt={1} color={isCompleted ? 'gray.500' : undefined}>
                        {task.notes}
                      </Text>
                    )}
                    {task.due && (
                      <Badge colorScheme={isCompleted ? 'gray' : 'blue'} mt={2}>
                        Due: {formatDate(task.due)}
                      </Badge>
                    )}
                  </Box>
                </HStack>
                <HStack>
                  <Tooltip label="Edit task">
                    <IconButton
                      icon={<EditIcon />}
                      size="sm"
                      variant="ghost"
                      aria-label="Edit task"
                    />
                  </Tooltip>
                  <Tooltip label="Delete task">
                    <IconButton
                      icon={<DeleteIcon />}
                      size="sm"
                      variant="ghost"
                      aria-label="Delete task"
                      onClick={() => deleteTask(task.id, task.tasklist_id)}
                    />
                  </Tooltip>
                </HStack>
              </HStack>
            </CardBody>
          </Card>
        );
      })}
    </VStack>
  );
};

export default TaskList;
