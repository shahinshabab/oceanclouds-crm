# common/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .roles import (
    CRM_ACCESS_ROLES,
    SALES_ACCESS_ROLES,
    PROJECT_ACCESS_ROLES,
    PROJECT_WORK_ACCESS_ROLES,
    INQUIRY_ACCESS_ROLES,
    INQUIRY_MANAGE_ROLES,
    user_has_role,
)


class RolesRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = []
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, *self.allowed_roles)


class CRMAccessMixin(RolesRequiredMixin):
    """
    Use for:
    - Clients
    - Contacts
    - Leads
    - Client Reviews
    - CRM dashboard

    Access:
    - Admin
    - CRM Manager
    """
    allowed_roles = CRM_ACCESS_ROLES


class SalesAccessMixin(RolesRequiredMixin):
    """
    Use for:
    - Deals
    - Proposals
    - Contracts
    - Invoices
    - Payments

    Access:
    - Admin
    - CRM Manager
    """
    allowed_roles = SALES_ACCESS_ROLES


class ProjectAccessMixin(RolesRequiredMixin):
    """
    Use for:
    - Project list
    - Project detail
    - Project create/update
    - Project overview
    - Project kanban

    Access:
    - Admin
    - Project Manager

    Employees should NOT access project pages directly.
    CRM Manager should NOT access project pages.
    """
    allowed_roles = PROJECT_ACCESS_ROLES


class ProjectWorkAccessMixin(RolesRequiredMixin):
    """
    Use for:
    - Task list/detail/kanban/status
    - Deliverable list/detail/kanban/status
    - Work sessions

    Access:
    - Admin
    - Project Manager
    - Employee
    """
    allowed_roles = PROJECT_WORK_ACCESS_ROLES


class InquiryAccessMixin(RolesRequiredMixin):
    """
    Everyone can see/create inquiries.

    Access:
    - Admin
    - CRM Manager
    - Project Manager
    - Employee
    """
    allowed_roles = INQUIRY_ACCESS_ROLES


class InquiryManageMixin(RolesRequiredMixin):
    """
    Admin, CRM Manager, and Project Manager can edit/delete inquiries.
    """
    allowed_roles = INQUIRY_MANAGE_ROLES


# Backward compatibility with old names
class AdminCRMManagerMixin(CRMAccessMixin):
    pass


class AdminManagerMixin(CRMAccessMixin):
    """
    Old name kept only for old CRM/Sales views.
    Do not use this in project app anymore.
    """
    pass


class StaffAllMixin(InquiryAccessMixin):
    pass


class InquiryManagerMixin(InquiryManageMixin):
    pass