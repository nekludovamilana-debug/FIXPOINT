from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import (
    RepairRequest, Service, StockPart, RepairStatusHistory, RepairPartUsage
)

User = get_user_model()


class RepairWorkflowTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='client', password='StrongPass123!')
        self.master = User.objects.create_user(
            username='master', password='StrongPass123!', is_staff=True
        )
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='StrongPass123!'
        )
        self.service = Service.objects.create(
            name='Диагностика', category='computer',
            description='Проверка устройства', price='1500.00',
            duration='1 день', is_active=True
        )

    def create_repair(self, **kwargs):
        defaults = {
            'user': self.customer,
            'customer_name': 'Тестовый клиент',
            'phone': '+79990000000',
            'device': 'Ноутбук',
            'problem': 'Не включается',
            'service': self.service,
            'service_price': self.service.price,
            'status': 'new',
        }
        defaults.update(kwargs)
        return RepairRequest.objects.create(**defaults)

    def test_guest_is_redirected_to_login_before_creating_request(self):
        response = self.client.get(reverse('create_request'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_master_sees_only_assigned_repairs(self):
        assigned = self.create_repair(assigned_master=self.master)
        self.create_repair(assigned_master=None, customer_name='Другая заявка')
        self.client.force_login(self.master)
        response = self.client.get(reverse('master_panel'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, assigned.device)
        self.assertNotContains(response, 'Другая заявка')

    def test_status_change_is_saved_to_history(self):
        repair = self.create_repair(assigned_master=self.master)
        self.client.force_login(self.master)
        response = self.client.post(reverse('master_panel'), {
            'repair_id': repair.pk,
            'status': 'diagnostics',
            'action': 'status',
        })
        self.assertEqual(response.status_code, 302)
        repair.refresh_from_db()
        self.assertEqual(repair.status, 'diagnostics')
        self.assertTrue(
            RepairStatusHistory.objects.filter(
                repair=repair, old_status='new', new_status='diagnostics',
                changed_by=self.master
            ).exists()
        )

    def test_stock_usage_decreases_stock_quantity(self):
        repair = self.create_repair(assigned_master=self.master)
        part = StockPart.objects.create(
            name='SSD 256 GB', category='Накопители',
            quantity=5, min_quantity=1, price='2500.00'
        )
        self.client.force_login(self.master)
        response = self.client.post(
            reverse('repair_detail', args=[repair.pk]),
            {'action': 'add_part', 'part': part.pk, 'quantity': 2}
        )
        self.assertEqual(response.status_code, 302)
        part.refresh_from_db()
        self.assertEqual(part.quantity, 3)
        usage = RepairPartUsage.objects.get(repair=repair, part=part)
        self.assertEqual(usage.quantity, 2)
        self.assertEqual(usage.unit_price, part.price)

    def test_customer_cannot_open_another_customers_repair(self):
        repair = self.create_repair()
        other = User.objects.create_user(username='other', password='StrongPass123!')
        self.client.force_login(other)
        response = self.client.get(reverse('repair_detail', args=[repair.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('account'))

    def test_admin_can_assign_repair_to_staff_member(self):
        repair = self.create_repair()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('master_panel'), {
            'action': 'assign',
            'repair_id': repair.pk,
            'assigned_master': self.master.pk,
        })
        self.assertEqual(response.status_code, 302)
        repair.refresh_from_db()
        self.assertEqual(repair.assigned_master, self.master)

    def test_assigned_master_can_open_repair_details(self):
        repair = self.create_repair(assigned_master=self.master)
        self.client.force_login(self.master)
        response = self.client.get(reverse('repair_detail', args=[repair.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'История статусов')
        self.assertContains(response, 'Использованные запчасти')

    def test_superuser_can_open_assignment_panel(self):
        self.create_repair()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('master_panel'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Назначенный мастер')
        self.assertContains(response, 'Без мастера')


class ExtendedRequirementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='rootadmin', email='root@example.com', password='StrongPass123!'
        )
        self.master = User.objects.create_user(
            username='worker', password='StrongPass123!', is_staff=True
        )
        self.customer = User.objects.create_user(username='buyer', password='StrongPass123!')
        self.service = Service.objects.create(
            name='Ремонт', category='computer', description='Работы',
            price='1000.00', duration='1 день'
        )
        self.repair = RepairRequest.objects.create(
            user=self.customer, assigned_master=self.master, service=self.service,
            service_price='1000.00', customer_name='Клиент', phone='+79990000000',
            device='ПК', problem='Не запускается'
        )

    def test_master_can_save_separate_labor_cost(self):
        self.client.force_login(self.master)
        response = self.client.post(
            reverse('repair_detail', args=[self.repair.pk]),
            {'action': 'labor_cost', 'labor_cost': '750.50'}
        )
        self.assertEqual(response.status_code, 302)
        self.repair.refresh_from_db()
        self.assertEqual(str(self.repair.labor_cost), '750.50')

    def test_negative_labor_cost_is_rejected(self):
        self.client.force_login(self.master)
        response = self.client.post(
            reverse('repair_detail', args=[self.repair.pk]),
            {'action': 'labor_cost', 'labor_cost': '-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.repair.refresh_from_db()
        self.assertEqual(str(self.repair.labor_cost), '0.00')

    def test_only_superuser_can_open_employee_management(self):
        self.client.force_login(self.master)
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_employee_with_hashed_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('employee_add'), {
            'username': 'newworker', 'email': 'worker@example.com',
            'password1': 'VeryStrongPass123!', 'password2': 'VeryStrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        employee = User.objects.get(username='newworker')
        self.assertTrue(employee.is_staff)
        self.assertTrue(employee.check_password('VeryStrongPass123!'))

    def test_part_usage_cannot_exceed_stock(self):
        part = StockPart.objects.create(
            name='Матрица', category='Экраны', quantity=1, min_quantity=0, price='3000.00'
        )
        self.client.force_login(self.master)
        response = self.client.post(
            reverse('repair_detail', args=[self.repair.pk]),
            {'action': 'add_part', 'part': part.pk, 'quantity': 2}
        )
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.quantity, 1)
        self.assertFalse(RepairPartUsage.objects.filter(repair=self.repair).exists())
