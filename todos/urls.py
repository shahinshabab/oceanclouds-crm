# todos/urls.py

from django.urls import path

from todos.views import (
    TodoListView,
    TodoDetailView,
    TodoCreateView,
    TodoUpdateView,
    TodoDeleteView,
    TodoCompleteView,
    TodoReopenView,
    TodoCancelView,
)

app_name = "todos"

urlpatterns = [
    path("", TodoListView.as_view(), name="todo_list"),
    path("new/", TodoCreateView.as_view(), name="todo_create"),
    path("<int:pk>/", TodoDetailView.as_view(), name="todo_detail"),
    path("<int:pk>/edit/", TodoUpdateView.as_view(), name="todo_update"),
    path("<int:pk>/delete/", TodoDeleteView.as_view(), name="todo_delete"),

    path("<int:pk>/complete/", TodoCompleteView.as_view(), name="todo_complete"),
    path("<int:pk>/reopen/", TodoReopenView.as_view(), name="todo_reopen"),
    path("<int:pk>/cancel/", TodoCancelView.as_view(), name="todo_cancel"),
]