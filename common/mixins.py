# common/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .roles import (
    CRM_ACCESS_ROLES,
    SALES_ACCESS_ROLES,
    PROJECT_ACCESS_ROLES,
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
    """
    allowed_roles = SALES_ACCESS_ROLES


class ProjectAccessMixin(RolesRequiredMixin):
    """
    Use for:
    - Projects
    - Tasks
    - Project workflow
    """
    allowed_roles = PROJECT_ACCESS_ROLES


class InquiryAccessMixin(RolesRequiredMixin):
    """
    Everyone can see/create inquiries.
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
    pass


class StaffAllMixin(InquiryAccessMixin):
    pass


class InquiryManagerMixin(InquiryManageMixin):
    pass