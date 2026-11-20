from datetime import date
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.conf import settings
from suppliers.models import Supplier


class MedicineCategory(models.Model):
    name = models.CharField(max_length=120, unique=True, help_text="e.g. Antibiotics, Analgesics, Antipyretics")
    code = models.CharField(max_length=20, unique=True, help_text="Short code, e.g. ANT, ANA, CAR")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Medicine Category'
        verbose_name_plural = 'Medicine Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_medicines(self):
        return self.medicines.filter(is_active=True).count()


class Medicine(models.Model):
    DOSAGE_FORMS = [
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('SYRUP', 'Syrup / Oral Liquid'),
        ('INJECTION', 'Injection / Vial'),
        ('OINTMENT', 'Ointment / Gel / Cream'),
        ('DROPS', 'Eye / Ear Drops'),
        ('INHALER', 'Inhaler / Respules'),
        ('POWDER', 'Powder / Granules'),
        ('OTHER', 'Other'),
    ]

    medicine_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique Medicine ID/SKU, e.g. MED-1001"
    )
    name = models.CharField(max_length=200, help_text="Brand or Commercial Name, e.g. Amoxil 500mg")
    generic_name = models.CharField(max_length=200, help_text="Generic active ingredient, e.g. Amoxicillin")
    category = models.ForeignKey(
        MedicineCategory,
        on_delete=models.PROTECT,
        related_name='medicines'
    )
    manufacturer = models.CharField(max_length=150, help_text="Manufacturing pharma company, e.g. GSK, Pfizer")
    description = models.TextField(blank=True, null=True, help_text="Indications, usage notes or storage guidelines")
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Standard selling price per unit"
    )
    minimum_stock_threshold = models.PositiveIntegerField(
        default=20,
        help_text="Threshold for triggering low-stock alert"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_medicines',
        help_text="Primary / preferred supplier"
    )
    dosage_form = models.CharField(max_length=30, choices=DOSAGE_FORMS, default='TABLET')
    strength = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 500mg, 10mg/5ml, 2%")
    storage_conditions = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="Store below 25°C in a dry place",
        help_text="Storage instructions"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Medicine'
        verbose_name_plural = 'Medicines'

    def __str__(self):
        return f"{self.name} ({self.medicine_id})"

    @property
    def total_available_stock(self):
        """
        Total quantity of all non-expired batches currently available.
        Per system requirements: Expired batches are excluded from available stock.
        """
        today = date.today()
        batches = self.batches.filter(expiry_date__gte=today, available_quantity__gt=0)
        return sum(b.available_quantity for b in batches)

    @property
    def total_expired_stock(self):
        """
        Total units in expired batches that have not yet been disposed.
        """
        today = date.today()
        batches = self.batches.filter(expiry_date__lt=today, available_quantity__gt=0)
        return sum(b.available_quantity for b in batches)

    @property
    def total_physical_stock(self):
        """Total physical units on shelf (both valid and expired)."""
        return sum(b.available_quantity for b in self.batches.filter(available_quantity__gt=0))

    @property
    def is_low_stock(self):
        """Low stock flag based on non-expired available stock."""
        return self.total_available_stock <= self.minimum_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.total_available_stock == 0

    @property
    def stock_status(self):
        if self.is_out_of_stock:
            return 'OUT_OF_STOCK'
        if self.is_low_stock:
            return 'LOW_STOCK'
        return 'IN_STOCK'

    @property
    def stock_status_badge(self):
        if self.is_out_of_stock:
            return {'class': 'bg-danger', 'label': 'Out of Stock'}
        if self.is_low_stock:
            return {'class': 'bg-warning text-dark', 'label': 'Low Stock'}
        return {'class': 'bg-success', 'label': 'Adequate Stock'}

    @property
    def nearest_expiry_batch(self):
        """Returns active batch with earliest expiry date."""
        return self.batches.filter(available_quantity__gt=0).order_by('expiry_date').first()


