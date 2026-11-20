from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=150, help_text="Contact person name")
    company_name = models.CharField(max_length=200, help_text="Pharmaceutical supply/distribution company")
    contact_number = models.CharField(max_length=30)
    email = models.EmailField(max_length=254)
    address = models.TextField(help_text="Office/Warehouse physical address")
    notes = models.TextField(blank=True, null=True, help_text="Optional remarks, terms, or delivery notes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return f"{self.company_name} - {self.name}"

    @property
    def total_batches(self):
        return self.batches.count()

    @property
    def total_supplied_medicines(self):
        # Unique medicines supplied through batches
        return self.batches.values('medicine').distinct().count()
