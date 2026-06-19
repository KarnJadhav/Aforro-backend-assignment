from django.core.cache import cache
from django.db.models import Case, IntegerField, OuterRef, Q, Subquery, Value, When
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from products.serializers import ProductSerializer
from stores.models import Inventory


def parse_bool(value):
    return str(value).lower() in {"1", "true", "yes"}


class ProductSearchView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Keyword searched across title, description, and category name."),
            OpenApiParameter("category", str, description="Category ID or exact category name."),
            OpenApiParameter("min_price", float, description="Minimum product price."),
            OpenApiParameter("max_price", float, description="Maximum product price."),
            OpenApiParameter("store_id", int, description="Include inventory quantity for this store."),
            OpenApiParameter("in_stock", bool, description="Return only products with available stock."),
            OpenApiParameter("sort", str, enum=["price", "newest", "relevance"]),
            OpenApiParameter("page", int, description="Page number for paginated results."),
        ],
        responses=ProductSerializer(many=True),
        summary="Search products",
        description=(
            "Searches products with optional category, price, store, stock, sorting, "
            "and pagination support. When store_id is provided, each product includes "
            "that store's inventory quantity."
        ),
    )
    def get(self, request):
        params = request.query_params
        queryset = Product.objects.select_related("category").all()
        keyword = params.get("q", "").strip()

        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(category__name__icontains=keyword)
            ).annotate(
                relevance=Case(
                    When(title__istartswith=keyword, then=Value(3)),
                    When(title__icontains=keyword, then=Value(2)),
                    When(category__name__icontains=keyword, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        else:
            queryset = queryset.annotate(relevance=Value(0, output_field=IntegerField()))

        category = params.get("category")
        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=category)
            else:
                queryset = queryset.filter(category__name__iexact=category)

        min_price = params.get("min_price")
        max_price = params.get("max_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        store_id = params.get("store_id")
        if store_id:
            store_inventory = Inventory.objects.filter(store_id=store_id, product_id=OuterRef("pk"))
            queryset = queryset.annotate(
                inventory_quantity=Subquery(store_inventory.values("quantity")[:1])
            )
            if parse_bool(params.get("in_stock")):
                queryset = queryset.filter(inventory__store_id=store_id, inventory__quantity__gt=0)
        elif params.get("in_stock") is not None and parse_bool(params.get("in_stock")):
            queryset = queryset.filter(inventory__quantity__gt=0).distinct()

        sort = params.get("sort", "relevance")
        if sort == "price":
            queryset = queryset.order_by("price", "title")
        elif sort == "newest":
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-relevance", "title")

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ProductSerializer(page, many=True).data)


class ProductSuggestView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, required=True, description="At least 3 characters."),
        ],
        responses={
            200: inline_serializer(
                name="ProductSuggestResponse",
                fields={"results": serializers.ListField(child=serializers.CharField())},
            ),
            400: OpenApiResponse(description="Minimum 3 characters required."),
        },
        summary="Autocomplete product titles",
        description="Returns up to 10 product title suggestions with prefix matches first.",
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 3:
            return Response({"detail": "Minimum 3 characters required.", "results": []}, status=400)

        cache_key = f"suggest:{query.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"results": cached})

        products = (
            Product.objects.filter(Q(title__istartswith=query) | Q(title__icontains=query))
            .annotate(
                prefix_rank=Case(
                    When(title__istartswith=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("prefix_rank", "title")
            .values_list("title", flat=True)[:10]
        )
        results = list(products)
        cache.set(cache_key, results, 120)
        return Response({"results": results})
