import json
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from accounts.decorators import staff_or_admin_required, admin_required
from suppliers.models import Supplier
from .models import MedicineCategory, Medicine, MedicineBatch, StockTransaction
from .forms import (
    MedicineForm, MedicineBatchForm, MedicineBatchEditForm,
    MedicineCategoryForm, StockDispenseForm, StockAdjustmentForm, BatchDisposalForm
)



def landing_page_view(request):
    """
    Public-facing clinical operations landing page.
    Provides live dispensary inventory telemetry, interactive FEFO simulator data,
    batch risk metrics, and instant test-drive login capabilities.
    """
    today = date.today()
    day7 = today + timedelta(days=7)
    day15 = today + timedelta(days=15)
    day30 = today + timedelta(days=30)

    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_categories = MedicineCategory.objects.count()
    total_transactions = StockTransaction.objects.count()

    active_batches = MedicineBatch.objects.filter(available_quantity__gt=0)
    valid_batches = active_batches.filter(expiry_date__gte=today)
    total_available_stock = valid_batches.aggregate(total=Sum('available_quantity'))['total'] or 0

    expired_count = active_batches.filter(expiry_date__lt=today).count()
    critical_7_count = active_batches.filter(expiry_date__gte=today, expiry_date__lte=day7).count()
    urgent_15_count = active_batches.filter(expiry_date__gt=day7, expiry_date__lte=day15).count()
    warning_30_count = active_batches.filter(expiry_date__gt=day15, expiry_date__lte=day30).count()
    safe_batches_count = active_batches.filter(expiry_date__gt=day30).count()

    sample_medicines = Medicine.objects.filter(is_active=True).select_related('category', 'supplier')[:6]

    context = {
        'total_medicines': total_medicines,
        'total_suppliers': total_suppliers,
        'total_categories': total_categories,
        'total_transactions': total_transactions,
        'total_available_stock': total_available_stock,
        'expired_count': expired_count,
        'critical_7_count': critical_7_count,
        'urgent_15_count': urgent_15_count,
        'warning_30_count': warning_30_count,
        'safe_batches_count': safe_batches_count,
        'sample_medicines': sample_medicines,
    }
    return render(request, 'inventory/landing.html', context)


