from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    inventory_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "description", "price", "category", "created_at", "inventory_quantity"]
