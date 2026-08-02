from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.utils import timezone

from common.models import UserLoginSession, UserSessionEndReason
from common.test_helpers import AuthenticatedViewTestMixin, make_user
from projects.models import WorkSession

from .utils import _build_attendance_summary, _build_login_month_table, _format_seconds_hm


class ReportsViewTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "reports:dashboard",
        "reports:sales_report",
        "reports:project_report",
        "reports:employee_work_report",
    ]


class EmployeeReportAttendanceTests(TestCase):
    @override_settings(TIME_ZONE="Asia/Kolkata", USE_TZ=True)
    def test_attendance_counts_only_manual_logout_days_with_eight_hours(self):
        user = make_user(username="attendance-user")
        kolkata = ZoneInfo("Asia/Kolkata")

        def aware(year, month, day, hour, minute=0):
            return timezone.make_aware(
                datetime(year, month, day, hour, minute),
                kolkata,
            )

        UserLoginSession.objects.create(
            user=user,
            session_key="seven-hours",
            login_at=aware(2026, 7, 1, 9),
            logout_at=aware(2026, 7, 1, 16),
            end_reason=UserSessionEndReason.LOGOUT,
        )
        UserLoginSession.objects.create(
            user=user,
            session_key="manual-part-one",
            login_at=aware(2026, 7, 2, 9),
            logout_at=aware(2026, 7, 2, 13),
            end_reason=UserSessionEndReason.LOGOUT,
        )
        UserLoginSession.objects.create(
            user=user,
            session_key="manual-part-two",
            login_at=aware(2026, 7, 2, 14),
            logout_at=aware(2026, 7, 2, 18),
            end_reason=UserSessionEndReason.LOGOUT,
        )
        UserLoginSession.objects.create(
            user=user,
            session_key="auto-timeout",
            login_at=aware(2026, 7, 3, 9),
            logout_at=aware(2026, 7, 3, 18),
            end_reason=UserSessionEndReason.AUTO_TIMEOUT,
        )

        summary = _build_attendance_summary(
            UserLoginSession.objects.filter(user=user),
            datetime(2026, 7, 1).date(),
            datetime(2026, 7, 3).date(),
        )

        self.assertEqual(summary["attendance_days"], 1)
        self.assertEqual(summary["days"][0]["date"], datetime(2026, 7, 2).date())
        self.assertEqual(summary["days"][0]["hm"], "8h 0m")

    def test_hm_formatter_uses_sixty_minutes_per_hour(self):
        self.assertEqual(_format_seconds_hm(100 * 60), "1h 40m")

    @override_settings(TIME_ZONE="Asia/Kolkata", USE_TZ=True, AUTO_LOGOUT_IDLE_SECONDS=3 * 60 * 60)
    def test_auto_timeout_reports_used_time_after_idle_window(self):
        user = make_user(username="auto-timeout-report-user")
        kolkata = ZoneInfo("Asia/Kolkata")
        login_at = timezone.make_aware(datetime(2026, 7, 4, 9), kolkata)
        logout_at = timezone.make_aware(datetime(2026, 7, 4, 18), kolkata)
        UserLoginSession.objects.create(
            user=user,
            session_key="auto-timeout-nine-hours",
            login_at=login_at,
            logout_at=logout_at,
            end_reason=UserSessionEndReason.AUTO_TIMEOUT,
        )

        table = _build_login_month_table(
            UserLoginSession.objects.filter(user=user),
            work_sessions_qs=WorkSession.objects.none(),
            date_from=datetime(2026, 7, 4).date(),
            date_to=datetime(2026, 7, 4).date(),
        )

        self.assertEqual(table["rows"][0]["logged_hm"], "6h 0m")
        self.assertEqual(table["rows"][0]["idle_hm"], "3h 0m")
        self.assertEqual(table["total_login_hm"], "6h 0m")
