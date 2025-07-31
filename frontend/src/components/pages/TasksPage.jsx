import React, { useState, useEffect } from 'react';
import {
  Box,
  Heading,
  VStack,
  Button,
  useDisclosure,
  Spinner,
  Text,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  useToast
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import TaskList from '../Tasks/TaskList';
import TaskForm from '../Tasks/TaskForm';

const TasksPage = () => {
  const [taskLists, setTaskLists] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTaskList, setSelectedTaskList] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  // Fetch task lists from the API
  const fetchTaskLists = async () => {
    try {
      const response = await fetch('/tasks/lists');
      const data = await response.json();
      
      if (data.tasklists && data.tasklists.length > 0) {
        setTaskLists(data.tasklists);
        // Select the first list by default if none is selected
        if (!selectedTaskList) {
          setSelectedTaskList(data.tasklists[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching task lists:', error);
      toast({
        title: 'Error fetching task lists',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // Fetch tasks for the selected task list
  const fetchTasks = async () => {
    if (!selectedTaskList) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/tasks?tasklist_id=${selectedTaskList}`);
      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      toast({
        title: 'Error fetching tasks',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Load task lists on mount
  useEffect(() => {
    fetchTaskLists();
  }, []);

  // Load tasks when the selected task list changes
  useEffect(() => {
    if (selectedTaskList) {
      fetchTasks();
    }
  }, [selectedTaskList]);

  // Create a new task
  const createTask = async (taskData) => {
    try {
      const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...taskData,
          tasklist_id: selectedTaskList,
        }),
      });
      
      const data = await response.json();
      
      // Refresh tasks
      fetchTasks();
      
      // Close the form
      onClose();
      
      // Show success message
      toast({
        title: 'Task created',
        description: 'Your task was successfully created.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      return data;
    } catch (error) {
      console.error('Error creating task:', error);
      
      toast({
        title: 'Error creating task',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      
      throw error;
    }
  };

  // Handle task list selection
  const handleTaskListChange = (index) => {
    if (taskLists[index]) {
      setSelectedTaskList(taskLists[index].id);
    }
  };

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Heading size="lg">Tasks</Heading>
          <Button 
            leftIcon={<AddIcon />} 
            colorScheme="brand" 
            onClick={onOpen}
            isDisabled={!selectedTaskList}
          >
            Add Task
          </Button>
        </Box>

        {taskLists.length > 0 ? (
          <Tabs onChange={handleTaskListChange}>
            <TabList>
              {taskLists.map((list) => (
                <Tab key={list.id}>{list.title}</Tab>
              ))}
            </TabList>

            <TabPanels>
              {taskLists.map((list) => (
                <TabPanel key={list.id} p={0} pt={4}>
                  {isLoading ? (
                    <Box textAlign="center" py={10}>
                      <Spinner size="xl" />
                      <Text mt={4}>Loading tasks...</Text>
                    </Box>
                  ) : (
                    <TaskList 
                      tasks={tasks} 
                      onRefresh={fetchTasks} 
                    />
                  )}
                </TabPanel>
              ))}
            </TabPanels>
          </Tabs>
        ) : (
          <Text>No task lists found.</Text>
        )}
      </VStack>

      <TaskForm
        isOpen={isOpen}
        onClose={onClose}
        onSubmit={createTask}
      />
    </Box>
  );
};

export default TasksPage;
