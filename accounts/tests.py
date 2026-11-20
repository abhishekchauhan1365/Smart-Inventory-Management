from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from inventory.models import Medicine, MedicineCategory
from suppliers.models import Supplier

User = get_user_model()


class WebRouteIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@test.com',
            password='adminpassword',
            role=User.Role.ADMIN
        )
        self.staff_user = User.objects.create_user(
            username='teststaff',
            email='staff@test.com',
            password='staffpassword',
            role=User.Role.STAFF
        )

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_login_and_dashboard_access(self):
        logged_in = self.client.login(username='teststaff', password='staffpassword')
        self.assertTrue(logged_in)

        # Dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory & Expiry Control Dashboard")

        # Medicines List
        response = self.client.get(reverse('medicine_list'))
        self.assertEqual(response.status_code, 200)

        # Batches List
        response = self.client.get(reverse('batch_list'))
        self.assertEqual(response.status_code, 200)

        # Reports index
        response = self.client.get(reverse('reports_index'))
        self.assertEqual(response.status_code, 200)

        # CSV Export test
        response = self.client.get(reverse('report_inventory') + '?export=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_admin_staff_management_access(self):
        # Staff cannot access staff_list
        self.client.login(username='teststaff', password='staffpassword')
        res = self.client.get(reverse('staff_list'))
        self.assertEqual(res.status_code, 302) # Denied and redirected

        # Admin can access staff_list
        self.client.login(username='testadmin', password='adminpassword')
        res = self.client.get(reverse('staff_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Pharmacy Staff Accounts")
