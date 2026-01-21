# ui/urls.py
from django.urls import path
from . import views

app_name = "ui"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.ProfileDetailView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
    path("profile/password/", views.ProfilePasswordChangeView.as_view(), name="profile_password"),
]
