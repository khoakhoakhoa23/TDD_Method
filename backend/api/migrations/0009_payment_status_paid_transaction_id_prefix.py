import uuid
from django.db import migrations, models


def generate_transaction_id():
    return f"TXN{uuid.uuid4().hex.upper()}"


def update_payment_data(apps, schema_editor):
    Payment = apps.get_model("api", "Payment")

    Payment.objects.filter(status="success").update(status="paid")

    existing_txn_ids = set(
        Payment.objects.filter(transaction_id__startswith="TXN")
        .values_list("transaction_id", flat=True)
    )

    for payment in Payment.objects.exclude(transaction_id__startswith="TXN").iterator():
        current = payment.transaction_id or ""
        candidate = f"TXN{current}" if current else generate_transaction_id()

        if candidate in existing_txn_ids:
            while True:
                candidate = generate_transaction_id()
                if not Payment.objects.filter(transaction_id=candidate).exists():
                    break

        payment.transaction_id = candidate
        payment.save(update_fields=["transaction_id"])
        existing_txn_ids.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_roles_permissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed")],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="transaction_id",
            field=models.CharField(
                default=generate_transaction_id,
                max_length=100,
                unique=True,
            ),
        ),
        migrations.RunPython(update_payment_data, reverse_code=migrations.RunPython.noop),
    ]
