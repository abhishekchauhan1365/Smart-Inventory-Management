import csv
from datetime import date, timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from accounts.decorators import staff_or_admin_required, admin_required
from inventory.models import Medicine, MedicineBatch, MedicineCategory, StockTransaction
from suppliers.models import Supplier


@staff_or_admin_required
def reports_index_view(request):
    """Reports overview dashboard with quick metrics and links to detailed reports."""
    today = date.today()
    day30 = today + timedelta(days=30)

    total_meds = Medicine.objects.filter(is_active=True).count()
    expired_batches = MedicineBatch.objects.filter(expiry_date__lt=today, available_quantity__gt=0).count()
    near_expiry_batches = MedicineBatch.objects.filter(expiry_date__gte=today, expiry_date__lte=day30, available_quantity__gt=0).count()

    # Low stock count
    low_stock_count = 0
    for med in Medicine.objects.filter(is_active=True):
        if med.is_low_stock:
            low_stock_count += 1

    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_transactions = StockTransaction.objects.count()

    return render(request, 'reports/reports_index.html', {
        'total_meds': total_meds,
        'expired_batches': expired_batches,
        'near_expiry_batches': near_expiry_batches,
        'low_stock_count': low_stock_count,
        'total_suppliers': total_suppliers,
        'total_transactions': total_transactions,
    })


# 1. Complete Inventory Report
@staff_or_admin_required
def report_inventory_view(request):
    if request.GET.get('export') == 'csv':
        return export_inventory_csv()

    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')

    medicines = Medicine.objects.filter(is_active=True).select_related('category', 'supplier')
    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) | Q(generic_name__icontains=query) | Q(medicine_id__icontains=query)
        )
    if category_id:
        medicines = medicines.filter(category_id=category_id)

    medicines = medicines.order_by('name')

    categories = MedicineCategory.objects.filter(is_active=True)
    return render(request, 'reports/report_inventory.html', {
        'medicines': medicines,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'total_count': medicines.count(),
    })


def export_inventory_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="complete_inventory_report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Medicine ID', 'Medicine Name', 'Generic Name', 'Category', 'Manufacturer',
        'Unit Price ($)', 'Available Stock (Units)', 'Expired Stock (Units)', 'Min Threshold', 'Status', 'Supplier'
    ])

    for m in Medicine.objects.filter(is_active=True).select_related('category', 'supplier'):
        status = 'Out of Stock' if m.is_out_of_stock else ('Low Stock' if m.is_low_stock else 'Adequate')
        supplier_name = m.supplier.company_name if m.supplier else 'None'
        writer.writerow([
            m.medicine_id, m.name, m.generic_name, m.category.name, m.manufacturer,
            f"{m.unit_price:.2f}", m.total_available_stock, m.total_expired_stock,
            m.minimum_stock_threshold, status, supplier_name
        ])

    return response


# 2. Expired Medicines Report
@staff_or_admin_required
def report_expired_view(request):
    if request.GET.get('export') == 'csv':
        return export_expired_csv()

    today = date.today()
    batches = MedicineBatch.objects.filter(
        expiry_date__lt=today,
        available_quantity__gt=0
    ).select_related('medicine', 'supplier', 'medicine__category').order_by('expiry_date')

    total_units = sum(b.available_quantity for b in batches)
    total_loss = sum(b.available_quantity * b.purchase_price for b in batches)

    return render(request, 'reports/report_expired.html', {
        'batches': batches,
        'total_units': total_units,
        'total_loss': total_loss,
    })


def export_expired_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expired_medicines_report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Medicine ID', 'Medicine Name', 'Generic Name', 'Category', 'Batch #',
        'Expiry Date', 'Days Expired', 'Expired Quantity', 'Unit Purchase Price ($)', 'Estimated Value Loss ($)', 'Supplier'
    ])

    today = date.today()
    for b in MedicineBatch.objects.filter(expiry_date__lt=today, available_quantity__gt=0).select_related('medicine', 'supplier', 'medicine__category'):
        days_expired = (today - b.expiry_date).days
        loss = b.available_quantity * b.purchase_price
        writer.writerow([
            b.medicine.medicine_id, b.medicine.name, b.medicine.generic_name, b.medicine.category.name,
            b.batch_number, b.expiry_date.strftime('%Y-%m-%d'), days_expired,
            b.available_quantity, f"{b.purchase_price:.2f}", f"{loss:.2f}", b.supplier.company_name
        ])

    return response


# 3. Near Expiry Report
@staff_or_admin_required
def report_near_expiry_view(request):
    if request.GET.get('export') == 'csv':
        return export_near_expiry_csv(request.GET.get('window', '30'))

    today = date.today()
    window = request.GET.get('window', '30')

    if window == '7':
        limit_date = today + timedelta(days=7)
    elif window == '15':
        limit_date = today + timedelta(days=15)
    else:
        window = '30'
        limit_date = today + timedelta(days=30)

    batches = MedicineBatch.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=limit_date,
        available_quantity__gt=0
    ).select_related('medicine', 'supplier', 'medicine__category').order_by('expiry_date')

    total_units = sum(b.available_quantity for b in batches)

    return render(request, 'reports/report_near_expiry.html', {
        'batches': batches,
        'window': window,
        'total_units': total_units,
    })


