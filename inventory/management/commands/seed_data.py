from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from suppliers.models import Supplier
from inventory.models import MedicineCategory, Medicine, MedicineBatch, StockTransaction
from notifications.services import ExpiryAlertService

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate pharmacy database with realistic demonstration medicines, categories, suppliers, batches, and users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Smart Pharmacy demonstration data..."))

        today = date.today()

        # 1. Create Users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@smartpharmacy.local',
                'first_name': 'Eleanor',
                'last_name': 'Vance',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'qualification': 'Pharm.D - Chief Pharmacist & Director',
                'phone_number': '+1 (555) 100-2000',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user: admin / admin123"))

        staff_user, created = User.objects.get_or_create(
            username='staff',
            defaults={
                'email': 'staff@smartpharmacy.local',
                'first_name': 'Marcus',
                'last_name': 'Reid',
                'role': User.Role.STAFF,
                'is_staff': False,
                'is_superuser': False,
                'qualification': 'B.Pharm - Clinical Staff Pharmacist',
                'phone_number': '+1 (555) 100-3000',
            }
        )
        if created:
            staff_user.set_password('staff123')
            staff_user.save()
            self.stdout.write(self.style.SUCCESS("Created staff user: staff / staff123"))

        staff_user2, created = User.objects.get_or_create(
            username='pharmacist1',
            defaults={
                'email': 'sarah.nurse@smartpharmacy.local',
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'role': User.Role.STAFF,
                'is_staff': False,
                'is_superuser': False,
                'qualification': 'Registered Pharmacy Technician',
                'phone_number': '+1 (555) 100-4000',
            }
        )
        if created:
            staff_user2.set_password('staff123')
            staff_user2.save()

        # 2. Create Suppliers
        suppliers_data = [
            {
                'company_name': 'Apex Pharma Distributors Ltd.',
                'name': 'Robert Smith',
                'contact_number': '+1 (555) 234-5678',
                'email': 'orders@apexpharma.com',
                'address': '124 Healthcare Boulevard, Suite 400, North Metro, IL',
                'notes': 'Primary distributor for generic antibiotics and cardiovascular medications. Net 30 payment terms.',
            },
            {
                'company_name': 'MediCare Global Supply Co.',
                'name': 'Eleanor Sterling',
                'contact_number': '+1 (555) 876-5432',
                'email': 'supply@medicareglobal.org',
                'address': '789 Logistics Parkway, Industrial Zone, OH',
                'notes': 'Cold chain specialist. Delivers insulin, respiratory inhalers, and biologicals.',
            },
            {
                'company_name': 'BioHealth Logistics Inc.',
                'name': 'David Chen',
                'contact_number': '+1 (555) 345-6789',
                'email': 'dchen@biohealthlogistics.com',
                'address': '55 Innovation Way, Tech Corridor, TX',
                'notes': 'Specialized vendor for analgesics, fever reducers, and OTC products.',
            },
            {
                'company_name': 'NovaCare Pharmaceuticals',
                'name': 'Amanda Price',
                'contact_number': '+1 (555) 901-2345',
                'email': 'sales@novacarepharma.net',
                'address': '210 Medical Center Drive, Boston, MA',
                'notes': 'Fast delivery for pediatric suspensions and gastrointestinal formulations.',
            },
        ]

        supplier_objs = {}
        for s_data in suppliers_data:
            s_obj, _ = Supplier.objects.get_or_create(
                company_name=s_data['company_name'],
                defaults=s_data
            )
            supplier_objs[s_data['company_name']] = s_obj

        # 3. Create Categories
        categories_data = [
            {'name': 'Antibiotics', 'code': 'ANT', 'description': 'Bacterial infection antimicrobials including penicillins, macrolides, and cephalosporins.'},
            {'name': 'Analgesics & Antipyretics', 'code': 'ANA', 'description': 'Pain management and fever reduction formulations including NSAIDs and acetaminophen.'},
            {'name': 'Cardiovascular', 'code': 'CAR', 'description': 'Hypertension, cholesterol management, and cardiac therapies.'},
            {'name': 'Diabetes Care', 'code': 'DIA', 'description': 'Oral hypoglycemic agents, insulin, and blood glucose management medicines.'},
            {'name': 'Respiratory', 'code': 'RES', 'description': 'Bronchodilators, antihistamines, and pulmonary disease therapeutics.'},
            {'name': 'Gastrointestinal', 'code': 'GAS', 'description': 'Proton pump inhibitors, antacids, and GI motility regulators.'},
            {'name': 'Vitamins & Supplements', 'code': 'VIT', 'description': 'Essential micronutrients, immune support, and dietary supplements.'},
        ]

        cat_objs = {}
        for c_data in categories_data:
            c_obj, _ = MedicineCategory.objects.get_or_create(
                code=c_data['code'],
                defaults=c_data
            )
            cat_objs[c_data['code']] = c_obj

        # 4. Create Medicines
        medicines_data = [
            {
                'medicine_id': 'MED-1001',
                'name': 'Amoxil 500mg',
                'generic_name': 'Amoxicillin Trihydrate',
                'category': cat_objs['ANT'],
                'manufacturer': 'GlaxoSmithKline',
                'dosage_form': 'CAPSULE',
                'strength': '500 mg',
                'unit_price': Decimal('14.50'),
                'minimum_stock_threshold': 30,
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'storage_conditions': 'Store below 25°C in dry conditions',
                'description': 'Broad-spectrum penicillin antibiotic indicated for ear, nose, throat, and respiratory infections.',
            },
            {
                'medicine_id': 'MED-1002',
                'name': 'Zithromax 250mg',
                'generic_name': 'Azithromycin Dihydrate',
                'category': cat_objs['ANT'],
                'manufacturer': 'Pfizer',
                'dosage_form': 'TABLET',
                'strength': '250 mg',
                'unit_price': Decimal('22.00'),
                'minimum_stock_threshold': 20,
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'storage_conditions': 'Store between 15°C and 30°C',
                'description': 'Macrolide antibiotic for mild to moderate bacterial infections including sinusitis and pneumonia.',
            },
            {
                'medicine_id': 'MED-1003',
                'name': 'Dolo 650',
                'generic_name': 'Paracetamol / Acetaminophen',
                'category': cat_objs['ANA'],
                'manufacturer': 'Micro Labs',
                'dosage_form': 'TABLET',
                'strength': '650 mg',
                'unit_price': Decimal('3.50'),
                'minimum_stock_threshold': 50,
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'storage_conditions': 'Room temperature away from moisture',
                'description': 'Antipyretic and analgesic for pain relief and fever management.',
            },
            {
                'medicine_id': 'MED-1004',
                'name': 'Advil 400mg',
                'generic_name': 'Ibuprofen',
                'category': cat_objs['ANA'],
                'manufacturer': 'Haleon',
                'dosage_form': 'TABLET',
                'strength': '400 mg',
                'unit_price': Decimal('8.00'),
                'minimum_stock_threshold': 25,
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'storage_conditions': 'Store at 20-25°C',
                'description': 'Nonsteroidal anti-inflammatory drug (NSAID) for inflammatory pain and headache relief.',
            },
            {
                'medicine_id': 'MED-1005',
                'name': 'Glucophage 500mg',
                'generic_name': 'Metformin Hydrochloride',
                'category': cat_objs['DIA'],
                'manufacturer': 'Merck',
                'dosage_form': 'TABLET',
                'strength': '500 mg',
                'unit_price': Decimal('11.20'),
                'minimum_stock_threshold': 40,
                'supplier': supplier_objs['MediCare Global Supply Co.'],
                'storage_conditions': 'Store below 25°C',
                'description': 'First-line biguanide oral medication for Type 2 diabetes glycemic control.',
            },
            {
                'medicine_id': 'MED-1006',
                'name': 'Lipitor 20mg',
                'generic_name': 'Atorvastatin Calcium',
                'category': cat_objs['CAR'],
                'manufacturer': 'Pfizer',
                'dosage_form': 'TABLET',
                'strength': '20 mg',
                'unit_price': Decimal('28.50'),
                'minimum_stock_threshold': 25,
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'storage_conditions': 'Store at 20°C to 25°C',
                'description': 'HMG-CoA reductase inhibitor (statin) for lowering cholesterol and cardiovascular risk reduction.',
            },
            {
                'medicine_id': 'MED-1007',
                'name': 'Norvasc 5mg',
                'generic_name': 'Amlodipine Besylate',
                'category': cat_objs['CAR'],
                'manufacturer': 'Viatris',
                'dosage_form': 'TABLET',
                'strength': '5 mg',
                'unit_price': Decimal('16.00'),
                'minimum_stock_threshold': 20,
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'storage_conditions': 'Protect from light, store below 30°C',
                'description': 'Calcium channel blocker for management of essential hypertension and coronary artery disease.',
            },
            {
                'medicine_id': 'MED-1008',
                'name': 'Prilosec 20mg',
                'generic_name': 'Omeprazole Delayed-Release',
                'category': cat_objs['GAS'],
                'manufacturer': 'AstraZeneca',
                'dosage_form': 'CAPSULE',
                'strength': '20 mg',
                'unit_price': Decimal('19.80'),
                'minimum_stock_threshold': 30,
                'supplier': supplier_objs['NovaCare Pharmaceuticals'],
                'storage_conditions': 'Store in original packaging below 25°C',
                'description': 'Proton pump inhibitor (PPI) for treatment of GERD, peptic ulcer, and gastric acid hypersecretion.',
            },
            {
                'medicine_id': 'MED-1009',
                'name': 'Ventolin HFA Inhaler',
                'generic_name': 'Albuterol / Salbutamol Sulfate',
                'category': cat_objs['RES'],
                'manufacturer': 'GSK',
                'dosage_form': 'INHALER',
                'strength': '100 mcg/actuation',
                'unit_price': Decimal('35.00'),
                'minimum_stock_threshold': 15,
                'supplier': supplier_objs['MediCare Global Supply Co.'],
                'storage_conditions': 'Store between 15°C and 25°C. Do not puncture canister.',
                'description': 'Short-acting beta2-adrenergic agonist for rapid relief of acute bronchospasm in asthma and COPD.',
            },
            {
                'medicine_id': 'MED-1010',
                'name': 'Zyrtec 10mg',
                'generic_name': 'Cetirizine Hydrochloride',
                'category': cat_objs['RES'],
                'manufacturer': 'Johnson & Johnson',
                'dosage_form': 'TABLET',
                'strength': '10 mg',
                'unit_price': Decimal('9.50'),
                'minimum_stock_threshold': 20,
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'storage_conditions': 'Store at 20° to 25°C',
                'description': 'Second-generation antihistamine for seasonal allergic rhinitis and chronic urticaria.',
            },
            {
                'medicine_id': 'MED-1011',
                'name': 'C-Vite 500mg',
                'generic_name': 'Ascorbic Acid (Vitamin C)',
                'category': cat_objs['VIT'],
                'manufacturer': 'Bayer',
                'dosage_form': 'TABLET',
                'strength': '500 mg',
                'unit_price': Decimal('6.00'),
                'minimum_stock_threshold': 30,
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'storage_conditions': 'Store below 25°C, protect from moisture',
                'description': 'Immune defense antioxidant supplement.',
            },
            {
                'medicine_id': 'MED-1012',
                'name': 'Zinc-Plus Complex',
                'generic_name': 'Zinc Gluconate & B-Complex',
                'category': cat_objs['VIT'],
                'manufacturer': 'Nature Bounty',
                'dosage_form': 'CAPSULE',
                'strength': '50 mg Zinc',
                'unit_price': Decimal('12.00'),
                'minimum_stock_threshold': 15,
                'supplier': supplier_objs['NovaCare Pharmaceuticals'],
                'storage_conditions': 'Dry cool location',
                'description': 'Nutritional dietary supplement for immune cellular health.',
            },
        ]

        med_objs = {}
        for m_data in medicines_data:
            m_obj, _ = Medicine.objects.get_or_create(
                medicine_id=m_data['medicine_id'],
                defaults=m_data
            )
            med_objs[m_data['medicine_id']] = m_obj

        # 5. Create Batches with deliberate distribution across all expiry tiers:
        # - EXPIRED (< today)
        # - CRITICAL (<= 7 days)
        # - URGENT (8 to 15 days)
        # - WARNING (16 to 30 days)
        # - SAFE (> 30 days)
        # - LOW STOCK / OUT OF STOCK

        batches_data = [
            # Amoxil 500mg
            {
                'medicine': med_objs['MED-1001'],
                'batch_number': 'AMX-2024-EXP1',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=700),
                'expiry_date': today - timedelta(days=25), # EXPIRED 25 days ago
                'purchase_quantity': 100,
                'available_quantity': 18, # 18 expired units quarantined
                'purchase_price': Decimal('9.00'),
                'entry_date': today - timedelta(days=650),
                'notes': 'Quarantined in storage room B for biomedical disposal.',
            },
            {
                'medicine': med_objs['MED-1001'],
                'batch_number': 'AMX-2025-CRIT',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=360),
                'expiry_date': today + timedelta(days=4), # CRITICAL: 4 days remaining!
                'purchase_quantity': 80,
                'available_quantity': 14,
                'purchase_price': Decimal('9.20'),
                'entry_date': today - timedelta(days=300),
                'notes': 'Front shelf - priority FEFO dispensing required.',
            },
            {
                'medicine': med_objs['MED-1001'],
                'batch_number': 'AMX-2026-SAFE',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=60),
                'expiry_date': today + timedelta(days=300), # SAFE
                'purchase_quantity': 150,
                'available_quantity': 140,
                'purchase_price': Decimal('8.80'),
                'entry_date': today - timedelta(days=45),
                'notes': 'Main stock shelf A-3.',
            },

            # Zithromax 250mg
            {
                'medicine': med_objs['MED-1002'],
                'batch_number': 'ZTH-2024-EXP',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=500),
                'expiry_date': today - timedelta(days=10), # EXPIRED 10 days ago
                'purchase_quantity': 50,
                'available_quantity': 12,
                'purchase_price': Decimal('14.00'),
                'entry_date': today - timedelta(days=450),
                'notes': 'Expired shelf quarantine.',
            },
            {
                'medicine': med_objs['MED-1002'],
                'batch_number': 'ZTH-2025-URG',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=300),
                'expiry_date': today + timedelta(days=12), # URGENT: 12 days
                'purchase_quantity': 60,
                'available_quantity': 22,
                'purchase_price': Decimal('14.50'),
                'entry_date': today - timedelta(days=280),
                'notes': 'Dispense first.',
            },

            # Dolo 650 (Set to LOW STOCK: Available 8 units, threshold is 50)
            {
                'medicine': med_objs['MED-1003'],
                'batch_number': 'DOL-2025-WARN',
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'manufacturing_date': today - timedelta(days=200),
                'expiry_date': today + timedelta(days=24), # WARNING: 24 days
                'purchase_quantity': 200,
                'available_quantity': 8, # Low stock condition!
                'purchase_price': Decimal('1.80'),
                'entry_date': today - timedelta(days=180),
                'notes': 'Critically low stock balance remaining.',
            },

            # Advil 400mg
            {
                'medicine': med_objs['MED-1004'],
                'batch_number': 'ADV-2026-SAFE',
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'manufacturing_date': today - timedelta(days=90),
                'expiry_date': today + timedelta(days=450), # SAFE
                'purchase_quantity': 120,
                'available_quantity': 110,
                'purchase_price': Decimal('4.50'),
                'entry_date': today - timedelta(days=80),
                'notes': 'Standard supply.',
            },

            # Glucophage 500mg
            {
                'medicine': med_objs['MED-1005'],
                'batch_number': 'GLU-2025-CRIT',
                'supplier': supplier_objs['MediCare Global Supply Co.'],
                'manufacturing_date': today - timedelta(days=400),
                'expiry_date': today + timedelta(days=6), # CRITICAL: 6 days
                'purchase_quantity': 90,
                'available_quantity': 15,
                'purchase_price': Decimal('6.80'),
                'entry_date': today - timedelta(days=380),
                'notes': 'Urgent dispensary bin 4.',
            },
            {
                'medicine': med_objs['MED-1005'],
                'batch_number': 'GLU-2026-SAFE',
                'supplier': supplier_objs['MediCare Global Supply Co.'],
                'manufacturing_date': today - timedelta(days=30),
                'expiry_date': today + timedelta(days=360), # SAFE
                'purchase_quantity': 100,
                'available_quantity': 95,
                'purchase_price': Decimal('6.50'),
                'entry_date': today - timedelta(days=20),
                'notes': 'Back room reserves.',
            },

            # Lipitor 20mg (Set to LOW STOCK: Available 14 units, threshold 25)
            {
                'medicine': med_objs['MED-1006'],
                'batch_number': 'LIP-2025-WARN',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=250),
                'expiry_date': today + timedelta(days=28), # WARNING: 28 days
                'purchase_quantity': 80,
                'available_quantity': 14, # Below threshold of 25
                'purchase_price': Decimal('18.00'),
                'entry_date': today - timedelta(days=240),
                'notes': 'Cardio stock low.',
            },

            # Norvasc 5mg
            {
                'medicine': med_objs['MED-1007'],
                'batch_number': 'NOR-2026-SAFE',
                'supplier': supplier_objs['Apex Pharma Distributors Ltd.'],
                'manufacturing_date': today - timedelta(days=80),
                'expiry_date': today + timedelta(days=500), # SAFE
                'purchase_quantity': 100,
                'available_quantity': 82,
                'purchase_price': Decimal('10.00'),
                'entry_date': today - timedelta(days=70),
                'notes': 'Cabinet C-2.',
            },

            # Prilosec 20mg
            {
                'medicine': med_objs['MED-1008'],
                'batch_number': 'PRL-2025-URG',
                'supplier': supplier_objs['NovaCare Pharmaceuticals'],
                'manufacturing_date': today - timedelta(days=350),
                'expiry_date': today + timedelta(days=14), # URGENT: 14 days
                'purchase_quantity': 75,
                'available_quantity': 26,
                'purchase_price': Decimal('12.50'),
                'entry_date': today - timedelta(days=320),
                'notes': 'GI shelves.',
            },

            # Ventolin HFA Inhaler (Set to OUT OF STOCK: 0 units)
            {
                'medicine': med_objs['MED-1009'],
                'batch_number': 'VEN-2024-DEP',
                'supplier': supplier_objs['MediCare Global Supply Co.'],
                'manufacturing_date': today - timedelta(days=300),
                'expiry_date': today + timedelta(days=200),
                'purchase_quantity': 40,
                'available_quantity': 0, # Fully depleted -> OUT OF STOCK!
                'purchase_price': Decimal('22.00'),
                'entry_date': today - timedelta(days=280),
                'notes': 'Depleted batch.',
            },

            # Zyrtec 10mg
            {
                'medicine': med_objs['MED-1010'],
                'batch_number': 'ZYR-2026-SAFE',
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'manufacturing_date': today - timedelta(days=40),
                'expiry_date': today + timedelta(days=420),
                'purchase_quantity': 150,
                'available_quantity': 135,
                'purchase_price': Decimal('5.20'),
                'entry_date': today - timedelta(days=35),
                'notes': 'Allergy stock.',
            },

            # C-Vite 500mg
            {
                'medicine': med_objs['MED-1011'],
                'batch_number': 'CVT-2024-EXP2',
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'manufacturing_date': today - timedelta(days=400),
                'expiry_date': today - timedelta(days=40), # EXPIRED 40 days ago
                'purchase_quantity': 100,
                'available_quantity': 35,
                'purchase_price': Decimal('3.00'),
                'entry_date': today - timedelta(days=380),
                'notes': 'Pending incinerator destruction.',
            },
            {
                'medicine': med_objs['MED-1011'],
                'batch_number': 'CVT-2026-SAFE',
                'supplier': supplier_objs['BioHealth Logistics Inc.'],
                'manufacturing_date': today - timedelta(days=20),
                'expiry_date': today + timedelta(days=350),
                'purchase_quantity': 100,
                'available_quantity': 90,
                'purchase_price': Decimal('3.10'),
                'entry_date': today - timedelta(days=15),
                'notes': 'Front counter OTC display.',
            },

            # Zinc-Plus Complex (Low Stock: 10 units, threshold 15)
            {
                'medicine': med_objs['MED-1012'],
                'batch_number': 'ZNC-2025-SAFE',
                'supplier': supplier_objs['NovaCare Pharmaceuticals'],
                'manufacturing_date': today - timedelta(days=100),
                'expiry_date': today + timedelta(days=250),
                'purchase_quantity': 50,
                'available_quantity': 10, # Below threshold of 15
                'purchase_price': Decimal('7.00'),
                'entry_date': today - timedelta(days=90),
                'notes': 'Low stock reorder advised.',
            },
        ]

        batch_objs = []
        for b_data in batches_data:
            b_obj, created = MedicineBatch.objects.get_or_create(
                medicine=b_data['medicine'],
                batch_number=b_data['batch_number'],
                defaults=b_data
            )
            batch_objs.append(b_obj)

            # Record initial Stock In Transaction if newly created
            if created:
                StockTransaction.objects.create(
                    medicine=b_obj.medicine,
                    batch=b_obj,
                    transaction_type=StockTransaction.TransactionType.PURCHASE,
                    quantity=b_obj.purchase_quantity,
                    unit_price=b_obj.purchase_price,
                    reference_note=f"Initial seed stock purchase from {b_obj.supplier.company_name}",
                    performed_by=admin_user
                )

        # 6. Add some realistic Dispense and Adjustment Transactions
        if not StockTransaction.objects.filter(transaction_type=StockTransaction.TransactionType.DISPENSE).exists():
            dispenses = [
                (med_objs['MED-1001'], batch_objs[1], 10, 'Rx #8812 - Dr. Vance / Patient: Alice'),
                (med_objs['MED-1003'], batch_objs[4], 25, 'Outpatient counter sale'),
                (med_objs['MED-1005'], batch_objs[6], 15, 'Rx #8845 - Diabetic Clinic'),
                (med_objs['MED-1006'], batch_objs[8], 12, 'Rx #8890 - Cardiology OPD'),
            ]
            for med, bch, qty, note in dispenses:
                StockTransaction.objects.create(
                    medicine=med,
                    batch=bch,
                    transaction_type=StockTransaction.TransactionType.DISPENSE,
                    quantity=qty,
                    unit_price=med.unit_price,
                    reference_note=note,
                    performed_by=staff_user
                )

        # 7. Execute initial Expiry Scan to populate ExpiryAlert records
        self.stdout.write(self.style.NOTICE("Running initial automated expiry alert check..."))
        summary = ExpiryAlertService.run_expiry_check(send_emails=False)

        self.stdout.write(self.style.SUCCESS(
            f"Demonstration data successfully generated!\n"
            f"- Users:         3 (Admin: admin / admin123, Staff: staff / staff123)\n"
            f"- Suppliers:     {len(supplier_objs)}\n"
            f"- Categories:    {len(cat_objs)}\n"
            f"- Medicines:     {len(med_objs)}\n"
            f"- Batches:       {len(batch_objs)}\n"
            f"- Expiry Alerts: {summary['new_notifications_created']} recorded\n"
        ))
