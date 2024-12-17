import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from acctmarket.applications.ecommerce.models import CartOrderItems, ProductKey

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CartOrderItems)
def assign_unique_key(sender, instance, created, **kwargs):
    """
    Signal to handle the assignment of unique keys
    after an order item is created.

    Args:
        sender (Model): The model class that sent the signal.
        instance (CartOrderItems): The instance of the model that was saved.
        created (bool): Whether this instance is being created.
        kwargs (dict): Additional keyword arguments.
    """
    if created:
        # This method is already handled in the service layer.
        # Just demonstrating how you could use signals for side effects.
        pass


@receiver(post_save, sender=ProductKey)
def update_product_quantity(sender, instance, created, **kwargs):
    """
    Updates the quantity_in_stock of the related Product
    whenever a ProductKey is created.
    """
    if created and instance.product:
        product = instance.product
        if product.quantity_in_stock > 0:
            product.quantity_in_stock += 1
            product.in_stock = product.quantity_in_stock > 0
            logger.info(f"product {product.quantity_in_stock} is updated")
            product.save()
