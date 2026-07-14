from django.db import migrations


def backfill_amount_paid(apps, schema_editor):
    Sale = apps.get_model('core', 'Sale')
    for s in Sale.objects.filter(payment_status='paid', amount_paid=0):
        s.amount_paid = s.sell_price * s.quantity
        s.save(update_fields=['amount_paid'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_sale_amount_paid_sale_customer_name_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_amount_paid, noop),
    ]