def export_near_expiry_csv(window='30'):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="near_expiry_report_{window}days_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Medicine ID', 'Medicine Name', 'Generic Name', 'Category', 'Batch #',
        'Expiry Date', 'Days Remaining', 'Available Quantity', 'Purchase Price ($)', 'Supplier'
    ])

    today = date.today()
    days_int = int(window) if window in ['7', '15', '30'] else 30
    limit_date = today + timedelta(days=days_int)

    for b in MedicineBatch.objects.filter(expiry_date__gte=today, expiry_date__lte=limit_date, available_quantity__gt=0).select_related('medicine', 'supplier', 'medicine__category').order_by('expiry_date'):
        days_rem = (b.expiry_date - today).days
        writer.writerow([
            b.medicine.medicine_id, b.medicine.name, b.medicine.generic_name, b.medicine.category.name,
            b.batch_number, b.expiry_date.strftime('%Y-%m-%d'), days_rem,
            b.available_quantity, f"{b.purchase_price:.2f}", b.supplier.company_name
        ])

    return response


# 4. Low Stock Report
@staff_or_admin_required
def report_low_stock_view(request):
    if request.GET.get('export') == 'csv':
        return export_low_stock_csv()

    medicines = Medicine.objects.filter(is_active=True).select_related('category', 'supplier')
    low_stock_list = []
    for med in medicines:
        if med.is_low_stock:
            low_stock_list.append(med)

    return render(request, 'reports/report_low_stock.html', {
        'medicines': low_stock_list,
        'total_count': len(low_stock_list),
    })


def export_low_stock_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="low_stock_report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Medicine ID', 'Medicine Name', 'Generic Name', 'Category',
        'Available Non-Expired Stock', 'Min Threshold', 'Deficit', 'Status', 'Preferred Supplier', 'Supplier Phone'
    ])

    for m in Medicine.objects.filter(is_active=True).select_related('category', 'supplier'):
        if m.is_low_stock:
            stock = m.total_available_stock
            deficit = max(0, m.minimum_stock_threshold - stock)
            status = 'Out of Stock' if stock == 0 else 'Critical Low'
            sup_name = m.supplier.company_name if m.supplier else 'N/A'
            sup_phone = m.supplier.contact_number if m.supplier else 'N/A'
            writer.writerow([
                m.medicine_id, m.name, m.generic_name, m.category.name,
                stock, m.minimum_stock_threshold, deficit, status, sup_name, sup_phone
            ])

    return response


# 5. Supplier-wise Inventory Report
@staff_or_admin_required
def report_suppliers_view(request):
    if request.GET.get('export') == 'csv':
        return export_suppliers_csv()

    suppliers = Supplier.objects.filter(is_active=True).prefetch_related('batches')
    supplier_data = []

    for sup in suppliers:
        batches = sup.batches.all()
        total_batches = batches.count()
        total_units = sum(b.available_quantity for b in batches)
        total_value = sum(b.available_quantity * b.purchase_price for b in batches)
        supplier_data.append({
            'supplier': sup,
            'total_batches': total_batches,
            'total_units': total_units,
            'total_value': total_value,
        })

    return render(request, 'reports/report_suppliers.html', {
        'supplier_data': supplier_data,
    })


def export_suppliers_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="supplier_inventory_report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Company Name', 'Contact Person', 'Phone', 'Email',
        'Total Batches Supplied', 'Current Active Units in Stock', 'Total Inventory Value ($)'
    ])

    for sup in Supplier.objects.filter(is_active=True):
        batches = sup.batches.all()
        total_batches = batches.count()
        total_units = sum(b.available_quantity for b in batches)
        total_value = sum(b.available_quantity * b.purchase_price for b in batches)
        writer.writerow([
            sup.company_name, sup.name, sup.contact_number, sup.email,
            total_batches, total_units, f"{total_value:.2f}"
        ])

    return response


# 6. Stock Movement Report
@staff_or_admin_required
def report_stock_movement_view(request):
    if request.GET.get('export') == 'csv':
        return export_stock_movement_csv(request.GET.get('type', ''))

    type_filter = request.GET.get('type', '')
    transactions = StockTransaction.objects.select_related('medicine', 'batch', 'performed_by')

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    transactions = transactions.order_by('-timestamp')

    paginator = Paginator(transactions, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reports/report_stock_movement.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'types': StockTransaction.TransactionType.choices,
        'total_count': transactions.count(),
    })


def export_stock_movement_csv(type_filter=''):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="stock_movement_report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'Transaction Type', 'Medicine Name', 'Medicine ID', 'Batch Number',
        'Quantity', 'Unit Price ($)', 'Performed By', 'Reference Notes'
    ])

    qs = StockTransaction.objects.select_related('medicine', 'batch', 'performed_by')
    if type_filter:
        qs = qs.filter(transaction_type=type_filter)
    qs = qs.order_by('-timestamp')

    for t in qs:
        batch_num = t.batch.batch_number if t.batch else 'N/A'
        user_name = t.performed_by.username if t.performed_by else 'System'
        price = f"{t.unit_price:.2f}" if t.unit_price else 'N/A'
        writer.writerow([
            t.timestamp.strftime('%Y-%m-%d %H:%M:%S'), t.get_transaction_type_display(),
            t.medicine.name, t.medicine.medicine_id, batch_num,
            t.quantity, price, user_name, t.reference_note or ''
        ])

    return response
