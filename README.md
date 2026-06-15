## Local setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Set `REDIS_URL` if Redis is not running on `redis://localhost:6379/0`.

## Docker

```bash
docker compose up --build
```


```bash
docker compose exec api python manage.py seed_data
```

## API examples

Create an order:

```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d "{\"store_id\":1,\"items\":[{\"product_id\":1,\"quantity_requested\":2}]}"
```

List store orders:

```bash
curl http://localhost:8000/stores/1/orders/
```

List store inventory:

```bash
curl http://localhost:8000/stores/1/inventory/
```

Search products:

```bash
curl "http://localhost:8000/api/search/products/?q=juice&store_id=1&in_stock=true&sort=relevance"
```

Autocomplete:

```bash
curl "http://localhost:8000/api/search/suggest/?q=jui"
```

## Notes

Order creation uses `transaction.atomic()` and row locks on inventory rows. If any requested item is unavailable, the order is saved as `REJECTED` and stock is unchanged. Confirmed orders deduct stock inside the same transaction.

Store inventory and autocomplete responses are cached with Redis. Inventory cache is invalidated whenever inventory rows are saved/deleted and when an order changes stock. Product autocomplete uses a short TTL to keep suggestions fast and small.

Celery uses Redis as broker/result backend. Confirmed or rejected order creation triggers `send_order_status_notification.delay(order_id)`.

## Scalability considerations

The search endpoint uses indexed fields, `select_related`, conditional inventory annotations, and pagination. For larger catalogs, PostgreSQL full-text search or an external search service would replace multi-field `icontains`. Inventory writes should continue to use row-level locking or optimistic versioning to prevent overselling under concurrency.
