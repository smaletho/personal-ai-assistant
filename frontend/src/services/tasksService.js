/**
 * Tasks Service
 * Centralizes all API calls related to task management functionality
 */
import apiClient from './api';

const BASE_PATH = '/tasks';

/**
 * Tasks service object for handling all task-related API calls
 */
export const tasksService = {
  /**
   * List available task lists
   * @returns {Promise<Array>} Array of task list objects
   */
  async listTaskLists() {
    try {
      const response = await apiClient.get(`${BASE_PATH}/lists`);
      return response.data.tasklists || [];
    } catch (error) {
      console.error('Error fetching task lists:', error);
      throw error;
    }
  },

  /**
   * List tasks from a task list
   * @param {Object} params - Query parameters
   * @param {string} [params.tasklist_id] - Task list ID (optional)
   * @returns {Promise<Array>} Array of task objects
   */
  async listTasks(params = {}) {
    try {
      const response = await apiClient.get(BASE_PATH, { params });
      return response.data.tasks || [];
    } catch (error) {
      console.error('Error fetching tasks:', error);
      throw error;
    }
  },

  /**
   * Get upcoming tasks for the next X days
   * @param {number} [days=7] - Number of days to look ahead
   * @param {string} [tasklistId] - Task list ID (optional)
   * @returns {Promise<Array>} Array of upcoming task objects
   */
  async getUpcomingTasks(days = 7, tasklistId = null) {
    try {
      const params = { days };
      if (tasklistId) params.tasklist_id = tasklistId;
      
      const response = await apiClient.get(`${BASE_PATH}/upcoming`, { params });
      return response.data.tasks || [];
    } catch (error) {
      console.error('Error fetching upcoming tasks:', error);
      throw error;
    }
  },

  /**
   * Create a new task
   * @param {Object} taskData - Task data
   * @param {string} taskData.title - Task title
   * @param {string} [taskData.notes] - Task notes/description
   * @param {string} [taskData.due_date] - Due date in ISO format
   * @param {string} [taskData.tasklist_id] - Task list ID (optional)
   * @returns {Promise<Object>} Created task object
   */
  async createTask(taskData) {
    try {
      const response = await apiClient.post(BASE_PATH, taskData);
      return response.data.task || {};
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    }
  },

  /**
   * Update an existing task
   * @param {string} tasklistId - Task list ID
   * @param {string} taskId - Task ID to update
   * @param {Object} taskData - Updated task data
   * @param {string} [taskData.title] - Updated title
   * @param {string} [taskData.notes] - Updated notes
   * @param {string} [taskData.due_date] - Updated due date
   * @param {string} [taskData.status] - Updated status
   * @returns {Promise<Object>} Updated task object
   */
  async updateTask(tasklistId, taskId, taskData) {
    try {
      const response = await apiClient.put(`${BASE_PATH}/${tasklistId}/${taskId}`, taskData);
      return response.data.task || {};
    } catch (error) {
      console.error('Error updating task:', error);
      throw error;
    }
  },

  /**
   * Delete a task
   * @param {string} tasklistId - Task list ID
   * @param {string} taskId - Task ID to delete
   * @returns {Promise<Object>} Response data
   */
  async deleteTask(tasklistId, taskId) {
    try {
      const response = await apiClient.delete(`${BASE_PATH}/${tasklistId}/${taskId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting task:', error);
      throw error;
    }
  },

  /**
   * Mark a task as completed
   * @param {string} tasklistId - Task list ID
   * @param {string} taskId - Task ID to complete
   * @returns {Promise<Object>} Updated task object
   */
  async completeTask(tasklistId, taskId) {
    try {
      const response = await apiClient.put(`${BASE_PATH}/${tasklistId}/${taskId}`, {
        status: 'completed'
      });
      return response.data.task || {};
    } catch (error) {
      console.error('Error completing task:', error);
      throw error;
    }
  },
  
  /**
   * Execute a confirmed task operation
   * This bypasses the agent and directly calls the appropriate tasks API
   * @param {Object} operationData - Operation data
   * @param {string} operationData.operation - Operation type (create_task, update_task, delete_task, complete_task)
   * @param {Object} operationData.details - Operation parameters
   * @returns {Promise<Object>} Operation result
   */
  async executeConfirmedOperation(operationData) {
    try {
      const response = await apiClient.post(`${BASE_PATH}/confirmed-operation`, operationData);
      return response.data;
    } catch (error) {
      console.error('Error executing confirmed operation:', error);
      throw error;
    }
  }
};

export default tasksService;
