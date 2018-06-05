from ddt import ddt, unpack, data
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from accounts.forms import CreatePasswordForm, ChangePasswordForm, SocialForm

from accounts.models import Instructor, Profile
from psa.custom_django_storage import CustomCode

@ddt
class AccountSettingsTests(TestCase):
    def setUp(self):
        self.url = reverse('accounts:settings')
        self.user = User.objects.create_user(
            username='username',
            email='email@mail.com',
            password='123'
        )
        self.instructor = Instructor(user=self.user)
        self.instructor.save()
        self.client.login(username='username', password='123')

    def get_user(self):
        return User.objects.get(id=self.user.id)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('new_login')+'?next='+self.url)

    def test_get_account_settings_page(self):
        self.client.login(username='username', password='123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/settings.html')
        self.assertIn('user_form', response.context)
        self.assertIn('instructor_form', response.context)
        self.assertIn('password_form', response.context)
        self.assertIn('delete_account_form', response.context)
        self.assertIn('email_form', response.context)
        self.assertIn('person', response.context)

        self.assertEqual(response.context['user_form'].instance, self.user)
        self.assertEqual(response.context['email_form'].initial['email'], self.user.email)
        self.assertEqual(response.context['instructor_form'].instance, self.user.instructor)
        self.assertEqual(response.context['delete_account_form'].instance, self.user)
        self.assertEqual(response.context['person'], self.user)

    def test_post_valid_change_user_data(self):
        data = {'first_name': 'SomeUser', 'last_name': 'somesome', 'form_id': 'user_form'}
        response = self.client.post(self.url, data, follow=True)
        user = self.get_user()
        self.assertRedirects(response, self.url)
        self.assertEqual(user.first_name, 'SomeUser')
        self.assertEqual(user.last_name, 'somesome')

    def test_post_valid_institution(self):
        data = {'institution': 'SomeInstitute', 'user': self.user.id, 'form_id': 'instructor_form'}
        response = self.client.post(self.url, data, follow=True)
        instructor = Instructor.objects.get(user__id=self.user.id)
        self.assertRedirects(response, self.url)
        self.assertEqual(instructor.institution, 'SomeInstitute')

    def test_post_valid_password_create(self):
        # make user password UNUSABLE
        self.user.password = '!' + self.user.password
        self.user.save()
        response = self.client.get(self.url)
        self.assertEqual(type(response.context['password_form']), CreatePasswordForm)

        data = {'confirm_password': '1234', 'password': '1234', 'form_id': 'password_form'}
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)
        can_login = self.client.login(username='username', password='1234')
        self.assertTrue(can_login)

    def test_post_valid_password_change(self):
        response = self.client.get(self.url)
        self.assertEqual(type(response.context['password_form']), ChangePasswordForm)

        can_login = self.client.login(username='username', password='123')
        self.assertTrue(can_login)

        data = {
            'current_password': '123',
            'confirm_password': '1234',
            'password': '1234',
            'form_id': 'password_form'
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)
        can_login = self.client.login(username='username', password='1234')
        self.assertTrue(can_login)


    @unpack
    @data(
        {
            'data': {
                'current_password': '123123123',  # not correct current password
                'confirm_password': '1234',
                'password': '1234',
                'form_id': 'password_form'
            },
            'errors': {
                'current_password': u'Provided current password doesn\'t match your password',
            },
        },
        {
            'data': {
                'current_password': '123',  # not correct current password
                'confirm_password': '1234',
                'password': '12341',
                'form_id': 'password_form'
            },
            'errors': {
                'password': u'Should be equal to confirm password field.',
                'confirm_password': u'Should be equal to password field.',
            }
        }

    )
    def test_post_invalid_current_password_change(self, data, errors):
        response = self.client.get(self.url)
        self.assertEqual(type(response.context['password_form']), ChangePasswordForm)

        can_login = self.client.login(username='username', password='123')
        self.assertTrue(can_login)

        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        if errors:
            for field, error in errors.items():
                self.assertIn(
                    error,
                    response.context['password_form'].errors.get(field, [])
                )
        can_login = self.client.login(username='username', password='1234')
        self.assertFalse(can_login)

    def test_post_valid_email_change(self):
        data = {'email': 'mm@mail.com', 'form_id': 'email_form'}
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, reverse('ctms:email_sent'))
        cc = CustomCode.objects.all().last()
        self.assertEqual(cc.email, data['email'])
        self.assertEqual(cc.user_id, self.user.id)
        self.assertEqual(cc.verified, False)

        user = self.get_user()
        self.assertEqual(user.email, self.user.email)

        # if user is authenticated - redirect to /ct/
        response = self.client.get(
            "/complete/email/?verification_code={}".format(cc.code),
            follow=True
        )
        self.assertRedirects(response, reverse('ctms:create_course'), target_status_code=200)

    def test_delete_account_post_valid_data(self):
        data = {'confirm_delete_account': True, 'form_id': 'delete_account_form'}
        response = self.client.post(reverse('accounts:delete'), data)
        user = self.get_user()
        self.assertNotEqual(user.is_active, self.user.is_active)
        self.assertRedirects(response, reverse('accounts:deleted'))

    def test_delete_account_post_invalid_data(self):
        data = {'confirm_delete_account': False}
        response = self.client.post(reverse('accounts:delete'), data)
        user = self.get_user()
        # user not deleted
        self.assertEqual(user.is_active, self.user.is_active)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, 'accounts/settings.html')
        self.assertTrue(bool(response.context['delete_account_form'].errors))


class AnonymousUserAccountSettingsTests(TestCase):
    def setUp(self):
        self.username = 'anonymous'
        self.user_pw = '123'
        self.create_user()
        self.url = reverse('accounts:settings')
        self.client.login(username=self.username, password=self.user_pw)

    def create_user(self):
        self.user = User.objects.create_user(
            username=self.username,
            email='email@mail.com',
            password=self.user_pw
        )
        self.instructor = Instructor(user=self.user)
        self.instructor.save()

    def test_login_required(self):
        '''
        Checks that user with username anonymous will be redirected to login page
        '''
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('new_login')+'?next='+self.url)

    def test_login_usual_user(self):
        '''
        Checks that usual user will not be redirected to login page
        '''
        self.username = 'user123'
        self.create_user()
        self.client.login(username=self.username, password=self.user_pw)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class ProfileUpdateTests(TestCase):
    def setUp(self):
        self.url = reverse('accounts:profile_update')
        self.user = User.objects.create_user(
            username='username',
            email='email@mail.com',
            password='123'
        )
        self.user = self.get_user()
        self.client.login(username='username', password='123')

    def get_user(self):
        return User.objects.get(id=self.user.id)

    def test_get_profile_update_page_without_instructor(self):
        """Test when user has no instructor it will show social form page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], SocialForm)
        self.assertTemplateUsed(response, 'accounts/profile_edit.html')
        self.assertFalse(Instructor.objects.all())

    def test_post_social_form(self):
        """Test when user has no instructor it will show social form, after submit it - user will have instructor."""
        inst_name = 'Some Institute'
        response = self.client.post(self.url, {
            'institution': inst_name,
            'user': self.user.id
        }, follow=True)
        self.assertRedirects(response, reverse('ctms:create_course'))
        self.assertEqual(self.get_user().instructor.institution, inst_name)



