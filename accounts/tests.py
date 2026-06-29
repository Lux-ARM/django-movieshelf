from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class SignupTest(TestCase):
    """Tests de l'inscription"""

    def test_signup_get(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')

    def test_signup_post_valid(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Str0ngP@ssword!',
            'password2': 'Str0ngP@ssword!',
            'security_question': 'pet',
            'security_answer': 'Rex',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        # Verifier que le profil avec question secrete a ete cree
        user = User.objects.get(username='newuser')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.security_question, 'pet')

    def test_signup_post_password_mismatch(self):
        response = self.client.post(reverse('signup'), {
            'username': 'baduser',
            'email': 'bad@example.com',
            'password1': 'Str0ngP@ssword!',
            'password2': 'WrongPassword',
            'security_question': 'city',
            'security_answer': 'Paris',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())


class LoginLogoutTest(TestCase):
    """Tests de connexion / deconnexion"""

    def setUp(self):
        self.user = User.objects.create_user(username='loginuser', password='testpass123')

    def test_login_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_post_valid(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('accueil'))

    def test_login_post_invalid(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='loginuser', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('accueil'))


class ProfileViewTest(TestCase):
    """Tests de la page profil"""

    def setUp(self):
        self.user = User.objects.create_user(username='profileuser', password='testpass')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_authenticated(self):
        self.client.login(username='profileuser', password='testpass')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertContains(response, 'profileuser')
