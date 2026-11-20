from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from accounts.decorators import staff_or_admin_required, admin_required
from .models import Supplier
from .forms import SupplierForm


@staff_or_admin_required
def supplier_list_view(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    suppliers = Supplier.objects.annotate(
        batches_total=Count('batches')
    )

    if query:
        suppliers = suppliers.filter(
            Q(company_name__icontains=query) |
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(contact_number__icontains=query)
        )

    if status_filter == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status_filter == 'inactive':
        suppliers = suppliers.filter(is_active=False)

    return render(request, 'suppliers/supplier_list.html', {
        'suppliers': suppliers,
        'query': query,
        'status_filter': status_filter,
        'total_count': suppliers.count(),
    })


@staff_or_admin_required
def supplier_detail_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    batches = supplier.batches.select_related('medicine').order_by('-entry_date')
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier,
        'batches': batches,
    })


@admin_required
def supplier_create_view(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.company_name}' registered successfully.")
            return redirect('supplier_detail', pk=supplier.pk)
        else:
            messages.error(request, "Please review the form errors below.")
    else:
        form = SupplierForm()

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': 'Register New Pharmaceutical Supplier',
    })


@admin_required
def supplier_update_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.company_name}' updated successfully.")
            return redirect('supplier_detail', pk=supplier.pk)
        else:
            messages.error(request, "Please review the form errors below.")
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': f"Edit Supplier: {supplier.company_name}",
    })


@admin_required
def supplier_delete_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    has_batches = supplier.batches.exists()

    if request.method == 'POST':
        if has_batches:
            messages.error(request, f"Cannot delete supplier '{supplier.company_name}' because active batch records depend on it. Consider marking it inactive instead.")
            return redirect('supplier_detail', pk=supplier.pk)
        name = supplier.company_name
        supplier.delete()
        messages.success(request, f"Supplier '{name}' was removed successfully.")
        return redirect('supplier_list')

    return render(request, 'suppliers/supplier_confirm_delete.html', {
        'supplier': supplier,
        'has_batches': has_batches,
    })