@staff_or_admin_required
def dashboard_view(request):
    """
    Central pharmacy dashboard presenting live inventory analytics,
    expiry distributions, stock shortage warnings, and recent transaction feeds.
    """
    today = date.today()
    day7 = today + timedelta(days=7)
    day15 = today + timedelta(days=15)
    day30 = today + timedelta(days=30)

    # Core inventory statistics
    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    active_batches = MedicineBatch.objects.filter(available_quantity__gt=0).select_related('medicine', 'supplier')

    # Non-expired batches (standard operational stock)
    valid_batches = active_batches.filter(expiry_date__gte=today)
    total_available_stock = valid_batches.aggregate(total=Sum('available_quantity'))['total'] or 0

    # Expiry breakdowns
    expired_batches_qs = active_batches.filter(expiry_date__lt=today).order_by('expiry_date')
    expired_batches_count = expired_batches_qs.count()
    total_expired_stock = expired_batches_qs.aggregate(total=Sum('available_quantity'))['total'] or 0

    critical_7_batches = active_batches.filter(expiry_date__gte=today, expiry_date__lte=day7).order_by('expiry_date')
    critical_7_count = critical_7_batches.count()

    urgent_15_batches = active_batches.filter(expiry_date__gt=day7, expiry_date__lte=day15).order_by('expiry_date')
    urgent_15_count = urgent_15_batches.count()

    warning_30_batches = active_batches.filter(expiry_date__gt=day15, expiry_date__lte=day30).order_by('expiry_date')
    warning_30_count = warning_30_batches.count()

    safe_batches_count = active_batches.filter(expiry_date__gt=day30).count()
    total_nearing_expiry = critical_7_count + urgent_15_count + warning_30_count

    # Calculate low-stock medicines
    all_medicines = Medicine.objects.filter(is_active=True).select_related('category')
    low_stock_list = []
    out_of_stock_list = []
    in_stock_count = 0

    for med in all_medicines:
        stock = med.total_available_stock
        if stock == 0:
            out_of_stock_list.append(med)
        elif stock <= med.minimum_stock_threshold:
            low_stock_list.append(med)
        else:
            in_stock_count += 1

    total_low_stock = len(low_stock_list) + len(out_of_stock_list)

    # Chart 1: Expiry Status Breakdown
    chart_expiry_labels = [
        'Expired',
        'Critical (<=7d)',
        'Urgent (<=15d)',
        'Notice (<=30d)',
        'Safe (>30d)'
    ]
    chart_expiry_data = [
        expired_batches_count,
        critical_7_count,
        urgent_15_count,
        warning_30_count,
        safe_batches_count
    ]

    # Chart 2: Category Distribution
    category_data_qs = MedicineCategory.objects.annotate(
        med_count=Count('medicines', filter=Q(medicines__is_active=True))
    ).filter(med_count__gt=0).order_by('-med_count')[:6]

    chart_cat_labels = [c.name for c in category_data_qs]
    chart_cat_data = [c.med_count for c in category_data_qs]

    # Recent Transactions
    recent_transactions = StockTransaction.objects.select_related(
        'medicine', 'batch', 'performed_by'
    ).order_by('-timestamp')[:8]

    # Top near-expiry urgent batches (for alert card)
    urgent_batches_table = active_batches.filter(expiry_date__lte=day30).order_by('expiry_date')[:6]

    return render(request, 'inventory/dashboard.html', {
        'total_medicines': total_medicines,
        'total_available_stock': total_available_stock,
        'total_expired_stock': total_expired_stock,
        'total_nearing_expiry': total_nearing_expiry,
        'expired_batches_count': expired_batches_count,
        'critical_7_count': critical_7_count,
        'urgent_15_count': urgent_15_count,
        'warning_30_count': warning_30_count,
        'total_low_stock': total_low_stock,
        'total_suppliers': total_suppliers,
        'low_stock_list': low_stock_list[:5],
        'out_of_stock_list': out_of_stock_list[:5],
        'urgent_batches_table': urgent_batches_table,
        'recent_transactions': recent_transactions,
        'chart_expiry_labels_json': json.dumps(chart_expiry_labels),
        'chart_expiry_data_json': json.dumps(chart_expiry_data),
        'chart_cat_labels_json': json.dumps(chart_cat_labels),
        'chart_cat_data_json': json.dumps(chart_cat_data),
    })


