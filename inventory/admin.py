from django.contrib import admin
from .models import MedicineCategory, Medicine, MedicineBatch, StockTransaction


class MedicineBatchInline(admin.TabularInline):
    model = MedicineBatch
    extra = 0
    fields = ('batch_number', 'supplier', 'manufacturing_date', 'expiry_date', 'purchase_quantity', 'available_quantity', 'purchase_price')
    readonly_fields = ('created_at',)


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('medicine_id', 'name', 'generic_name', 'category', 'manufacturer', 'unit_price', 'minimum_stock_threshold', 'is_active')
    list_filter = ('category', 'is_active', 'dosage_form')
    search_fields = ('medicine_id', 'name', 'generic_name', 'manufacturer')
    inlines = [MedicineBatchInline]


@admin.register(MedicineBatch)
class MedicineBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'medicine', 'supplier', 'expiry_date', 'available_quantity', 'purchase_quantity', 'purchase_price')
    list_filter = ('expiry_date', 'supplier', 'entry_date')
    search_fields = ('batch_number', 'medicine__name', 'medicine__medicine_id')
    date_hierarchy = 'expiry_date'


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'transaction_type', 'medicine', 'batch', 'quantity', 'performed_by')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('medicine__name', 'batch__batch_number', 'reference_note')
    readonly_fields = ('timestamp',)
