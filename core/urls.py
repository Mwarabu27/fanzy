from django.urls import path
from django.views.decorators.cache import never_cache

from . import views

nc = never_cache  # API responses carry live financial data — never let the browser cache them

urlpatterns = [
    path('', views.index, name='index'),

    # Products
    path('api/products/', nc(views.products_list), name='products_list'),
    path('api/products/<int:pk>/', nc(views.product_detail), name='product_detail'),
    path('api/products/<int:pk>/adj-qty/', nc(views.adj_qty), name='adj_qty'),

    # Sales
    path('api/sales/', nc(views.sales_list), name='sales_list'),

    # Customer Debts
    path('api/debts/', nc(views.debts_list), name='debts_list'),
    path('api/debts/pay/', nc(views.debt_pay), name='debt_pay'),

    # Restocks
    path('api/restocks/', nc(views.restocks_list), name='restocks_list'),

    # Suppliers
    path('api/suppliers/', nc(views.suppliers_list), name='suppliers_list'),
    path('api/suppliers/<int:pk>/', nc(views.supplier_detail), name='supplier_detail'),

    # Activity
    path('api/activity/', nc(views.activity_list), name='activity_list'),

    # Expenses
    path('api/expenses/', nc(views.expenses_list), name='expenses_list'),
    path('api/expenses/<int:pk>/', nc(views.expense_detail), name='expense_detail'),
]
