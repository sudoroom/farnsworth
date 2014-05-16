"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.core.urlresolvers import reverse
from utils.variables import ANONYMOUS_USERNAME, MESSAGES
from base.models import UserProfile, ProfileRequest
from managers.models import Manager, RequestType, Request, Response

class TestPermissions(TestCase):
	def setUp(self):
		self.u = User.objects.create_user(username="u", password="pwd")
		self.st = User.objects.create_user(username="st", password="pwd")
		self.pu = User.objects.create_user(username="pu", password="pwd")
		self.su = User.objects.create_user(username="su", password="pwd")
		self.np = User.objects.create_user(username="np", password="pwd")

		self.st.is_staff = True
		self.su.is_staff, self.su.is_superuser = True, True

		self.u.save()
		self.st.save()
		self.pu.save()
		self.su.save()
		self.np.save()

		president = Manager(title="House President", url_title="president",
				    president=True)
		president.incumbent = UserProfile.objects.get(user=self.pu)
		president.save()

		food = RequestType(name="Food", url_name="food", enabled=True)
		food.save()
		food.managers = [president]
		food.save()

		self.request = Request(owner=UserProfile.objects.get(user=self.u),
				       body="request body", request_type=food)
		self.request.save()

		UserProfile.objects.get(user=self.np).delete()
		self.pr = ProfileRequest(username="pr", email="pr@email.com",
					 affiliation=UserProfile.STATUS_CHOICES[0][0])
		self.pr.save()

	def _admin_required(self, url, success_target=None):
		response = self.client.get(url)
		self.assertRedirects(response, "/login/")

		self.client.login(username="np", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/landing/")
		self.assertIn(MESSAGES["NO_PROFILE"], response.content)
		self.client.logout()

		self.client.login(username="u", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES["ADMINS_ONLY"], response.content)
		self.client.logout()

		self.client.login(username="st", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES["ADMINS_ONLY"], response.content)
		self.client.logout()

		self.client.login(username="su", password="pwd")
		response = self.client.get(url)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

	def _president_admin_required(self, url, success_target=None):
		response = self.client.get(url)
		self.assertRedirects(response, "/login/")

		self.client.login(username="np", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/landing/")
		self.assertIn(MESSAGES["NO_PROFILE"], response.content)
		self.client.logout()

		self.client.login(username="u", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES["PRESIDENTS_ONLY"], response.content)
		self.client.logout()

		self.client.login(username="st", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES["PRESIDENTS_ONLY"], response.content)
		self.client.logout()

		self.client.login(username="su", password="pwd")
		response = self.client.get(url)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

		self.client.login(username="pu", password="pwd")
		response = self.client.get(url)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

	def _profile_required(self, url, success_target=None):
		response = self.client.get(url)
		self.assertRedirects(response, "/login/")

		self.client.login(username="np", password="pwd")
		response = self.client.get(url, follow=True)
		self.assertRedirects(response, "/landing/")
		self.assertIn(MESSAGES["NO_PROFILE"], response.content)
		self.client.logout()

		self.client.login(username="u", password="pwd")
		response = self.client.get(url, follow=True)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

		self.client.login(username="st", password="pwd")
		response = self.client.get(url, follow=True)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

		self.client.login(username="su", password="pwd")
		response = self.client.get(url, follow=True)
		if success_target is None:
			self.assertEqual(response.status_code, 200)
		else:
			self.assertRedirects(response, success_target)
		self.client.logout()

	def test_admin_required(self):
		pages = [
			"profile_requests",
			"profile_requests/{0}".format(self.pr.pk),
			"manage_users",
			"modify_user/{0}".format(self.u.username),
			"add_user",
			"utilities",
			]
		for page in pages:
			self._admin_required("/custom_admin/" + page + "/")
		self._admin_required("/custom_admin/recount/",
				     success_target="/custom_admin/utilities/")
		self._admin_required("/custom_admin/anonymous_login/",
				     success_target="/")
		self._admin_required("/custom_admin/end_anonymous_session/",
				     success_target="/custom_admin/utilities/")

	def test_president_admin_required(self):
		pages = [
			"managers",
			"managers/president",
			"add_manager",
			"request_types",
			"request_types/food",
			"add_request_type",
			]
		for page in pages:
			self._president_admin_required("/custom_admin/" + page + "/")

	def test_profile_required(self):
		pages = [
			"manager_directory",
			"manager_directory/president",
			"profile/{0}/requests".format(self.u.username),
			"requests/food",
			"archives/all_requests",
			"requests/food/all",
			"my_requests",
			"request/{0}".format(self.request.pk),
			"archives/all_announcements",
			]
		for page in pages:
			self._profile_required("/" + page + "/")

class TestAnonymousUser(TestCase):
	def setUp(self):
		self.u = User.objects.create_user(username="u", password="pwd")
		self.su = User.objects.create_user(username="su", password="pwd")

		self.su.is_staff, self.su.is_superuser = True, True

		self.u.save()
		self.su.save()

		self.client.login(username="su", password="pwd")

	def test_anonymous_start(self):
		response = self.client.get("/")
		self.assertNotIn("Logged in as anonymous user Anonymous Coward",
				 response.content)

		response = self.client.get("/custom_admin/anonymous_login/", follow=True)
		self.assertRedirects(response, "/")
		self.assertIn("Logged in as anonymous user Anonymous Coward",
			      response.content)

	def test_anonymous_end(self):
		self.client.get("/custom_admin/anonymous_login/")
		self.client.login(username="su", password="pwd")

		response = self.client.get("/custom_admin/end_anonymous_session/",
					   follow=True)
		self.assertRedirects(response, "/custom_admin/utilities/")
		self.assertIn(MESSAGES["ANONYMOUS_SESSION_ENDED"], response.content)
		self.assertNotIn("Logged in as anonymous user Anonymous Coward",
				 response.content)

	def test_anonymous_profile(self):
		# Failing before anonymous user is first logged in
		response = self.client.get("/profile/{0}/".format(ANONYMOUS_USERNAME))
		self.assertEqual(response.status_code, 404)

		self.client.get("/custom_admin/anonymous_login/")

		response = self.client.get("/profile/{0}/".format(ANONYMOUS_USERNAME))
		self.assertEqual(response.status_code, 200)
		self.assertIn("Anonymous Coward", response.content)

		response = self.client.get("/profile/", follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES['SPINELESS'], response.content)

	def test_anonymous_edit_profile(self):
		# Failing before anonymous user is first logged in
		response = self.client.get("/custom_admin/modify_user/{0}/"
					   .format(ANONYMOUS_USERNAME))
		self.assertEqual(response.status_code, 404)

		self.client.get("/custom_admin/anonymous_login/")
		self.client.get("/logout/", follow=True)

		self.client.login(username="su", password="pwd")

		response = self.client.get("/custom_admin/modify_user/{0}/"
					   .format(ANONYMOUS_USERNAME))
		self.assertEqual(response.status_code, 200)
		self.assertIn("Anonymous", response.content)
		self.assertIn("Coward", response.content)
		self.assertIn(MESSAGES['ANONYMOUS_EDIT'], response.content)

	def test_anonymous_logout(self):
		self.client.get("/custom_admin/anonymous_login/")

		response = self.client.get("/logout/", follow=True)
		self.assertRedirects(response, "/")
		self.assertIn(MESSAGES['ANONYMOUS_DENIED'], response.content)

	def test_anonymous_user_login_logout(self):
		self.client.get("/custom_admin/anonymous_login/")

		# Need to be careful here, client.login and client.logout clear the
		# session cookies, causing this test to break
		response = self.client.post("/login/", {
				"username": "u",
				"password": "pwd",
				}, follow=True)

		self.assertRedirects(response, "/")
		self.assertNotIn("Logged in as anonymous user Anonymous Coward",
				 response.content)

		response = self.client.get("/logout/", follow=True)
		self.assertRedirects(response, "/")

		response = self.client.get("/")
		self.assertEqual(response.status_code, 200)
		self.assertIn("Logged in as anonymous user Anonymous Coward",
			      response.content)

class TestRequestPages(TestCase):
	def setUp(self):
		self.u = User.objects.create_user(username="u", password="pwd")
		self.pu = User.objects.create_user(username="pu", password="pwd")

		self.u.save()
		self.pu.save()

		president = Manager(title="House President", url_title="president",
				    president=True)
		president.incumbent = UserProfile.objects.get(user=self.pu)
		president.save()

		self.food = RequestType(name="Food", url_name="food", enabled=True)
		self.food.save()
		self.food.managers = [president]
		self.food.save()

		self.request = Request(owner=UserProfile.objects.get(user=self.u),
				       body="Request Body", request_type=self.food)
		self.request.save()

		self.response = Response(owner=UserProfile.objects.get(user=self.pu),
					 body="Response Body", request=self.request,
					 manager=True)
		self.response.save()

	def test_request_form(self):
		urls = [
			"/request/{0}/".format(self.request.pk),
			"/requests/{0}/".format(self.food.url_name),
			]

		self.client.login(username="u", password="pwd")
		for url in urls + ["/my_requests/"]:
			response = self.client.get(url)
			self.assertIn("Request Body", response.content)
			self.assertIn("Response Body", response.content)
			self.assertNotIn("mark_filled", response.content)
		self.client.logout()

		self.client.login(username="pu", password="pwd")
		for url in urls:
			response = self.client.get(url)
			self.assertIn("Request Body", response.content)
			self.assertIn("Response Body", response.content)
			self.assertIn("mark_filled", response.content)

		response = self.client.get("/my_requests/")
		self.assertNotIn("Request Body", response.content)
		self.assertNotIn("Response Body", response.content)
		self.assertNotIn("mark_filled", response.content)
