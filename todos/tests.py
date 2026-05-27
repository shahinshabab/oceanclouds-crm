from datetime import timedelta

from django.utils import timezone

from common.test_helpers import AuthenticatedViewTestMixin, make_user

from .forms import TodoForm
from .models import Todo, TodoStatus


class TodoTests(AuthenticatedViewTestMixin):
    list_url_names = ["todos:todo_list"]

    def test_todo_status_helpers_and_transitions(self):
        todo = Todo.objects.create(title="Follow up")

        self.assertTrue(todo.is_open)
        self.assertFalse(todo.is_completed)

        todo.mark_completed()
        todo.refresh_from_db()
        self.assertTrue(todo.is_completed)
        self.assertIsNotNone(todo.completed_at)

        todo.reopen()
        todo.refresh_from_db()
        self.assertEqual(todo.status, TodoStatus.PENDING)
        self.assertIsNone(todo.completed_at)

        todo.cancel()
        todo.refresh_from_db()
        self.assertTrue(todo.is_cancelled)

    def test_todo_overdue_ignores_completed_items(self):
        todo = Todo.objects.create(
            title="Old task",
            due_date=timezone.localdate() - timedelta(days=1),
        )

        self.assertTrue(todo.is_overdue)
        todo.mark_completed()
        todo.refresh_from_db()
        self.assertFalse(todo.is_overdue)

    def test_todo_form_accepts_minimal_valid_data(self):
        assignee = make_user(username="todo-assignee")
        form = TodoForm(
            data={
                "title": "Call client",
                "description": "",
                "assigned_to": assignee.pk,
                "status": TodoStatus.PENDING,
                "priority": "medium",
                "due_date": "",
                "project": "",
                "task": "",
                "deliverable": "",
                "client": "",
                "lead": "",
                "deal": "",
                "proposal": "",
                "contract": "",
                "invoice": "",
                "event": "",
                "checklist_item": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
