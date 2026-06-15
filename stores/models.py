from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="inventory")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "product"], name="unique_store_product_inventory")
        ]
        indexes = [
            models.Index(fields=["store", "product"]),
            models.Index(fields=["quantity"]),
        ]

    def __str__(self):
        return f"{self.store} - {self.product}: {self.quantity}"
