import json
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import Product, Sale, RestockLog, Supplier, ActivityLog, Expense

CAT_PFX = {
    'Audio & Electronics': 'AUD',
    'Exterior Accessories': 'EXT',
    'Interior Accessories': 'INT',
    'Tyres & Wheels': 'TYR',
    'Lighting': 'LIT',
    'Car Care': 'CAR',
    'Security': 'SEC',
    'Performance Parts': 'PER',
}


def generate_sku(category):
    pfx = CAT_PFX.get(category, 'GEN')
    count = Product.objects.filter(category=category).count() + 1
    sku = f'FAZ-{pfx}-{count:03d}'
    while Product.objects.filter(sku=sku).exists():
        count += 1
        sku = f'FAZ-{pfx}-{count:03d}'
    return sku


def log_act(action, detail, actor='System'):
    ActivityLog.objects.create(action=action, detail=detail, actor=actor)
    ActivityLog.objects.filter(pk__lt=ActivityLog.objects.order_by('-pk')[min(1999, ActivityLog.objects.count() - 1)].pk).delete() if ActivityLog.objects.count() > 2000 else None


# ── Auth ─────────────────────────────────────────────────────────────
class FanzyLoginView(auth_views.LoginView):
    template_name = 'login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST.get('remember_me'):
            self.request.session.set_expiry(settings.REMEMBER_ME_AGE)
        else:
            self.request.session.set_expiry(0)  # expire when the browser closes
        return response


# ── Index ────────────────────────────────────────────────────────────
@login_required
@never_cache
def index(request):
    return render(request, 'index.html', {'user': request.user})


