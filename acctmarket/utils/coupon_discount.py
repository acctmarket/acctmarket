import logging
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from acctmarket.applications.ecommerce.models import Product
from acctmarket.utils.choices import COUPON_CHOICE

logger = logging.getLogger(__name__)


def validate_coupon(coupon_code, cart_data):
    """Validate the coupon code and calculate the discount."""
    from acctmarket.applications.ecommerce.models import Coupon

    try:
        coupon = Coupon.objects.get(code=coupon_code)
        if not coupon.is_valid():
            return None, "Coupon is expired or usage limit reached."

        return coupon, None
    except ObjectDoesNotExist:
        return None, "Coupon does not exist."


def calculate_discount(coupon, cart_data):
    """
    Calculate the discount based on the coupon's applicability.

    Logs detailed information for debugging purposes.

    Args:
        coupon (Coupon): The coupon being applied.
        cart_data (dict): Cart items with product details.

    Returns:
        Decimal: Total discount amount.
    """
    total_discount = Decimal("0.00")
    logger.info(f"Starting discount calculation for coupon: {coupon.code}")  # noqa

    try:
        # Universal coupon: apply to all cart items
        if coupon.universal:
            logger.info("Coupon is universal, applying to all items.")
            total_cart_value = sum(
                Decimal(item["price"])
                * int(
                    item["quantity"],
                )
                for item in cart_data.values()
            )
            logger.info(f"Total cart value: {total_cart_value}")

            if coupon.discount_type == COUPON_CHOICE.PERCENTAGE:
                total_discount = total_cart_value * (coupon.discount_value / 100)  # noqa
                logger.info(f"Percentage discount applied: {coupon.discount_value}%")  # noqa
            else:
                total_discount = coupon.discount_value
                logger.info(f"Flat discount applied: {coupon.discount_value}")  # noqa

        # Specific product/category coupon
        else:
            logger.info("Coupon is product/category specific.")
            for product_id, item in cart_data.items():
                try:
                    product = get_object_or_404(Product, id=product_id)
                    item_total = Decimal(item["price"]) * int(item["quantity"])
                    logger.info(f"Processing product {product_id}: Total={item_total}")  # noqa

                    if (
                        coupon.applicable_products.filter(
                            id=product.id,
                        ).exists()
                        or coupon.applicable_categories.filter(
                            id=product.category.id,
                        ).exists()
                    ):
                        logger.info(f"Coupon applicable to product {product_id}.")  # noqa
                        if coupon.discount_type == COUPON_CHOICE.PERCENTAGE:
                            discount = item_total * (coupon.discount_value / 100)  # noqa
                            logger.info(
                                f"Percentage discount for product {product_id}: {discount}"  # noqa
                            )
                        else:
                            discount = min(coupon.discount_value, item_total)
                            logger.info(
                                f"Flat discount for product {product_id}: {discount}"  # noqa
                            )
                        total_discount += discount
                    else:
                        logger.info(f"Coupon not applicable to product {product_id}.")  # noqa
                except Exception as e:
                    logger.error(f"Error processing product {product_id}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error during discount calculation: {e}")

    logger.info(f"Total discount calculated: {total_discount}")
    return total_discount
