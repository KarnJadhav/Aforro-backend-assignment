from django.urls import path

from .views import StoreInventoryView
from orders.views import StoreOrderListView

urlpatterns = [
    path("stores/<int:store_id>/inventory/", StoreInventoryView.as_view(), name="store-inventory"),
    path("stores/<int:store_id>/orders/", StoreOrderListView.as_view(), name="store-orders"),
]