# ── Products ─────────────────────────────────────────────────────────
@login_required
def products_list(request):
    if request.method == 'GET':
        return JsonResponse([p.to_dict() for p in Product.objects.all()], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        sku = (data.get('sku') or '').strip()
        if not sku or sku == 'Auto-generated on save' or Product.objects.filter(sku=sku).exists():
            sku = generate_sku(data['category'])
        p = Product.objects.create(
            name=data['name'],
            category=data['category'],
            sku=sku,
            quantity=int(data.get('quantity', 0)),
            cost_price=float(data['costPrice']),
            sell_price=float(data['sellPrice']),
            alert_threshold=int(data.get('alertThreshold', 5)),
        )
        log_act('Product Added', f"{p.name} ({p.sku}) — {p.quantity} units @ TZS {p.sell_price}", data.get('actor', 'User'))
        return JsonResponse(p.to_dict(), status=201)


@login_required
def product_detail(request, pk):
    p = get_object_or_404(Product, pk=pk)

    if request.method == 'GET':
        return JsonResponse(p.to_dict())

    if request.method == 'PUT':
        data = json.loads(request.body)
        old_qty, old_cost = p.quantity, p.cost_price
        p.name = data.get('name', p.name)
        p.category = data.get('category', p.category)
        p.cost_price = float(data.get('costPrice', p.cost_price))
        p.sell_price = float(data.get('sellPrice', p.sell_price))
        p.quantity = int(data.get('quantity', p.quantity))
        p.alert_threshold = int(data.get('alertThreshold', p.alert_threshold))
        p.save()
        log_act('Product Edited', f"{p.name}: qty {old_qty}→{p.quantity}, cost TZS {old_cost}→{p.cost_price}", data.get('actor', 'User'))
        return JsonResponse(p.to_dict())

    if request.method == 'DELETE':
        name, sku = p.name, p.sku
        p.delete()
        log_act('Product Deleted', f"{name} ({sku}) removed", 'User')
        return JsonResponse({'ok': True})


@login_required
def adj_qty(request, pk):
    if request.method == 'POST':
        p = get_object_or_404(Product, pk=pk)
        data = json.loads(request.body)
        delta = int(data.get('delta', 0))
        old = p.quantity
        p.quantity = max(0, p.quantity + delta)
        p.save()
        log_act('Stock Edit', f"{p.name}: {old} → {p.quantity}", data.get('actor', 'User'))
        return JsonResponse(p.to_dict())


# ── Sales ─────────────────────────────────────────────────────────────
@login_required
def sales_list(request):
    if request.method == 'GET':
        qs = Sale.objects.all()
        from_d = request.GET.get('from')
        to_d = request.GET.get('to')
        if from_d:
            qs = qs.filter(date__gte=from_d)
        if to_d:
            qs = qs.filter(date__lte=to_d)
        return JsonResponse([s.to_dict() for s in qs], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        p = get_object_or_404(Product, pk=data['productId'])
        qty = int(data['quantity'])
        sell = float(data['sellPrice'])
        if p.quantity < qty:
            return JsonResponse({'error': f'Only {p.quantity} units in stock!'}, status=400)
        cost = float(p.cost_price)
        profit = (sell - cost) * qty
        p.quantity -= qty
        p.save()

        revenue = sell * qty
        payment_status = data.get('paymentStatus') or 'paid'
        if payment_status == 'paid':
            amount_paid = revenue
            due_date = None
        else:
            amount_paid = float(data.get('amountPaid', 0) or 0)
            due_date = data.get('dueDate') or None

        sale = Sale.objects.create(
            product=p, product_name=p.name, category=p.category,
            quantity=qty, sell_price=sell, cost_price=cost, profit=profit,
            date=data['date'], actor=data.get('actor', 'Staff'),
            payment_status=payment_status,
            customer_name=data.get('customerName', '').strip(),
            customer_phone=data.get('customerPhone', '').strip(),
            amount_paid=amount_paid,
            due_date=due_date,
        )
        log_act('Sale', f"{p.name} × {qty} @ TZS {sell} — Profit: TZS {profit:.0f}", data.get('actor', 'Staff'))
        return JsonResponse(sale.to_dict(), status=201)


# ── Restocks ──────────────────────────────────────────────────────────
@login_required
def restocks_list(request):
    if request.method == 'GET':
        return JsonResponse([r.to_dict() for r in RestockLog.objects.all()], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        p = get_object_or_404(Product, pk=data['productId'])
        qty = int(data['quantity'])
        cpu = float(data.get('costPerUnit', 0) or 0)
        sup, sup_name = None, 'N/A'
        if data.get('supplierId'):
            try:
                sup = Supplier.objects.get(pk=data['supplierId'])
                sup_name = sup.name
            except Supplier.DoesNotExist:
                pass
        p.quantity += qty
        p.save()
        rs = RestockLog.objects.create(
            product=p, product_name=p.name, quantity=qty,
            cost_per_unit=cpu, total_cost=cpu * qty,
            supplier=sup, supplier_name=sup_name,
            date=data['date'], actor=data.get('actor', 'Staff'),
        )
        log_act('Restock', f"{p.name} +{qty} units. Supplier: {sup_name}. Cost: TZS {cpu * qty:.0f}", data.get('actor', 'Staff'))
        return JsonResponse(rs.to_dict(), status=201)


# ── Suppliers ─────────────────────────────────────────────────────────
@login_required
def suppliers_list(request):
    if request.method == 'GET':
        return JsonResponse([s.to_dict() for s in Supplier.objects.all()], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        s = Supplier.objects.create(
            name=data['name'],
            category_specialty=data.get('categorySpecialty', ''),
            phone=data['phone'],
            location=data.get('location', ''),
        )
        log_act('Supplier Added', f"{s.name} — {s.phone}, {s.location or 'no location'}", 'User')
        return JsonResponse(s.to_dict(), status=201)


@login_required
def supplier_detail(request, pk):
    s = get_object_or_404(Supplier, pk=pk)

    if request.method == 'PUT':
        data = json.loads(request.body)
        s.name = data.get('name', s.name)
        s.category_specialty = data.get('categorySpecialty', s.category_specialty)
        s.phone = data.get('phone', s.phone)
        s.location = data.get('location', s.location)
        s.save()
        log_act('Supplier Edited', f"{s.name} — {s.phone}, {s.location}", 'User')
        return JsonResponse(s.to_dict())

    if request.method == 'DELETE':
        name = s.name
        s.delete()
        log_act('Supplier Deleted', f"{name} removed", 'User')
        return JsonResponse({'ok': True})


# ── Activity ──────────────────────────────────────────────────────────
@login_required
def activity_list(request):
    if request.method == 'GET':
        qs = ActivityLog.objects.all()
        from_d = request.GET.get('from')
        to_d = request.GET.get('to')
        if from_d:
            qs = qs.filter(ts__date__gte=from_d)
        if to_d:
            qs = qs.filter(ts__date__lte=to_d)
        return JsonResponse([l.to_dict() for l in qs[:500]], safe=False)


# ── Expenses ──────────────────────────────────────────────────────────
@login_required
def expenses_list(request):
    if request.method == 'GET':
        return JsonResponse([e.to_dict() for e in Expense.objects.all()], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        e = Expense.objects.create(
            category=data['category'],
            description=data['description'],
            amount=float(data['amount']),
            date=data['date'],
            recurring=bool(data.get('recurring', False)),
            recurring_period=data.get('recurringPeriod', '') or '',
        )
        return JsonResponse(e.to_dict(), status=201)


@login_required
def expense_detail(request, pk):
    e = get_object_or_404(Expense, pk=pk)

    if request.method == 'PUT':
        data = json.loads(request.body)
        e.category = data.get('category', e.category)
        e.description = data.get('description', e.description)
        e.amount = float(data.get('amount', e.amount))
        e.date = data.get('date', e.date)
        e.recurring = bool(data.get('recurring', e.recurring))
        e.recurring_period = data.get('recurringPeriod', e.recurring_period) or ''
        e.save()
        return JsonResponse(e.to_dict())

    if request.method == 'DELETE':
        e.delete()
        return JsonResponse({'ok': True})


# ── Customer Debts ──────────────────────────────────────────────────────
@login_required
def debts_list(request):
    if request.method == 'GET':
        outstanding = Sale.objects.exclude(payment_status='paid').exclude(customer_name='')
        groups = {}
        for s in outstanding:
            bal = s.balance_due()
            if bal <= 0:
                continue
            key = (s.customer_name, s.customer_phone)
            g = groups.setdefault(key, {
                'customerName': s.customer_name,
                'customerPhone': s.customer_phone,
                'totalOwed': 0.0,
                'lastTransactionDate': None,
                'nextDueDate': None,
            })
            g['totalOwed'] += bal
            if not g['lastTransactionDate'] or str(s.date) > g['lastTransactionDate']:
                g['lastTransactionDate'] = str(s.date)
            if s.due_date and (not g['nextDueDate'] or str(s.due_date) < g['nextDueDate']):
                g['nextDueDate'] = str(s.due_date)
        result = sorted(groups.values(), key=lambda g: g['totalOwed'], reverse=True)
        return JsonResponse(result, safe=False)


@login_required
def debt_pay(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('customerName', '').strip()
        phone = data.get('customerPhone', '').strip()
        amount = float(data.get('amount', 0) or 0)
        if not name or amount <= 0:
            return JsonResponse({'error': 'Customer name and a positive amount are required'}, status=400)

        sales = Sale.objects.filter(customer_name=name, customer_phone=phone).exclude(payment_status='paid').order_by('date', 'ts')
        remaining = amount
        for s in sales:
            if remaining <= 0:
                break
            bal = s.balance_due()
            if bal <= 0:
                continue
            pay = min(remaining, bal)
            s.amount_paid = float(s.amount_paid) + pay
            remaining -= pay
            if s.balance_due() <= 0.01:
                s.payment_status = 'paid'
                s.due_date = None
            else:
                s.payment_status = 'partial'
            s.save()

        applied = amount - remaining
        log_act('Debt Payment', f"{name} paid TZS {applied:.0f}", data.get('actor', 'Staff'))
        return JsonResponse({'ok': True, 'applied': applied})
