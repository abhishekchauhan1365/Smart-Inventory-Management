from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from suppliers.models import Supplier
from inventory.models import MedicineCategory, Medicine, MedicineBatch
from notifications.models import ExpiryNotification
from notifications.services import ExpiryAlertService


class ExpiryAlertServiceTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            company_name='Alert Supplier Ltd',
            contact_number='+1 555-9988',
            email='supplier@alert.com',
            address='123 Supply Ave'
        )
        self.category = MedicineCategory.objects.create(
            name='Pain Relief',
            code='PNR',
            description='Test'
        )
        self.medicine = Medicine.objects.create(
            medicine_id='MED-ALERT-01',
            name='Alert Pain Reliever',
            generic_name='Analgesic Complex',
            category=self.category,
            manufacturer='Alert Corp',
            unit_price=Decimal('5.00'),
            minimum_stock_threshold=10,
            supplier=self.supplier
        )

    def test_alert_generation_and_deduplication(self):
        today = date.today()

        # Create batch expiring in 5 days (CRITICAL_7 category)
        batch = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='LOT-CRIT-001',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=200),
            expiry_date=today + timedelta(days=5),
            purchase_quantity=30,
            available_quantity=30,
            purchase_price=Decimal('2.50')
        )

        # 1st Run: Should create 1 new notification
        summary1 = ExpiryAlertService.run_expiry_check(send_emails=False)
        self.assertEqual(summary1['critical_7'], 1)
        self.assertEqual(summary1['new_notifications_created'], 1)
        self.assertEqual(summary1['duplicates_skipped'], 0)
        self.assertEqual(ExpiryNotification.objects.filter(batch=batch).count(), 1)

        # 2nd Run immediately: Should recognize existing alert and SKIP duplicate!
        summary2 = ExpiryAlertService.run_expiry_check(send_emails=False)
        self.assertEqual(summary2['new_notifications_created'], 0)
        self.assertEqual(summary2['duplicates_skipped'], 1)
        self.assertEqual(ExpiryNotification.objects.filter(batch=batch).count(), 1)
