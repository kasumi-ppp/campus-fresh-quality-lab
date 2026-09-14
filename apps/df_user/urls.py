from django.urls import re_path

from . import views

app_name = "df_user"

urlpatterns = [
    re_path(r"^register/$", views.register, name="register"),
    re_path(r"^register_handle/$", views.register_handle, name="register_handle"),
    re_path(r"^register_exist/$", views.register_exist, name="register_exist"),
    re_path(r"^login/$", views.login, name="login"),
    re_path(r"^login_handle/$", views.login_handle, name="login_handle"),
    re_path(r"^info/$", views.info, name="info"),
    re_path(r"^order/(\d+)$", views.order, name="order"),
    re_path(r"^site/$", views.site, name="site"),
    re_path(r"^logout/$", views.logout, name="logout"),
]
