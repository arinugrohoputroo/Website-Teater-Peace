from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from apps.snacks.models import CommitteeMember, SnackClaim, SnackSession
from apps.snacks.services import process_qr_snack_scan


class SeedCommitteeTests(TestCase):
    def test_seed_creates_31_with_tokens(self):
        call_command('seed_committee')
        self.assertEqual(CommitteeMember.objects.count(), 31)
        self.assertEqual(CommitteeMember.objects.exclude(qr_token='').count(), 31)
        self.assertEqual(CommitteeMember.objects.values('qr_token').distinct().count(), 31)
        self.assertTrue(all(m.member_code.startswith('P') for m in CommitteeMember.objects.all()))

    def test_seed_idempotent(self):
        call_command('seed_committee')
        tokens = list(CommitteeMember.objects.order_by('id').values_list('qr_token', flat=True))
        call_command('seed_committee')
        self.assertEqual(CommitteeMember.objects.count(), 31)
        self.assertEqual(
            list(CommitteeMember.objects.order_by('id').values_list('qr_token', flat=True)),
            tokens,
        )


class QRSnackClaimTests(TestCase):
    def setUp(self):
        call_command('seed_committee')
        self.admin = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            name='Ari Nugroho Putro',
            password='password123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        self.staff = get_user_model().objects.create_user(
            username='staff',
            email='staff@example.com',
            name='Staff User',
            password='password123',
            role='STAFF',
            is_staff=True,
        )
        self.session1 = SnackSession.objects.create(
            name='Session 1', date=date.today(),
            start_time=time(10, 0), end_time=time(12, 0), active=True,
        )
        self.session2 = SnackSession.objects.create(
            name='Session 2', date=date.today(),
            start_time=time(14, 0), end_time=time(16, 0), active=True,
        )
        self.member = CommitteeMember.objects.get(name='Rohmad Pujiono, S.Psi., M.Si')

    def test_success_claim(self):
        result = process_qr_snack_scan(
            qr_token=self.member.qr_token,
            session=self.session1,
            operator=self.admin,
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'approved')
        claim = SnackClaim.objects.get(committee_member=self.member, session=self.session1)
        self.assertEqual(claim.detection_method, 'QR')
        self.assertEqual(claim.operator, self.admin)
        self.assertEqual(claim.qr_token_used, self.member.qr_token)

    def test_duplicate_same_session(self):
        process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session1, operator=self.admin)
        result = process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session1, operator=self.admin)
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'already_claimed')
        self.assertEqual(SnackClaim.objects.filter(committee_member=self.member, session=self.session1).count(), 1)

    def test_different_session_ok(self):
        process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session1, operator=self.admin)
        result = process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session2, operator=self.admin)
        self.assertTrue(result['success'])
        self.assertEqual(SnackClaim.objects.filter(committee_member=self.member).count(), 2)

    def test_unknown_qr(self):
        result = process_qr_snack_scan(qr_token='TP26-XXXXYYYY', session=self.session1, operator=self.admin)
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'unknown')
        self.assertFalse(SnackClaim.objects.exists())

    def test_inactive_member(self):
        self.member.active = False
        self.member.save(update_fields=['active'])
        result = process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session1, operator=self.admin)
        self.assertEqual(result['status'], 'inactive')
        self.assertFalse(SnackClaim.objects.exists())

    def test_regenerate_invalidates_old(self):
        old = self.member.qr_token
        self.member.regenerate_qr_token()
        result_old = process_qr_snack_scan(qr_token=old, session=self.session1, operator=self.admin)
        self.assertEqual(result_old['status'], 'unknown')
        result_new = process_qr_snack_scan(qr_token=self.member.qr_token, session=self.session1, operator=self.admin)
        self.assertEqual(result_new['status'], 'approved')

    def test_qr_token_not_name(self):
        self.assertNotIn('Rohmad', self.member.qr_token)
        self.assertTrue(self.member.qr_token.startswith('TP26-'))


class ScannerAccessTests(TestCase):
    def setUp(self):
        call_command('seed_committee')
        self.admin = get_user_model().objects.create_user(
            username='admin2', email='admin2@example.com', name='Admin',
            password='password123', role='ADMIN', is_staff=True, is_superuser=True,
        )
        self.staff = get_user_model().objects.create_user(
            username='staff2', email='staff2@example.com', name='Staff',
            password='password123', role='STAFF', is_staff=True,
        )
        from apps.accounts.models import StaffPermission
        StaffPermission.objects.create(user=self.staff, module='snack')
        SnackSession.objects.create(
            name='Session 1', date=date.today(),
            start_time=time(10, 0), end_time=time(12, 0), active=True,
        )

    def test_admin_can_access_scanner(self):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(self.admin)
        response = client.get(reverse('snacks:scanner'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Snack Scanner')

    def test_staff_cannot_access_scanner(self):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(self.staff)
        response = client.get(reverse('snacks:scanner'))
        self.assertEqual(response.status_code, 403)

    def test_api_scan_success(self):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(self.admin)
        session = SnackSession.objects.first()
        member = CommitteeMember.objects.first()
        response = client.post(
            reverse('snacks:api_scan'),
            data='{"session_id": %d, "qr_token": "%s"}' % (session.pk, member.qr_token),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'approved')
        self.assertEqual(data['member']['id'], member.member_code)

    def test_committee_pages(self):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(self.admin)
        self.assertEqual(client.get(reverse('snacks:committee_list')).status_code, 200)
        self.assertEqual(client.get(reverse('snacks:committee_qr_list')).status_code, 200)
        self.assertEqual(client.get(reverse('snacks:committee_qr_print')).status_code, 200)
        member = CommitteeMember.objects.first()
        self.assertEqual(client.get(reverse('snacks:committee_detail', args=[member.pk])).status_code, 200)
        self.assertEqual(client.get(reverse('snacks:committee_qr_download', args=[member.pk])).status_code, 200)

    def test_committee_add(self):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(self.admin)
        before = CommitteeMember.objects.count()
        response = client.post(reverse('snacks:committee_add'), {'name': 'Panitia Baru Test'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CommitteeMember.objects.count(), before + 1)
        member = CommitteeMember.objects.get(name='Panitia Baru Test')
        self.assertTrue(member.member_code.startswith('P'))
        self.assertTrue(member.qr_token)