@staff_or_admin_required
def medicine_list_view(request):
    """
    Searchable, filterable medicine directory with category, supplier,
    stock status, and sorting filters.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    supplier_id = request.GET.get('supplier', '')
    stock_filter = request.GET.get('stock_status', '')
    sort_by = request.GET.get('sort', 'name')

    medicines = Medicine.objects.filter(is_active=True).select_related('category', 'supplier')

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(medicine_id__icontains=query) |
            Q(manufacturer__icontains=query)
        )

    if category_id:
        medicines = medicines.filter(category_id=category_id)

    if supplier_id:
        medicines = medicines.filter(supplier_id=supplier_id)

    # Sort
    if sort_by == 'price_asc':
        medicines = medicines.order_by('unit_price')
    elif sort_by == 'price_desc':
        medicines = medicines.order_by('-unit_price')
    elif sort_by == 'id':
        medicines = medicines.order_by('medicine_id')
    else:
        medicines = medicines.order_by('name')

    # Apply stock filter in Python if needed
    medicine_items = list(medicines)
    if stock_filter == 'low_stock':
        medicine_items = [m for m in medicine_items if m.is_low_stock and not m.is_out_of_stock]
    elif stock_filter == 'out_of_stock':
        medicine_items = [m for m in medicine_items if m.is_out_of_stock]
    elif stock_filter == 'in_stock':
        medicine_items = [m for m in medicine_items if not m.is_low_stock and not m.is_out_of_stock]

    paginator = Paginator(medicine_items, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = MedicineCategory.objects.filter(is_active=True)
    suppliers = Supplier.objects.filter(is_active=True)

    return render(request, 'inventory/medicine_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'suppliers': suppliers,
        'query': query,
        'selected_category': category_id,
        'selected_supplier': supplier_id,
        'stock_filter': stock_filter,
        'sort_by': sort_by,
        'total_count': len(medicine_items),
    })


@staff_or_admin_required
def medicine_detail_view(request, pk):
    medicine = get_object_or_404(Medicine.objects.select_related('category', 'supplier'), pk=pk)
    batches = medicine.batches.select_related('supplier').order_by('expiry_date')
    transactions = medicine.transactions.select_related('performed_by', 'batch').order_by('-timestamp')[:15]
    dispense_form = StockDispenseForm(medicine=medicine)

    return render(request, 'inventory/medicine_detail.html', {
        'medicine': medicine,
        'batches': batches,
        'transactions': transactions,
        'dispense_form': dispense_form,
    })


@admin_required
def medicine_create_view(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f"Medicine '{medicine.name}' registered successfully.")
            return redirect('medicine_detail', pk=medicine.pk)
        else:
            messages.error(request, "Failed to create medicine. Please review form errors.")
    else:
        form = MedicineForm()

    return render(request, 'inventory/medicine_form.html', {
        'form': form,
        'title': 'Add New Medicine',
    })


@admin_required
def medicine_update_view(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f"Medicine '{medicine.name}' updated successfully.")
            return redirect('medicine_detail', pk=medicine.pk)
        else:
            messages.error(request, "Please review form errors.")
    else:
        form = MedicineForm(instance=medicine)

    return render(request, 'inventory/medicine_form.html', {
        'form': form,
        'medicine': medicine,
        'title': f"Edit Medicine: {medicine.name}",
    })


@admin_required
def medicine_delete_view(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    has_active_batches = medicine.batches.filter(available_quantity__gt=0).exists()

    if request.method == 'POST':
        if has_active_batches:
            messages.error(request, f"Cannot delete '{medicine.name}' while it has active stock batches in the system.")
            return redirect('medicine_detail', pk=medicine.pk)
        name = medicine.name
        medicine.delete()
        messages.success(request, f"Medicine '{name}' was deleted.")
        return redirect('medicine_list')

    return render(request, 'inventory/medicine_confirm_delete.html', {
        'medicine': medicine,
        'has_active_batches': has_active_batches,
    })


@staff_or_admin_required
def batch_list_view(request):
    """
    Search and filter batches by expiry category, medicine, batch number, or supplier.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    supplier_id = request.GET.get('supplier', '')

    today = date.today()
    day7 = today + timedelta(days=7)
    day15 = today + timedelta(days=15)
    day30 = today + timedelta(days=30)

    batches = MedicineBatch.objects.select_related('medicine', 'supplier', 'medicine__category')

    if query:
        batches = batches.filter(
            Q(batch_number__icontains=query) |
            Q(medicine__name__icontains=query) |
            Q(medicine__generic_name__icontains=query) |
            Q(medicine__medicine_id__icontains=query)
        )

    if supplier_id:
        batches = batches.filter(supplier_id=supplier_id)

    if status_filter == 'expired':
        batches = batches.filter(expiry_date__lt=today, available_quantity__gt=0)
    elif status_filter == 'critical_7':
        batches = batches.filter(expiry_date__gte=today, expiry_date__lte=day7, available_quantity__gt=0)
    elif status_filter == 'urgent_15':
        batches = batches.filter(expiry_date__gt=day7, expiry_date__lte=day15, available_quantity__gt=0)
    elif status_filter == 'warning_30':
        batches = batches.filter(expiry_date__gt=day15, expiry_date__lte=day30, available_quantity__gt=0)
    elif status_filter == 'safe':
        batches = batches.filter(expiry_date__gt=day30, available_quantity__gt=0)
    elif status_filter == 'depleted':
        batches = batches.filter(available_quantity=0)

    batches = batches.order_by('expiry_date')

    paginator = Paginator(batches, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    suppliers = Supplier.objects.filter(is_active=True)

    return render(request, 'inventory/batch_list.html', {
        'page_obj': page_obj,
        'suppliers': suppliers,
        'query': query,
        'status_filter': status_filter,
        'selected_supplier': supplier_id,
        'total_count': batches.count(),
    })


@staff_or_admin_required
def batch_detail_view(request, pk):
    batch = get_object_or_404(
        MedicineBatch.objects.select_related('medicine', 'supplier', 'medicine__category'),
        pk=pk
    )
    transactions = batch.transactions.select_related('performed_by').order_by('-timestamp')
    notifications = batch.notifications.order_by('-sent_at')

    return render(request, 'inventory/batch_detail.html', {
        'batch': batch,
        'transactions': transactions,
        'notifications': notifications,
    })


@staff_or_admin_required
def batch_create_view(request):
    """
    Register new incoming medicine batch (Stock In).
    Automatically initializes available_quantity and records PURCHASE transaction.
    """
    initial_medicine_id = request.GET.get('medicine')
    initial_data = {}
    if initial_medicine_id:
        initial_data['medicine'] = initial_medicine_id

    if request.method == 'POST':
        form = MedicineBatchForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                batch = form.save(commit=False)
                # When stock arrives, available quantity equals purchase quantity
                batch.available_quantity = batch.purchase_quantity
                batch.save()

                # Record Stock In Transaction
                StockTransaction.objects.create(
                    medicine=batch.medicine,
                    batch=batch,
                    transaction_type=StockTransaction.TransactionType.PURCHASE,
                    quantity=batch.purchase_quantity,
                    unit_price=batch.purchase_price,
                    reference_note=f"Stock In - Batch #{batch.batch_number} received from {batch.supplier.company_name}",
                    performed_by=request.user
                )

            messages.success(request, f"Batch '{batch.batch_number}' added with {batch.purchase_quantity} units.")
            return redirect('medicine_detail', pk=batch.medicine.pk)
        else:
            messages.error(request, "Failed to record batch. Please review errors below.")
    else:
        form = MedicineBatchForm(initial=initial_data)

    return render(request, 'inventory/batch_form.html', {
        'form': form,
        'title': 'Stock In / Register New Batch',
    })


@admin_required
def batch_update_view(request, pk):
    batch = get_object_or_404(MedicineBatch, pk=pk)
    if request.method == 'POST':
        form = MedicineBatchEditForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, f"Batch '{batch.batch_number}' updated successfully.")
            return redirect('batch_detail', pk=batch.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = MedicineBatchEditForm(instance=batch)

    return render(request, 'inventory/batch_form.html', {
        'form': form,
        'batch': batch,
        'title': f"Edit Batch: {batch.batch_number} ({batch.medicine.name})",
    })


@staff_or_admin_required
def stock_dispense_view(request, pk):
    """
    Dispense medicine units from an active, non-expired batch.
    """
    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == 'POST':
        form = StockDispenseForm(request.POST, medicine=medicine)
        if form.is_valid():
            batch = form.cleaned_data['batch']
            quantity = form.cleaned_data['quantity']
            ref_note = form.cleaned_data.get('reference_note', '')

            with transaction.atomic():
                batch.available_quantity -= quantity
                batch.save()

                StockTransaction.objects.create(
                    medicine=medicine,
                    batch=batch,
                    transaction_type=StockTransaction.TransactionType.DISPENSE,
                    quantity=quantity,
                    unit_price=medicine.unit_price,
                    reference_note=f"Dispensed {quantity} units. Note: {ref_note}" if ref_note else f"Dispensed {quantity} units",
                    performed_by=request.user
                )

            messages.success(request, f"Successfully dispensed {quantity} units of {medicine.name} from Batch {batch.batch_number}.")
            return redirect('medicine_detail', pk=medicine.pk)
        else:
            messages.error(request, "Dispensation failed. Please check quantity and selected batch.")
    else:
        form = StockDispenseForm(medicine=medicine)

    return render(request, 'inventory/stock_dispense.html', {
        'medicine': medicine,
        'form': form,
    })


@staff_or_admin_required
def stock_adjustment_view(request):
    """
    Stock audit adjustment for surplus or shrinkage/damage.
    """
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            batch = form.cleaned_data['batch']
            action = form.cleaned_data['action']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            with transaction.atomic():
                if action == 'ADD':
                    batch.available_quantity += quantity
                    msg_action = f"Added {quantity} surplus units"
                else:
                    if quantity > batch.available_quantity:
                        messages.error(request, f"Cannot deduct {quantity} units; batch only has {batch.available_quantity}.")
                        return render(request, 'inventory/stock_adjustment.html', {'form': form})
                    batch.available_quantity -= quantity
                    msg_action = f"Deducted {quantity} units"

                batch.save()

                StockTransaction.objects.create(
                    medicine=batch.medicine,
                    batch=batch,
                    transaction_type=StockTransaction.TransactionType.ADJUSTMENT,
                    quantity=quantity,
                    unit_price=batch.purchase_price,
                    reference_note=f"Inventory Audit ({action}): {reason}",
                    performed_by=request.user
                )

            messages.success(request, f"Stock adjustment recorded: {msg_action} for Batch {batch.batch_number}.")
            return redirect('batch_detail', pk=batch.pk)
        else:
            messages.error(request, "Adjustment validation failed. Please check form values.")
    else:
        form = StockAdjustmentForm()

    return render(request, 'inventory/stock_adjustment.html', {'form': form})


@staff_or_admin_required
def batch_dispose_view(request, pk):
    """
    Safe recorded disposal of expired medicine batches.
    """
    batch = get_object_or_404(MedicineBatch, pk=pk)

    if request.method == 'POST':
        form = BatchDisposalForm(request.POST)
        if form.is_valid():
            disposed_qty = form.cleaned_data['quantity']
            method = form.cleaned_data['disposal_method']

            if disposed_qty > batch.available_quantity:
                messages.error(request, f"Cannot dispose {disposed_qty} units; batch only has {batch.available_quantity} available.")
                return render(request, 'inventory/batch_dispose.html', {'batch': batch, 'form': form})

            with transaction.atomic():
                batch.available_quantity -= disposed_qty
                batch.save()

                StockTransaction.objects.create(
                    medicine=batch.medicine,
                    batch=batch,
                    transaction_type=StockTransaction.TransactionType.DISPOSAL_EXPIRED,
                    quantity=disposed_qty,
                    unit_price=batch.purchase_price,
                    reference_note=f"Expired Stock Disposal: {method}",
                    performed_by=request.user
                )

            messages.success(request, f"Disposed {disposed_qty} units of expired stock from Batch {batch.batch_number}.")
            return redirect('batch_detail', pk=batch.pk)
        else:
            messages.error(request, "Please check the form inputs and try again.")
    else:
        initial_data = {'batch': batch, 'quantity': batch.available_quantity}
        form = BatchDisposalForm(initial=initial_data)

    return render(request, 'inventory/batch_dispose.html', {
        'batch': batch,
        'form': form,
    })


@admin_required
def category_list_view(request):
    categories = MedicineCategory.objects.annotate(
        medicine_count=Count('medicines')
    ).order_by('name')
    return render(request, 'inventory/category_list.html', {
        'categories': categories,
    })


@admin_required
def category_create_view(request):
    if request.method == 'POST':
        form = MedicineCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created.")
            return redirect('category_list')
        else:
            messages.error(request, "Failed to create category.")
    else:
        form = MedicineCategoryForm()

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'title': 'Add Medicine Category',
    })


