from django.urls import re_path

from . import views

app_name = "df_order"

urlpatterns = [
    re_path(r"^$", views.order, name="order"),
    re_path(r"^push/$", views.order_handle, name="push"),
]
