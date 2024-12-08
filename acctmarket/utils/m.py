# class PaymentVerificationMixin:
#     def assign_keys_and_notify(self, request, payment):
#         try:
#             with transaction.atomic():
#                 self.assign_unique_keys_to_order(payment.order.id)

#                 purchased_product_url = request.build_absolute_uri(
#                     reverse("ecommerce:purchased_products")
#                 )

#                 send_mail(
#                     "Your Purchase is Complete",
#                     f"Thank you for your purchase.\nYou can access your purchased products here: {purchased_product_url}",  # noqa
#                     settings.DEFAULT_FROM_EMAIL,
#                     [request.user.email],
#                     fail_silently=False,
#                 )

#                 messages.success(request, "Verification successful. Check your email for access to your products.")  # noqa
#                 return redirect("ecommerce:payment_complete")
#         except Exception as e:
#             messages.error(
#                 request,
#                 f"Verification succeeded but an issue occurred: {e}"
#             )
#             return redirect("ecommerce:support")

#     def assign_unique_keys_to_order(self, order_id):
#         order = get_object_or_404(CartOrder, id=order_id)

#         for order_item in order.order_items.all():
#             product = order_item.product
#             quantity = order_item.quantity

#             available_keys = ProductKey.objects.select_for_update().filter(
#                 product=product, is_used=False)[:quantity]

#             if len(available_keys) < quantity:
#                 self.handle_insufficient_keys(order_item, available_keys)
#                 continue

#             keys_and_passwords = []

#             for i in range(quantity):
#                 product_key = available_keys[i]
#                 product_key.is_used = True
#                 product_key.save()
#                 keys_and_passwords.append({
#                     "key": product_key.key,
#                     "password": product_key.password
#                 })

#             order_item.keys_and_passwords = keys_and_passwords
#             order_item.save()

#             product.quantity_in_stock -= quantity
#             if product.quantity_in_stock < 1:
#                 product.visible = False
#             product.save()

#     def handle_insufficient_keys(self, order_item, available_keys):
#         keys_and_passwords = []

#         for key in available_keys:
#             key.is_used = True
#             key.save()
#             keys_and_passwords.append({
#                 "key": key.key, "password": key.password
#             })

#         order_item.keys_and_passwords = keys_and_passwords
#         order_item.save()

#         product = order_item.product
#         user = order_item.order.user
#         notify_user_insufficient_keys(user, product)

#     def notify_site_owner(self, request, payment):
#         order = payment.order
#         user = request.user
#         site_owner_email = settings.EMAIL_HOST_USER

#         # Create the email content for the site owner
#         subject = f"New Purchase by {user.username} - Order #{order.id}"
#         message = render_to_string("emails/purchase_notification_to_owner.html", {   # noqa
#             "user": user,
#             "order": order,
#             "order_items": order.order_items.all(),
#         })

#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [site_owner_email],
#             fail_silently=False,
#         )


# def notify_user_insufficient_keys(user, product):
#     # Send notification to user about the insufficient keys for the product
#     send_mail(
#         "Insufficient Product Keys",
#         f"Dear customer,\n\nWe regret to inform you that there are insufficient keys available for the product '{product.title}'. Our team is working on resolving this issue.\n\nThank you for your understanding.",  # noqa
#         settings.DEFAULT_FROM_EMAIL,
#         [user.email],
#         fail_silently=False,
#     )
