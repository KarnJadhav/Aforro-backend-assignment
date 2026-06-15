import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from faker import Faker

from products.models import Category, Product
from stores.models import Inventory, Store


class Command(BaseCommand):
    help = "Seed categories, products, stores, and inventory for local development."

    def handle(self, *args, **options):
        fake = Faker()
        categories = [
            Category.objects.get_or_create(name=name)[0]
            for name in [
                "Bakery",
                "Beverages",
                "Dairy",
                "Frozen",
                "Pantry",
                "Produce",
                "Snacks",
                "Household",
                "Personal Care",
                "Pet Supplies",
                "Electronics",
                "Stationery",
            ]
        ]

        product_count = Product.objects.count()
        if product_count < 1000:
            products = [
                Product(
                    title=f"{fake.word().title()} {fake.word().title()} SKU-{product_count + idx + 1:04d}",
                    description=fake.sentence(nb_words=12),
                    price=Decimal(random.randrange(100, 25000)) / Decimal("100"),
                    category=random.choice(categories),
                )
                for idx in range(1000 - product_count)
            ]
            Product.objects.bulk_create(products, batch_size=500)

        if Store.objects.count() < 20:
            stores = [
                Store(name=f"{fake.city()} Store {idx}", location=fake.address())
                for idx in range(20 - Store.objects.count())
            ]
            Store.objects.bulk_create(stores, batch_size=100)

        product_ids = list(Product.objects.values_list("id", flat=True))
        inventory = []
        for store in Store.objects.all():
            existing = set(
                Inventory.objects.filter(store=store).values_list("product_id", flat=True)
            )
            needed = max(0, 300 - len(existing))
            candidates = [pk for pk in product_ids if pk not in existing]
            for product_id in random.sample(candidates, min(needed, len(candidates))):
                inventory.append(
                    Inventory(store=store, product_id=product_id, quantity=random.randint(0, 250))
                )
        Inventory.objects.bulk_create(inventory, batch_size=1000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS("Seed data created."))
