from django.test import override_settings
from rest_framework.test import APITestCase

from products.models import Category, Product
from stores.models import Inventory, Store


@override_settings(
    USE_LOC_MEM_CACHE='1',
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class AforroApiTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(name="Beverages")
        self.product = Product.objects.create(
            title="Apple Juice",
            description="Fresh apple drink",
            price="3.50",
            category=category,
        )
        self.other = Product.objects.create(
            title="Banana Chips",
            description="Crispy snack",
            price="2.00",
            category=category,
        )
        self.store = Store.objects.create(name="Main Store", location="Pune")
        Inventory.objects.create(store=self.store, product=self.product, quantity=10)
        Inventory.objects.create(store=self.store, product=self.other, quantity=0)

    def test_confirmed_order_deducts_stock(self):
        response = self.client.post(
            "/orders/",
            {"store_id": self.store.id, "items": [{"product_id": self.product.id, "quantity_requested": 3}]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 7)

    def test_rejected_order_does_not_deduct_stock(self):
        response = self.client.post(
            "/orders/",
            {"store_id": self.store.id, "items": [{"product_id": self.product.id, "quantity_requested": 30}]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "REJECTED")
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)

    def test_inventory_listing_includes_product_and_category(self):
        response = self.client.get(f"/stores/{self.store.id}/inventory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["product_title"], "Apple Juice")
        self.assertEqual(response.data[0]["category_name"], "Beverages")

    def test_product_search_can_filter_in_stock_by_store(self):
        response = self.client.get(f"/api/search/products/?q=apple&store_id={self.store.id}&in_stock=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["inventory_quantity"], 10)

    def test_suggest_requires_three_chars_and_prioritizes_prefix(self):
        too_short = self.client.get("/api/search/suggest/?q=ap")
        self.assertEqual(too_short.status_code, 400)
        response = self.client.get("/api/search/suggest/?q=app")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0], "Apple Juice")

    def test_openapi_schema_is_available(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.data)
