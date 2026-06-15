from celery import shared_task


@shared_task
def send_order_status_notification(order_id):
    from .models import Order

    order = Order.objects.select_related("store").get(pk=order_id)
    return f"Order {order.pk} for {order.store.name} is {order.status}"
