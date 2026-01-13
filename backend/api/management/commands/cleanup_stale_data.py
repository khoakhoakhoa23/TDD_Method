from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import Cart, CartItem, Payment


class Command(BaseCommand):
    help = "Cleanup stale carts and expire old pending payments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cart-age-hours",
            type=int,
            default=24,
            help="Cart inactivity age in hours before cleanup.",
        )
        parser.add_argument(
            "--payment-age-hours",
            type=int,
            default=24,
            help="Pending payment age in hours before marking failed.",
        )
        parser.add_argument(
            "--delete-empty-carts",
            action="store_true",
            help="Delete carts after removing stale items.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show counts without deleting or updating.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        cart_cutoff = now - timedelta(hours=options["cart_age_hours"])
        payment_cutoff = now - timedelta(hours=options["payment_age_hours"])

        stale_carts = Cart.objects.filter(updated_at__lt=cart_cutoff)
        stale_cart_ids = list(stale_carts.values_list("id", flat=True))
        stale_items = CartItem.objects.filter(cart_id__in=stale_cart_ids)

        pending_payments = Payment.objects.filter(
            status="pending",
            created_at__lt=payment_cutoff,
        )

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: {len(stale_cart_ids)} stale carts, "
                f"{stale_items.count()} cart items to delete, "
                f"{pending_payments.count()} pending payments to expire."
            )
            return

        deleted_items, _ = stale_items.delete()
        self.stdout.write(f"Deleted cart items: {deleted_items}")

        if options["delete_empty_carts"] and stale_cart_ids:
            deleted_carts, _ = Cart.objects.filter(id__in=stale_cart_ids).delete()
            self.stdout.write(f"Deleted carts: {deleted_carts}")

        updated_payments = pending_payments.update(status="failed")
        self.stdout.write(f"Expired payments: {updated_payments}")
