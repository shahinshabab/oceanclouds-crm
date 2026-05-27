from common.test_helpers import AuthenticatedViewTestMixin


class ReportsViewTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "reports:dashboard",
        "reports:sales_report",
        "reports:project_report",
        "reports:employee_work_report",
    ]
