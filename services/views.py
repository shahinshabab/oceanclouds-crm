# services/views.py
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.shortcuts import redirect

from common.mixins import AdminManagerMixin  # 👈 ensures only Admin/Manager can access

from .models import (
    Vendor,
    Service,
    Package,
    InventoryItem,
    ServiceCategory,
    VendorType,
)
from .forms import (
    VendorForm,
    ServiceForm,
    PackageForm,
    PackageItemFormSet,
    InventoryItemForm,
)


# -------- Vendors -------- #

class VendorListView(AdminManagerMixin, ListView):
    model = Vendor
    template_name = "services/vendor_list.html"
    context_object_name = "vendors"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        q = self.request.GET.get("q", "").strip()
        vendor_type = self.request.GET.get("vendor_type", "").strip()
        preferred = self.request.GET.get("preferred", "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(company_name__icontains=q)
            )

        if vendor_type:
            qs = qs.filter(vendor_type=vendor_type)

        if preferred == "yes":
            qs = qs.filter(is_preferred=True)
        elif preferred == "no":
            qs = qs.filter(is_preferred=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["vendor_type"] = self.request.GET.get("vendor_type", "").strip()
        context["preferred"] = self.request.GET.get("preferred", "").strip()
        context["vendor_type_choices"] = VendorType.choices
        return context


class VendorDetailView(AdminManagerMixin, DetailView):
    model = Vendor
    template_name = "services/vendor_detail.html"
    context_object_name = "vendor"


class VendorCreateView(AdminManagerMixin, CreateView):
    model = Vendor
    form_class = VendorForm
    template_name = "services/vendor_form.html"
    success_url = reverse_lazy("services:vendor_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class VendorUpdateView(AdminManagerMixin, UpdateView):
    model = Vendor
    form_class = VendorForm
    template_name = "services/vendor_form.html"
    success_url = reverse_lazy("services:vendor_list")


# -------- Services -------- #

class ServiceListView(AdminManagerMixin, ListView):
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("vendors")

        q = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category", "").strip()
        is_active = self.request.GET.get("is_active", "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q)
            )

        if category:
            qs = qs.filter(category=category)

        if is_active == "active":
            qs = qs.filter(is_active=True)
        elif is_active == "inactive":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["category"] = self.request.GET.get("category", "").strip()
        context["is_active"] = self.request.GET.get("is_active", "").strip()
        context["category_choices"] = ServiceCategory.choices
        return context


class ServiceDetailView(AdminManagerMixin, DetailView):
    model = Service
    template_name = "services/service_detail.html"
    context_object_name = "service"


class ServiceCreateView(AdminManagerMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("services:service_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ServiceUpdateView(AdminManagerMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("services:service_list")


# -------- Packages -------- #

class PackageListView(AdminManagerMixin, ListView):
    model = Package
    template_name = "services/package_list.html"
    context_object_name = "packages"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        q = self.request.GET.get("q", "").strip()
        is_active = self.request.GET.get("is_active", "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q)
            )

        if is_active == "active":
            qs = qs.filter(is_active=True)
        elif is_active == "inactive":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["is_active"] = self.request.GET.get("is_active", "").strip()
        return context


class PackageDetailView(AdminManagerMixin, DetailView):
    model = Package
    template_name = "services/package_detail.html"
    context_object_name = "package"


class PackageCreateView(AdminManagerMixin, CreateView):
    model = Package
    form_class = PackageForm
    template_name = "services/package_form.html"
    success_url = reverse_lazy("services:package_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["items_formset"] = PackageItemFormSet(
                self.request.POST,
                prefix="items",
            )
        else:
            context["items_formset"] = PackageItemFormSet(prefix="items")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context["items_formset"]

        form.instance.owner = self.request.user

        if items_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            self.object.recalculate_total()
            return redirect(self.get_success_url())

        # if formset invalid, re-render with errors
        return self.render_to_response(self.get_context_data(form=form))


class PackageUpdateView(AdminManagerMixin, UpdateView):
    model = Package
    form_class = PackageForm
    template_name = "services/package_form.html"
    success_url = reverse_lazy("services:package_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["items_formset"] = PackageItemFormSet(
                self.request.POST,
                instance=self.object,
                prefix="items",
            )
        else:
            context["items_formset"] = PackageItemFormSet(
                instance=self.object,
                prefix="items",
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context["items_formset"]

        form.instance.owner = self.request.user

        if items_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            self.object.recalculate_total()
            return redirect(self.get_success_url())

        return self.render_to_response(self.get_context_data(form=form))


# -------- Inventory Items -------- #

class InventoryItemListView(AdminManagerMixin, ListView):
    model = InventoryItem
    template_name = "services/inventory_list.html"
    context_object_name = "inventory_items"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("service")

        q = self.request.GET.get("q", "").strip()
        service_id = self.request.GET.get("service", "").strip()
        stock_status = self.request.GET.get("stock_status", "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q)
            )

        if service_id:
            qs = qs.filter(service_id=service_id)

        if stock_status == "in_stock":
            qs = qs.filter(quantity_available__gt=0)
        elif stock_status == "out_of_stock":
            qs = qs.filter(quantity_available__lte=0)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["service_filter"] = self.request.GET.get("service", "").strip()
        context["stock_status"] = self.request.GET.get("stock_status", "").strip()
        context["service_choices"] = Service.objects.order_by("name")
        return context


class InventoryItemDetailView(AdminManagerMixin, DetailView):
    model = InventoryItem
    template_name = "services/inventory_detail.html"
    context_object_name = "inventory_item"


class InventoryItemCreateView(AdminManagerMixin, CreateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "services/inventory_form.html"
    success_url = reverse_lazy("services:inventory_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class InventoryItemUpdateView(AdminManagerMixin, UpdateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "services/inventory_form.html"
    success_url = reverse_lazy("services:inventory_list")
