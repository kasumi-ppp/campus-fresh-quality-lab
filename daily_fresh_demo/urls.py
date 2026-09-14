from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("df_goods.urls", namespace="df_goods")),
    path("user/", include("df_user.urls", namespace="df_user")),
    path("cart/", include("df_cart.urls", namespace="df_cart")),
    path("order/", include("df_order.urls", namespace="df_order")),
    path("tinymce/", include("tinymce.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