@admin_required
def category_update_view(request, pk):
    category = get_object_or_404(MedicineCategory, pk=pk)
    if request.method == 'POST':
        form = MedicineCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect('category_list')
        else:
            messages.error(request, "Failed to update category.")
    else:
        form = MedicineCategoryForm(instance=category)

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'category': category,
        'title': f"Edit Category: {category.name}",
    })


@admin_required
def category_delete_view(request, pk):
    category = get_object_or_404(MedicineCategory, pk=pk)
    has_medicines = category.medicines.exists()

    if request.method == 'POST':
        if has_medicines:
            messages.error(request, f"Cannot delete category '{category.name}' as medicines are assigned to it.")
            return redirect('category_list')
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('category_list')

    return render(request, 'inventory/category_confirm_delete.html', {
        'category': category,
        'has_medicines': has_medicines,
    })


@staff_or_admin_required
def transaction_list_view(request):
    """Complete log of all stock movements and audit trails."""
    type_filter = request.GET.get('type', '')
    query = request.GET.get('q', '').strip()

    transactions = StockTransaction.objects.select_related('medicine', 'batch', 'performed_by')

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    if query:
        transactions = transactions.filter(
            Q(medicine__name__icontains=query) |
            Q(batch__batch_number__icontains=query) |
            Q(reference_note__icontains=query)
        )

    transactions = transactions.order_by('-timestamp')

    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/transaction_list.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'query': query,
        'types': StockTransaction.TransactionType.choices,
        'total_count': transactions.count(),
    })