class MedicineBatch(models.Model):
    batch_number = models.CharField(
        max_length=60,
        help_text="Manufacturer batch/lot number, e.g. LOT-2024-981"
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    manufacturing_date = models.DateField(help_text="Date the batch was manufactured")
    expiry_date = models.DateField(help_text="Expiry date marked on packaging")
    purchase_quantity = models.PositiveIntegerField(help_text="Quantity received when batch was entered")
    available_quantity = models.PositiveIntegerField(help_text="Current available balance for this batch")
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Purchase cost per unit"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='batches',
        help_text="Supplier delivering this batch"
    )
    entry_date = models.DateField(default=timezone.now, help_text="Date of stock entry into pharmacy")
    notes = models.TextField(blank=True, null=True, help_text="Batch specific remarks (e.g. storage bin)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiry_date', 'batch_number']
        verbose_name = 'Medicine Batch'
        verbose_name_plural = 'Medicine Batches'
        unique_together = ('medicine', 'batch_number')

    def __str__(self):
        return f"{self.medicine.name} - Batch: {self.batch_number} (Exp: {self.expiry_date})"

    @property
    def days_to_expiry(self):
        """Number of days until expiry (negative if already expired)."""
        today = date.today()
        return (self.expiry_date - today).days

    @property
    def is_expired(self):
        return self.days_to_expiry < 0

    @property
    def expiry_category(self):
        """
        Categorization as per system specification:
        - Already expired (< 0 days)
        - Expiring within 7 days (0 to 7 days)
        - Expiring within 15 days (8 to 15 days)
        - Expiring within 30 days (16 to 30 days)
        - Valid (> 30 days)
        """
        days = self.days_to_expiry
        if days < 0:
            return 'EXPIRED'
        elif days <= 7:
            return 'CRITICAL_7'
        elif days <= 15:
            return 'URGENT_15'
        elif days <= 30:
            return 'WARNING_30'
        else:
            return 'VALID'

    @property
    def expiry_status_label(self):
        category = self.expiry_category
        days = self.days_to_expiry
        if category == 'EXPIRED':
            abs_days = abs(days)
            return f"Expired ({abs_days} day{'s' if abs_days != 1 else ''} ago)"
        elif category == 'CRITICAL_7':
            return f"Expiring in {days} day{'s' if days != 1 else ''} (<= 7d)"
        elif category == 'URGENT_15':
            return f"Expiring in {days} days (<= 15d)"
        elif category == 'WARNING_30':
            return f"Expiring in {days} days (<= 30d)"
        else:
            return f"Safe ({days} days remaining)"

    @property
    def expiry_badge(self):
        category = self.expiry_category
        if category == 'EXPIRED':
            return {'class': 'bg-danger text-white', 'icon': 'bi-x-octagon-fill', 'level': 'Expired'}
        elif category == 'CRITICAL_7':
            return {'class': 'bg-danger text-white', 'icon': 'bi-exclamation-triangle-fill', 'level': 'Critical (<=7d)'}
        elif category == 'URGENT_15':
            return {'class': 'bg-warning text-dark', 'icon': 'bi-exclamation-circle-fill', 'level': 'Urgent (<=15d)'}
        elif category == 'WARNING_30':
            return {'class': 'bg-info text-dark', 'icon': 'bi-info-circle-fill', 'level': 'Notice (<=30d)'}
        else:
            return {'class': 'bg-success text-white', 'icon': 'bi-check-circle-fill', 'level': 'Safe'}


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Stock In (Purchase/Batch Entry)'
        DISPENSE = 'DISPENSE', 'Stock Out (Dispense/Sale)'
        ADJUSTMENT = 'ADJUSTMENT', 'Stock Adjustment (Inventory Audit)'
        RETURN = 'RETURN', 'Stock Return (To Supplier)'
        DISPOSAL_EXPIRED = 'DISPOSAL_EXPIRED', 'Disposal of Expired Medicine'

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    batch = models.ForeignKey(
        MedicineBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    quantity = models.IntegerField(
        help_text="Units added (positive) or removed (positive number representing deduction)"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Unit price associated with this transaction"
    )
    reference_note = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Prescription ID, Invoice #, or Reason"
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_transactions'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.medicine.name} ({self.quantity} units)"
