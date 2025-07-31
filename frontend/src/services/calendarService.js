/**
 * Calendar Service
 * Centralizes all API calls related to calendar functionality
 */
import apiClient from './api';

const BASE_PATH = '/calendar';

/**
 * Calendar service object for handling all calendar-related API calls
 */
export const calendarService = {
  /**
   * List available calendars
   * @returns {Promise<Array>} Array of calendar objects
   */
  async listCalendars() {
    try {
      const response = await apiClient.get(BASE_PATH);
      return response.data.calendars || [];
    } catch (error) {
      console.error('Error fetching calendars:', error);
      throw error;
    }
  },

  /**
   * List events from a calendar
   * @param {Object} params - Query parameters
   * @param {string} [params.calendar_id='primary'] - Calendar ID
   * @param {number} [params.max_results=10] - Maximum number of events to return
   * @param {string} [params.time_min] - Start time in ISO format
   * @param {string} [params.time_max] - End time in ISO format
   * @returns {Promise<Array>} Array of event objects
   */
  async listEvents(params = {}) {
    try {
      const response = await apiClient.get(`${BASE_PATH}/events`, { params });
      return response.data.events || [];
    } catch (error) {
      console.error('Error fetching events:', error);
      throw error;
    }
  },

  /**
   * Create a new calendar event
   * @param {Object} eventData - Event data
   * @param {string} eventData.summary - Event title
   * @param {string} eventData.start_time - Start time in ISO format
   * @param {string} eventData.end_time - End time in ISO format
   * @param {string} [eventData.description] - Event description
   * @param {string} [eventData.location] - Event location
   * @param {string} [eventData.calendar_id='primary'] - Calendar ID
   * @returns {Promise<Object>} Created event object
   */
  async createEvent(eventData) {
    try {
      const response = await apiClient.post(`${BASE_PATH}/events`, eventData);
      return response.data.event || {};
    } catch (error) {
      console.error('Error creating event:', error);
      throw error;
    }
  },

  /**
   * Delete a calendar event
   * @param {string} eventId - ID of the event to delete
   * @param {string} [calendarId='primary'] - Calendar ID
   * @returns {Promise<Object>} Response data
   */
  async deleteEvent(eventId, calendarId = 'primary') {
    try {
      const response = await apiClient.delete(`${BASE_PATH}/events/${eventId}`, {
        params: { calendar_id: calendarId }
      });
      return response.data;
    } catch (error) {
      console.error('Error deleting event:', error);
      throw error;
    }
  },

  /**
   * Get the next upcoming event
   * @param {string} [calendarId='primary'] - Calendar ID
   * @returns {Promise<Object>} Next event object or null
   */
  async getNextEvent(calendarId = 'primary') {
    try {
      const response = await apiClient.get(`${BASE_PATH}/next`, {
        params: { calendar_id: calendarId }
      });
      return response.data.event || null;
    } catch (error) {
      console.error('Error fetching next event:', error);
      throw error;
    }
  },
  
  /**
   * Execute a confirmed calendar operation
   * This bypasses the agent and directly calls the appropriate calendar API
   * @param {Object} operationData - Operation data
   * @param {string} operationData.operation - Operation type (create_event, update_event, delete_event)
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

export default calendarService;
