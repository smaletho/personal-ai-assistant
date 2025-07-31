"""
Unit tests for Google Tasks API wrapper.
"""
import unittest
from unittest.mock import patch, MagicMock
import datetime
from freezegun import freeze_time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_tasks import GoogleTasks
from tests.test_mocks import MockTasksService


class TestGoogleTasks(unittest.TestCase):
    """Test the GoogleTasks class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.mock_service = MockTasksService()
        patcher = patch('auth.get_calendar_service')
        self.mock_get_service = patcher.start()
        self.mock_get_service.return_value = self.mock_service
        self.addCleanup(patcher.stop)
        
        self.tasks = GoogleTasks(account_name='default')
    
    def test_init(self):
        """Test initialization of GoogleTasks."""
        self.mock_get_service.assert_called_once()
        self.assertIsNotNone(self.tasks.tasks_service)
    
    def test_list_tasklists(self):
        """Test listing task lists."""
        tasklists = self.tasks.list_tasklists()
        
        self.assertIsInstance(tasklists, list)
        self.assertGreaterEqual(len(tasklists), 1)
        self.assertEqual(tasklists[0]['id'], '@default')
    
    def test_get_tasklist(self):
        """Test getting a specific task list."""
        tasklist = self.tasks.get_tasklist('@default')
        
        self.assertEqual(tasklist['id'], '@default')
        self.assertEqual(tasklist['title'], 'My Tasks')
    
    def test_create_tasklist(self):
        """Test creating a new task list."""
        tasklist = self.tasks.create_tasklist('New List')
        
        self.assertIsNotNone(tasklist)
        self.assertIn('id', tasklist)
        self.assertEqual(tasklist['title'], 'New List')
    
    def test_update_tasklist(self):
        """Test updating a task list."""
        # First create a tasklist
        tasklist = self.tasks.create_tasklist('Test List')
        tasklist_id = tasklist['id']
        
        # Now update it
        updated = self.tasks.update_tasklist(tasklist_id, 'Updated List')
        
        self.assertEqual(updated['id'], tasklist_id)
        self.assertEqual(updated['title'], 'Updated List')
    
    def test_delete_tasklist(self):
        """Test deleting a task list."""
        # First create a tasklist
        tasklist = self.tasks.create_tasklist('Test List')
        tasklist_id = tasklist['id']
        
        # Now delete it
        result = self.tasks.delete_tasklist(tasklist_id)
        
        self.assertTrue(result)
        
        # Try to get the deleted tasklist - should raise an exception
        with self.assertRaises(Exception):
            self.tasks.get_tasklist(tasklist_id)
    
    def test_list_tasks(self):
        """Test listing tasks in a task list."""
        tasks = self.tasks.list_tasks('@default')
        
        self.assertIsInstance(tasks, list)
        self.assertGreaterEqual(len(tasks), 3)  # Based on our mock data
    
    def test_list_tasks_filtering(self):
        """Test listing tasks with filtering."""
        # Get only completed tasks
        completed_tasks = self.tasks.list_tasks('@default', completed=True)
        for task in completed_tasks:
            self.assertEqual(task['status'], 'completed')
        
        # Get only uncompleted tasks
        uncompleted_tasks = self.tasks.list_tasks('@default', completed=False)
        for task in uncompleted_tasks:
            self.assertEqual(task['status'], 'needsAction')
    
    def test_get_task(self):
        """Test getting a specific task."""
        task = self.tasks.get_task('@default', 'task1')
        
        self.assertEqual(task['id'], 'task1')
        self.assertEqual(task['title'], 'Buy groceries')
    
    def test_create_task(self):
        """Test creating a new task."""
        task = self.tasks.create_task(
            tasklist_id='@default',
            title='Test Task',
            notes='Test Notes',
            due='2023-07-10T10:00:00Z'
        )
        
        self.assertIsNotNone(task)
        self.assertIn('id', task)
        self.assertEqual(task['title'], 'Test Task')
        self.assertEqual(task['notes'], 'Test Notes')
        self.assertEqual(task['due'], '2023-07-10T10:00:00Z')
        self.assertEqual(task['status'], 'needsAction')
    
    def test_update_task(self):
        """Test updating a task."""
        # First create a task
        task = self.tasks.create_task(
            tasklist_id='@default',
            title='Test Task'
        )
        task_id = task['id']
        
        # Now update it
        updated = self.tasks.update_task(
            tasklist_id='@default',
            task_id=task_id,
            title='Updated Task',
            notes='Updated Notes'
        )
        
        self.assertEqual(updated['id'], task_id)
        self.assertEqual(updated['title'], 'Updated Task')
        self.assertEqual(updated['notes'], 'Updated Notes')
    
    def test_delete_task(self):
        """Test deleting a task."""
        # First create a task
        task = self.tasks.create_task(
            tasklist_id='@default',
            title='Test Task'
        )
        task_id = task['id']
        
        # Now delete it
        result = self.tasks.delete_task('@default', task_id)
        
        self.assertTrue(result)
        
        # Try to get the deleted task - should raise an exception
        with self.assertRaises(Exception):
            self.tasks.get_task('@default', task_id)
    
    def test_complete_task(self):
        """Test marking a task as completed."""
        # First create a task
        task = self.tasks.create_task(
            tasklist_id='@default',
            title='Test Task'
        )
        task_id = task['id']
        
        # Now complete it
        completed = self.tasks.complete_task('@default', task_id)
        
        self.assertEqual(completed['status'], 'completed')
        self.assertIn('completed', completed)
    
    def test_clear_completed(self):
        """Test clearing completed tasks."""
        # First create and complete a task
        task = self.tasks.create_task(
            tasklist_id='@default',
            title='Test Task'
        )
        task_id = task['id']
        self.tasks.complete_task('@default', task_id)
        
        # Now clear completed tasks
        result = self.tasks.clear_completed('@default')
        
        self.assertTrue(result)
        
        # Check that the completed task is gone
        tasks = self.tasks.list_tasks('@default')
        task_ids = [t['id'] for t in tasks]
        self.assertNotIn(task_id, task_ids)


if __name__ == '__main__':
    unittest.main()
