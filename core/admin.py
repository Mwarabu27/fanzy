from django.contrib import admin
from .models import Product, Sale, RestockLog, Supplier, ActivityLog, Expense

admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(RestockLog)
admin.site.register(Supplier)
admin.site.register(ActivityLog)
admin.site.register(Expense)
