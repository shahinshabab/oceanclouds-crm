from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Project list/detail
    path("project/", views.ProjectListView.as_view(), name="project_list"),
    path("project/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("project/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("project/<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),

    # ---------- TASKS ---------- #
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("tasks/create/", views.TaskCreateView.as_view(), name="task_create"),  # global +New
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_update"),

    # optional: create task for a specific project from project detail
    path(
        "project/<int:project_pk>/tasks/create/",
        views.TaskCreateView.as_view(),
        name="task_create_for_project",
    ),

    # ---------- DELIVERABLES ---------- #
    path("deliverables/", views.DeliverableListView.as_view(), name="deliverable_list"),
    path(
        "deliverables/create/",
        views.DeliverableCreateView.as_view(),     # ✅ NOT TaskCreateView
        name="deliverable_create",
    ),
    path(
        "deliverables/<int:pk>/",
        views.DeliverableDetailView.as_view(),
        name="deliverable_detail",
    ),
    path(
        "deliverables/<int:pk>/edit/",
        views.DeliverableUpdateView.as_view(),
        name="deliverable_update",
    ),
    path(
        "project/<int:project_pk>/deliverables/create/",
        views.DeliverableCreateView.as_view(),
        name="deliverable_create_for_project",
    ),

    # Kanban
    path("project/kanban/", views.ProjectKanbanView.as_view(), name="project_kanban"),
    path("tasks/kanban/", views.TaskKanbanView.as_view(), name="task_kanban"),
    path("deliverables/kanban/", views.DeliverableKanbanView.as_view(), name="deliverable_kanban"),
    path("deliverables/<int:pk>/set-status/", views.DeliverableStatusUpdateView.as_view(), name="deliverable_set_status"),

    # AJAX status endpoints
    path(
        "projects/<int:pk>/set-status/",
        views.ProjectStatusUpdateView.as_view(),
        name="project_set_status",
    ),
    path(
        "tasks/<int:pk>/set-status/",
        views.TaskStatusUpdateView.as_view(),
        name="task_set_status",
    ),
    path("ajax/load-tasks/", views.ajax_load_tasks, name="ajax_load_tasks"),
    path(
        "overview/<int:pk>/",
        views.ProjectOverviewView.as_view(),
        name="project_overview",
    ),
]
