from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stores.models import Inventory, Store
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderDetailSerializer, StoreOrderListSerializer
from .tasks import send_order_status_notification


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item_map = {item["product_id"]: item["quantity_requested"] for item in data["items"]}

        with transaction.atomic():
            store = get_object_or_404(Store.objects.select_for_update(), pk=data["store_id"])
            inventory_rows = (
                Inventory.objects.select_for_update()
                .select_related("product")
                .filter(store=store, product_id__in=item_map.keys())
            )
            inventory_by_product = {row.product_id: row for row in inventory_rows}

            has_shortage = any(
                product_id not in inventory_by_product
                or inventory_by_product[product_id].quantity < quantity
                for product_id, quantity in item_map.items()
            )
            order = Order.objects.create(
                store=store,
                status=Order.Status.REJECTED if has_shortage else Order.Status.CONFIRMED,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(order=order, product_id=product_id, quantity_requested=quantity)
                    for product_id, quantity in item_map.items()
                ]
            )

            if not has_shortage:
                for product_id, quantity in item_map.items():
                    Inventory.objects.filter(pk=inventory_by_product[product_id].pk).update(
                        quantity=F("quantity") - quantity
                    )

            cache.delete(f"store:{store.pk}:inventory")

        send_order_status_notification.delay(order.pk)
        order = Order.objects.prefetch_related("items__product").get(pk=order.pk)
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)


class StoreOrderListView(APIView):
    def get(self, request, store_id):
        get_object_or_404(Store, pk=store_id)
        orders = (
            Order.objects.filter(store_id=store_id)
            .annotate(total_items=Count("items"))
            .order_by("-created_at")
        )
        return Response(StoreOrderListSerializer(orders, many=True).data)
