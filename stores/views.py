from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Inventory, Store
from .serializers import InventorySerializer


class StoreInventoryView(APIView):
    def get(self, request, store_id):
        get_object_or_404(Store, pk=store_id)
        cache_key = f"store:{store_id}:inventory"
        data = cache.get(cache_key)
        if data is None:
            inventory = (
                Inventory.objects.filter(store_id=store_id)
                .select_related("product", "product__category")
                .order_by("product__title")
            )
            data = InventorySerializer(inventory, many=True).data
            cache.set(cache_key, data, 300)
        return Response(data)
