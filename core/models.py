from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    category_specialty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'categorySpecialty': self.category_specialty,
            'phone': self.phone,
            'location': self.location,
        }


class Product(models.Model):
    name = models.CharField(max_length=300)
    category = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True)
    quantity = models.IntegerField(default=0)
    cost_price = models.DecimalField(max_digits=15, decimal_places=2)
    sell_price = models.DecimalField(max_digits=15, decimal_places=2)
    alert_threshold = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def status(self):
        if self.quantity <= 0:
            return 'out-of-stock'
        if self.quantity <= self.alert_threshold:
            return 'low-stock'
        return 'in-stock'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'sku': self.sku,
            'quantity': self.quantity,
            'costPrice': float(self.cost_price),
            'sellPrice': float(self.sell_price),
            'alertThreshold': self.alert_threshold,
            'status': self.status(),
        }


PAYMENT_STATUSES = [
    ('paid', 'Fully Paid'),
    ('partial', 'Partially Paid'),
    ('unpaid', 'Unpaid'),
]


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=300)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField()
    sell_price = models.DecimalField(max_digits=15, decimal_places=2)
    cost_price = models.DecimalField(max_digits=15, decimal_places=2)
    profit = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    ts = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=100, default='Staff')

    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='paid')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=50, blank=True)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-ts']

    def balance_due(self):
        return float(self.sell_price) * self.quantity - float(self.amount_paid)

    def to_dict(self):
        return {
            'id': self.id,
            'productId': self.product_id,
            'productName': self.product_name,
            'category': self.category,
            'quantity': self.quantity,
            'sellPrice': float(self.sell_price),
            'costPrice': float(self.cost_price),
            'profit': float(self.profit),
            'date': str(self.date),
            'ts': self.ts.isoformat(),
            'actor': self.actor,
            'paymentStatus': self.payment_status,
            'customerName': self.customer_name,
            'customerPhone': self.customer_phone,
            'amountPaid': float(self.amount_paid),
            'dueDate': str(self.due_date) if self.due_date else None,
            'balanceDue': self.balance_due(),
        }


class RestockLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=300)
    quantity = models.IntegerField()
    cost_per_unit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    supplier_name = models.CharField(max_length=200, default='N/A')
    date = models.DateField()
    ts = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=100, default='Staff')

    class Meta:
        ordering = ['-ts']

    def to_dict(self):
        return {
            'id': self.id,
            'productId': self.product_id,
            'productName': self.product_name,
            'quantity': self.quantity,
            'costPerUnit': float(self.cost_per_unit),
            'totalCost': float(self.total_cost),
            'supplierName': self.supplier_name,
            'date': str(self.date),
            'ts': self.ts.isoformat(),
            'actor': self.actor,
        }


class ActivityLog(models.Model):
    action = models.CharField(max_length=100)
    detail = models.TextField()
    actor = models.CharField(max_length=100, default='System')
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ts']

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'detail': self.detail,
            'actor': self.actor,
            'ts': self.ts.isoformat(),
        }


EXPENSE_CATEGORIES = [
    ('Rent', 'Frame / Shop Rent'),
    ('Electricity', 'Electricity Bill'),
    ('Salary', 'Staff Salary'),
    ('Social Media', 'Social Media Ads'),
    ('Transport', 'Transport & Delivery'),
    ('Maintenance', 'Maintenance & Repairs'),
    ('Internet', 'Internet & Airtime'),
    ('Water', 'Water Bill'),
    ('Other', 'Other'),
]

RECURRING_PERIODS = [
    ('monthly', 'Monthly'),
    ('weekly', 'Weekly'),
    ('yearly', 'Yearly'),
]


class Expense(models.Model):
    category = models.CharField(max_length=100, choices=EXPENSE_CATEGORIES)
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    recurring = models.BooleanField(default=False)
    recurring_period = models.CharField(max_length=20, blank=True, choices=RECURRING_PERIODS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'description': self.description,
            'amount': float(self.amount),
            'date': str(self.date),
            'recurring': self.recurring,
            'recurringPeriod': self.recurring_period,
        }
