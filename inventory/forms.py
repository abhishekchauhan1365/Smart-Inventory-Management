from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from .models import MedicineCategory, Medicine, MedicineBatch, StockTransaction
from suppliers.models import Supplier


class MedicineCategoryForm(forms.ModelForm):
    class Meta:
        model = MedicineCategory
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Antibiotics'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ANT'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Category clinical usage notes'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'medicine_id', 'name', 'generic_name', 'category', 'manufacturer',
            'dosage_form', 'strength', 'unit_price', 'minimum_stock_threshold',
            'supplier', 'storage_conditions', 'description', 'is_active'
        ]
        widgets = {
            'medicine_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MED-1001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand Name (e.g. Amoxil 500mg)'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Generic Name (e.g. Amoxicillin Trihydrate)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. GlaxoSmithKline'}),
            'dosage_form': forms.Select(attrs={'class': 'form-select'}),
            'strength': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500mg'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'minimum_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'storage_conditions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Store below 25°C'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Therapeutic indications, warnings, packaging details'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if price is not None and price <= 0:
            raise ValidationError("Unit selling price must be greater than zero.")
        return price


class MedicineBatchForm(forms.ModelForm):
    class Meta:
        model = MedicineBatch
        fields = [
            'medicine', 'batch_number', 'supplier', 'manufacturing_date', 'expiry_date',
            'purchase_quantity', 'purchase_price', 'entry_date', 'notes'
        ]
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-select'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. LOT-2024-889'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'manufacturing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purchase_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bin location, storage shelf, delivery invoice #'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # New batch defaults
            self.fields['entry_date'].initial = date.today()

    def clean(self):
        cleaned_data = super().clean()
        mfg = cleaned_data.get('manufacturing_date')
        exp = cleaned_data.get('expiry_date')

        if mfg and exp and exp <= mfg:
            self.add_error('expiry_date', "Expiry date must be strictly after the manufacturing date.")

        return cleaned_data


class MedicineBatchEditForm(forms.ModelForm):
    class Meta:
        model = MedicineBatch
        fields = [
            'batch_number', 'supplier', 'manufacturing_date', 'expiry_date',
            'available_quantity', 'purchase_price', 'notes'
        ]
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'manufacturing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        mfg = cleaned_data.get('manufacturing_date')
        exp = cleaned_data.get('expiry_date')
        if mfg and exp and exp <= mfg:
            self.add_error('expiry_date', "Expiry date must be after manufacturing date.")
        return cleaned_data


class StockDispenseForm(forms.Form):
    """Dispense stock from a non-expired batch."""
    batch = forms.ModelChoiceField(
        queryset=MedicineBatch.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity to dispense', 'min': '1'})
    )
    reference_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prescription ID / Patient Name / Doctor'})
    )

    def __init__(self, *args, medicine=None, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today()
        if medicine:
            # Only allow dispensing from non-expired batches with available quantity!
            self.fields['batch'].queryset = medicine.batches.filter(
                expiry_date__gte=today,
                available_quantity__gt=0
            ).order_by('expiry_date')
            self.medicine = medicine

    def clean(self):
        cleaned_data = super().clean()
        batch = cleaned_data.get('batch')
        quantity = cleaned_data.get('quantity')

        if batch and quantity:
            if batch.is_expired:
                raise ValidationError("Cannot dispense from an expired batch!")
            if quantity > batch.available_quantity:
                raise ValidationError(f"Requested quantity ({quantity}) exceeds available batch stock ({batch.available_quantity}).")
        return cleaned_data


class StockAdjustmentForm(forms.Form):
    """Adjust batch stock during inventory audit or damage report."""
    batch = forms.ModelChoiceField(
        queryset=MedicineBatch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ADJUSTMENT_ACTIONS = [
        ('ADD', 'Add Units (Surplus Audit Correction)'),
        ('DEDUCT', 'Deduct Units (Damage / Shrinkage / Discrepancy)'),
    ]
    action = forms.ChoiceField(
        choices=ADJUSTMENT_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of units'})
    )
    reason = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for adjustment (e.g. Audit variance)'})
    )


class BatchDisposalForm(forms.Form):
    """Disposal of expired batches."""
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    disposal_method = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Disposal protocol (e.g. Biomedical waste incinerator / Return to pharma rep)'
        })
    )
    batch = forms.ModelChoiceField(
        queryset=MedicineBatch.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
