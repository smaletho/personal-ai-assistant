"""
Mock objects for testing API integrations.
"""
import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock


class MockCalendarService:
    """Mock for Google Calendar service."""
    
    def __init__(self):
        """Initialize with mock data."""
        self.events = {}
        self.calendars = {
            'primary': {'id': 'primary', 'summary': 'Primary Calendar'},
            'family': {'id': 'family', 'summary': 'Family Calendar'},
            'work': {'id': 'work', 'summary': 'Work Calendar'}
        }
        
        # Add some sample events
        self.add_sample_events()
    
    def add_sample_events(self):
        """Add sample events for testing."""
        self.events = {
            'event1': {
                'id': 'event1',
                'summary': 'Team Meeting',
                'description': 'Weekly team sync',
                'start': {'dateTime': '2023-07-01T10:00:00Z'},
                'end': {'dateTime': '2023-07-01T11:00:00Z'},
                'location': 'Conference Room',
                'calendarId': 'primary'
            },
            'event2': {
                'id': 'event2',
                'summary': 'Dentist Appointment',
                'start': {'dateTime': '2023-07-02T14:00:00Z'},
                'end': {'dateTime': '2023-07-02T15:00:00Z'},
                'location': 'Dental Clinic',
                'calendarId': 'primary'
            },
            'event3': {
                'id': 'event3',
                'summary': 'Family Dinner',
                'start': {'dateTime': '2023-07-03T18:00:00Z'},
                'end': {'dateTime': '2023-07-03T20:00:00Z'},
                'location': 'Home',
                'calendarId': 'family'
            }
        }
    
    def events(self):
        """Mock events() resource."""
        events_resource = MagicMock()
        
        # Mock insert method
        def insert_mock(calendarId, body):
            execute_mock = MagicMock()
            event_id = f"new_event_{len(self.events) + 1}"
            
            def execute():
                new_event = body.copy()
                new_event['id'] = event_id
                new_event['calendarId'] = calendarId
                self.events[event_id] = new_event
                return new_event
            
            execute_mock.execute = execute
            return execute_mock
        
        events_resource.insert = insert_mock
        
        # Mock get method
        def get_mock(calendarId, eventId):
            execute_mock = MagicMock()
            
            def execute():
                if eventId in self.events and self.events[eventId].get('calendarId') == calendarId:
                    return self.events[eventId]
                raise Exception(f"Event {eventId} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        events_resource.get = get_mock
        
        # Mock update method
        def update_mock(calendarId, eventId, body):
            execute_mock = MagicMock()
            
            def execute():
                if eventId in self.events and self.events[eventId].get('calendarId') == calendarId:
                    updated_event = body.copy()
                    updated_event['id'] = eventId
                    updated_event['calendarId'] = calendarId
                    self.events[eventId] = updated_event
                    return updated_event
                raise Exception(f"Event {eventId} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        events_resource.update = update_mock
        
        # Mock delete method
        def delete_mock(calendarId, eventId):
            execute_mock = MagicMock()
            
            def execute():
                if eventId in self.events and self.events[eventId].get('calendarId') == calendarId:
                    del self.events[eventId]
                    return {}
                raise Exception(f"Event {eventId} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        events_resource.delete = delete_mock
        
        # Mock list method
        def list_mock(calendarId, **kwargs):
            execute_mock = MagicMock()
            
            def execute():
                filtered_events = []
                for event_id, event in self.events.items():
                    if event.get('calendarId') == calendarId:
                        filtered_events.append(event)
                
                return {'items': filtered_events}
            
            execute_mock.execute = execute
            return execute_mock
        
        events_resource.list = list_mock
        
        return events_resource
    
    def freebusy(self):
        """Mock freebusy() resource."""
        freebusy_resource = MagicMock()
        
        def query_mock(body):
            execute_mock = MagicMock()
            
            def execute():
                calendar_id = body['items'][0]['id']
                time_min = body['timeMin']
                time_max = body['timeMax']
                
                busy_periods = []
                for event in self.events.values():
                    if event.get('calendarId') == calendar_id:
                        event_start = event['start']['dateTime']
                        event_end = event['end']['dateTime']
                        if (event_start >= time_min and event_start < time_max) or \
                           (event_end > time_min and event_end <= time_max):
                            busy_periods.append({
                                'start': event_start,
                                'end': event_end
                            })
                
                return {
                    'calendars': {
                        calendar_id: {
                            'busy': busy_periods
                        }
                    }
                }
            
            execute_mock.execute = execute
            return execute_mock
        
        freebusy_resource.query = query_mock
        return freebusy_resource


class MockTasksService:
    """Mock for Google Tasks service."""
    
    def __init__(self):
        """Initialize with mock data."""
        self.tasklists = {
            'default': {'id': '@default', 'title': 'My Tasks'}
        }
        self.tasks = {
            '@default': {
                'task1': {
                    'id': 'task1',
                    'title': 'Buy groceries',
                    'notes': 'Milk, eggs, bread',
                    'due': '2023-07-01T18:00:00Z',
                    'status': 'needsAction',
                    'position': '00000000000000000001'
                },
                'task2': {
                    'id': 'task2',
                    'title': 'Call mom',
                    'due': '2023-07-02T12:00:00Z',
                    'status': 'needsAction',
                    'position': '00000000000000000002'
                },
                'task3': {
                    'id': 'task3',
                    'title': 'Pay bills',
                    'status': 'completed',
                    'completed': '2023-06-30T15:00:00Z',
                    'position': '00000000000000000003'
                }
            }
        }
    
    def tasklists(self):
        """Mock tasklists() resource."""
        tasklists_resource = MagicMock()
        
        # Mock list method
        def list_mock():
            execute_mock = MagicMock()
            
            def execute():
                return {'items': list(self.tasklists.values())}
            
            execute_mock.execute = execute
            return execute_mock
        
        tasklists_resource.list = list_mock
        
        # Mock get method
        def get_mock(tasklist):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist in self.tasklists:
                    return self.tasklists[tasklist]
                raise Exception(f"Task list {tasklist} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        tasklists_resource.get = get_mock
        
        # Mock insert method
        def insert_mock(body):
            execute_mock = MagicMock()
            
            def execute():
                title = body.get('title', 'New List')
                list_id = f"list_{len(self.tasklists) + 1}"
                new_list = {
                    'id': list_id,
                    'title': title
                }
                self.tasklists[list_id] = new_list
                self.tasks[list_id] = {}
                return new_list
            
            execute_mock.execute = execute
            return execute_mock
        
        tasklists_resource.insert = insert_mock
        
        # Mock update method
        def update_mock(tasklist, body):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist in self.tasklists:
                    self.tasklists[tasklist]['title'] = body.get('title', self.tasklists[tasklist]['title'])
                    return self.tasklists[tasklist]
                raise Exception(f"Task list {tasklist} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        tasklists_resource.update = update_mock
        
        # Mock delete method
        def delete_mock(tasklist):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist in self.tasklists:
                    del self.tasklists[tasklist]
                    if tasklist in self.tasks:
                        del self.tasks[tasklist]
                    return {}
                raise Exception(f"Task list {tasklist} not found")
            
            execute_mock.execute = execute
            return execute_mock
        
        tasklists_resource.delete = delete_mock
        
        return tasklists_resource
    
    def tasks(self):
        """Mock tasks() resource."""
        tasks_resource = MagicMock()
        
        # Mock list method
        def list_mock(tasklist, **kwargs):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks:
                    raise Exception(f"Task list {tasklist} not found")
                
                tasks = list(self.tasks[tasklist].values())
                
                # Apply filters
                if 'showCompleted' in kwargs and not kwargs['showCompleted']:
                    tasks = [t for t in tasks if t['status'] != 'completed']
                
                # Apply due date filters
                if 'dueMin' in kwargs:
                    tasks = [t for t in tasks if t.get('due', '') >= kwargs['dueMin']]
                if 'dueMax' in kwargs:
                    tasks = [t for t in tasks if t.get('due', '') <= kwargs['dueMax']]
                
                return {'items': tasks}
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.list = list_mock
        
        # Mock get method
        def get_mock(tasklist, task):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks or task not in self.tasks[tasklist]:
                    raise Exception(f"Task {task} not found in list {tasklist}")
                return self.tasks[tasklist][task]
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.get = get_mock
        
        # Mock insert method
        def insert_mock(tasklist, body, **kwargs):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks:
                    raise Exception(f"Task list {tasklist} not found")
                
                task_id = f"task_{len(self.tasks[tasklist]) + 1}"
                new_task = body.copy()
                new_task['id'] = task_id
                
                if 'status' not in new_task:
                    new_task['status'] = 'needsAction'
                
                position = str(len(self.tasks[tasklist]) + 1).zfill(20)
                new_task['position'] = position
                
                self.tasks[tasklist][task_id] = new_task
                return new_task
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.insert = insert_mock
        
        # Mock update method
        def update_mock(tasklist, task, body):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks or task not in self.tasks[tasklist]:
                    raise Exception(f"Task {task} not found in list {tasklist}")
                
                updated_task = body.copy()
                updated_task['id'] = task
                
                # Preserve position if not in update
                if 'position' not in updated_task and 'position' in self.tasks[tasklist][task]:
                    updated_task['position'] = self.tasks[tasklist][task]['position']
                
                self.tasks[tasklist][task] = updated_task
                return updated_task
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.update = update_mock
        
        # Mock delete method
        def delete_mock(tasklist, task):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks or task not in self.tasks[tasklist]:
                    raise Exception(f"Task {task} not found in list {tasklist}")
                
                del self.tasks[tasklist][task]
                return {}
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.delete = delete_mock
        
        # Mock clear method
        def clear_mock(tasklist):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks:
                    raise Exception(f"Task list {tasklist} not found")
                
                # Remove all completed tasks
                task_ids = list(self.tasks[tasklist].keys())
                for task_id in task_ids:
                    if self.tasks[tasklist][task_id]['status'] == 'completed':
                        del self.tasks[tasklist][task_id]
                
                return {}
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.clear = clear_mock
        
        # Mock move method
        def move_mock(tasklist, task, **kwargs):
            execute_mock = MagicMock()
            
            def execute():
                if tasklist not in self.tasks or task not in self.tasks[tasklist]:
                    raise Exception(f"Task {task} not found in list {tasklist}")
                
                # In a real implementation, this would handle parent/previous params
                # but for mocking purposes, we'll just return the task
                return self.tasks[tasklist][task]
            
            execute_mock.execute = execute
            return execute_mock
        
        tasks_resource.move = move_mock
        
        return tasks_resource
