from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from suppliers.models import Supplier
from inventory.models import MedicineCategory, Medicine, MedicineBatch, StockTransaction

User = get_user_model()


class InventorySystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testpharmacist',
            password='password123',
            role=User.Role.STAFF
        )
        self.supplier = Supplier.objects.create(
            name='Test Contact',
            company_name='Test Pharma Ltd',
            contact_number='+1 555-0199',
            email='test@pharma.com',
            address='100 Medical Plaza'
        )
        self.category = MedicineCategory.objects.create(
            name='Antibiotics',
            code='ANT',
            description='Test category'
        )
        self.medicine = Medicine.objects.create(
            medicine_id='MED-TEST-01',
            name='Test Cillin 500mg',
            generic_name='Testcillin',
            category=self.category,
            manufacturer='Test Labs',
            unit_price=Decimal('10.00'),
            minimum_stock_threshold=20,
            supplier=self.supplier
        )

    def test_medicine_stock_calculation_excludes_expired_batches(self):
        today = date.today()

        # Batch 1: Expired (10 units)
        MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='BATCH-EXP',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=400),
            expiry_date=today - timedelta(days=10),
            purchase_quantity=50,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )

        # Batch 2: Valid non-expired (40 units)
        MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='BATCH-VALID',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=50),
            expiry_date=today + timedelta(days=200),
            purchase_quantity=50,
            available_quantity=40,
            purchase_price=Decimal('5.00')
        )

        # Verify: Usable available stock must equal ONLY the valid batch (40 units)
        self.assertEqual(self.medicine.total_available_stock, 40)
        # Verify: Expired stock is isolated and tracked separately (10 units)
        self.assertEqual(self.medicine.total_expired_stock, 10)
        # Verify: Low stock is False because 40 > 20 threshold
        self.assertFalse(self.medicine.is_low_stock)

    def test_low_stock_trigger(self):
        today = date.today()
        # Add valid batch with only 15 units (threshold is 20)
        MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='BATCH-LOW',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=20),
            expiry_date=today + timedelta(days=150),
            purchase_quantity=50,
            available_quantity=15,
            purchase_price=Decimal('5.00')
        )

        self.assertEqual(self.medicine.total_available_stock, 15)
        self.assertTrue(self.medicine.is_low_stock)

    def test_batch_expiry_categories(self):
        today = date.today()

        b_expired = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-EXP',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=365),
            expiry_date=today - timedelta(days=1),
            purchase_quantity=10,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )
        self.assertEqual(b_expired.expiry_category, 'EXPIRED')

        b_critical = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-CRIT',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=300),
            expiry_date=today + timedelta(days=5),
            purchase_quantity=10,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )
        self.assertEqual(b_critical.expiry_category, 'CRITICAL_7')

        b_urgent = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-URG',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=300),
            expiry_date=today + timedelta(days=12),
            purchase_quantity=10,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )
        self.assertEqual(b_urgent.expiry_category, 'URGENT_15')

        b_warning = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-WARN',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=300),
            expiry_date=today + timedelta(days=25),
            purchase_quantity=10,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )
        self.assertEqual(b_warning.expiry_category, 'WARNING_30')

        b_valid = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-SAFE',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=300),
            purchase_quantity=10,
            available_quantity=10,
            purchase_price=Decimal('5.00')
        )
        self.assertEqual(b_valid.expiry_category, 'VALID')

    def test_landing_page_renders_for_unauthenticated_users(self):
        from django.urls import reverse
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FEFO")
        self.assertContains(response, "SmartRx")

    def test_batch_dispose_view_executes_successfully(self):
        from django.urls import reverse
        today = date.today()
        expired_batch = MedicineBatch.objects.create(
            medicine=self.medicine,
            batch_number='B-DISPOSE-TEST',
            supplier=self.supplier,
            manufacturing_date=today - timedelta(days=400),
            expiry_date=today - timedelta(days=20),
            purchase_quantity=30,
            available_quantity=30,
            purchase_price=Decimal('4.50')
        )
        self.client.force_login(self.user)
        url = reverse('batch_dispose', kwargs={'pk': expired_batch.pk})

        # Test GET loads form
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)

        # Test POST executes disposal
        post_data = {
            'quantity': 30,
            'disposal_method': 'Incineration via clinical waste contractor'
        }
        post_res = self.client.post(url, data=post_data)
        self.assertEqual(post_res.status_code, 302)

        expired_batch.refresh_from_db()
        self.assertEqual(expired_batch.available_quantity, 0)
        self.assertTrue(StockTransaction.objects.filter(
            batch=expired_batch,
            transaction_type=StockTransaction.TransactionType.DISPOSAL_EXPIRED
        ).exists())
