"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import utc

from django.core.management import call_command
import haystack
from haystack.query import SearchQuerySet

from utils.variables import MESSAGES
from base.models import UserProfile, ProfileRequest
from threads.models import Thread, Message
from managers.models import Manager, Announcement, RequestType, Request
from events.models import Event

class TestLogin(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="u", password="pwd")
        self.iu = User.objects.create_user(username="iu", password="pwd")

        self.iu.is_active = False
        self.iu.save()

    def test_user_profile_created(self):
        ''' Test that the user profile for a user is automatically created when a user is created. '''
        self.assertEqual(1, UserProfile.objects.filter(user=self.u).count())
        self.assertEqual(self.u, UserProfile.objects.get(user=self.u).user)

    def test_login(self):
        self.assertTrue(self.client.login(username="u", password="pwd"))
        self.assertEqual(None, self.client.logout())

        response = self.client.post("/login/", {
                "username_or_email": self.u.username,
                "password": "pwd",
                }, follow=True)
        self.assertRedirects(response, "/")

        response = self.client.get("/logout/", follow=True)
        self.assertRedirects(response, reverse('external'))

    def test_bad_login(self):
        self.assertFalse(self.client.login(username=self.iu.username, password="bad pwd"))
        self.assertFalse(self.client.login(username="baduser", password="pwd"))

        response = self.client.post("/login/", {
                "username_or_email": self.u.username,
                "password": "bad pwd",
                })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, MESSAGES["INVALID_LOGIN"])

        response = self.client.post("/login/", {
                "username_or_email": "baduser",
                "password": "pwd",
                })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, MESSAGES["INVALID_LOGIN"])

    def test_inactive_login(self):
        self.assertFalse(self.client.login(username=self.iu.username, password="pwd"))

        response = self.client.post("/login/", {
                "username_or_email": self.iu.username,
                "password": "pwd",
                })
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your account is not active. Please contact the site administrator to activate your account.")

        response = self.client.get("/", follow=True)
        self.assertRedirects(response, reverse('external'))

    def test_homepage(self):
        response = self.client.get("/", follow=True)
        self.assertRedirects(response, reverse('external'))
        self.client.login(username="u", password="pwd")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        response = self.client.get("/", follow=True)
        self.assertRedirects(response, reverse('external'))

class TestHomepage(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="u", password="pwd")

        self.profile = UserProfile.objects.get(user=self.u)

        self.manager = Manager(title="Super Manager", url_title="super")
        self.manager.incumbent = self.profile
        self.manager.save()

        self.rt = RequestType(name="Super", url_name="super", enabled=True)
        self.rt.save()
        self.rt.managers = [self.manager]
        self.rt.save()

        self.req = Request(owner=self.profile, request_type=self.rt)
        self.req.save()

        now = datetime.utcnow().replace(tzinfo=utc)
        one_day = timedelta(days=1)
        self.ev = Event(owner=self.profile, title="Event Title Test",
                start_time=now, end_time=now + one_day)
        self.ev.save()

        self.announce = Announcement(
            manager=self.manager,
            incumbent=self.profile,
            body="Test Announcement Body",
            )
        self.announce.save()

        self.client.login(username="u", password="pwd")

    def test_homepage_view(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recent Threads")
        self.assertContains(response, "Recent Announcements")
        self.assertContains(response, "Week's Events")
        self.assertContains(response, self.ev.title)
        self.assertContains(response, "{0} Requests".format(self.rt.name))

    def test_homepage_no_requests(self):
        self.req.delete()
        response = self.client.get("/")
        self.assertNotContains(response, "{0} Requests".format(self.rt.name))

    def test_homepage_requests_filled(self):
        self.req.filled = True
        self.req.save()
        response = self.client.get("/")
        self.assertNotContains(response, "{0} Requests".format(self.rt.name))

    def test_thread_post(self):
        response = self.client.post("/", {
                "submit_thread_form": "",
                "subject": "Thread Subject Test",
                "body": "Thread Body Text Test",
                 }, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, "Thread Subject Test")

        thread = Thread.objects.get(subject="Thread Subject Test")
        self.assertEqual(thread.owner, self.profile)

    def test_announcment_post(self):
        response = self.client.post("/", {
                "post_announcement": "",
                "manager": "1",
                "body": "Announcement Body Text Test",
                }, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, "Announcement Body Text Test")

        announcement = Announcement.objects.get(body="Announcement Body Text Test")
        self.assertEqual(announcement.incumbent, self.profile)

    def test_rsvp_post(self):
        response = self.client.post("/", {
                "rsvp": "",
                "event_pk": "{0}".format(self.ev.pk),
                }, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, 'Un-RSVP')

        response = self.client.post("/", {
                "rsvp": "",
                "event_pk": "{0}".format(self.ev.pk),
                }, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, 'RSVP')

    def test_response(self):
        response = self.client.post("/", {
            "add_response": "",
            "request_pk": self.req.pk,
            "body": "You betcha",
            }, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, "You betcha")
        self.assertNotContains(response, MESSAGES['REQ_CLOSED'])
        self.assertNotContains(response, MESSAGES['REQ_FILLED'])

    def test_response_closed(self):
        response = self.client.post("/", {
            "add_response": "",
            "request_pk": self.req.pk,
            "body": "You betcha",
            "mark_closed": "on",
            }, follow=True)
        self.assertRedirects(response, "/")
        # We shouldn't see the request body on the homepage any more when it is
        # filled
        self.assertNotContains(response, "You betcha")
        self.assertContains(response, MESSAGES['REQ_CLOSED'])
        self.assertNotContains(response, MESSAGES['REQ_FILLED'])

    def test_response_filled(self):
        response = self.client.post("/", {
            "add_response": "",
            "request_pk": self.req.pk,
            "body": "You betcha",
            "mark_filled": "on",
            }, follow=True)
        self.assertRedirects(response, "/")
        # We shouldn't see the request body on the homepage any more when it is
        # filled
        self.assertNotContains(response, "You betcha")
        self.assertNotContains(response, MESSAGES['REQ_CLOSED'])
        self.assertContains(response, MESSAGES['REQ_FILLED'])

    def test_unpin(self):
        self.announce.pinned = True
        self.announce.save()
        response = self.client.post("/", {
            "unpin": "",
            "announcement_pk": self.announce.pk,
            }, follow=True)
        self.assertRedirects(response, "/")
        self.assertEqual(Announcement.objects.get(pk=self.announce.pk).pinned,
                         False)

    def test_upvote(self):
        # Upvote
        response = self.client.post("/", {
            "upvote": "",
            "request_pk": self.req.pk,
            }, follow=True)
        self.assertRedirects(response, "/")
        self.assertIn(self.profile,
                      Request.objects.get(pk=self.req.pk).upvotes.all())

        # Remove upvote
        response = self.client.post("/", {
            "upvote": "",
            "request_pk": self.req.pk,
            }, follow=True)
        self.assertRedirects(response, "/")
        self.assertNotIn(self.profile,
                         Request.objects.get(pk=self.req.pk).upvotes.all())

    def test_bad_page(self):
        response = self.client.get("/bad_page/")
        self.assertEqual(response.status_code, 404)

        self.client.logout()

        response = self.client.get("/bad_page/")
        self.assertEqual(response.status_code, 404)

class TestRequestProfile(TestCase):
    def test_request_profile(self):
        response = self.client.post("/request_profile/", {
                "username": "request",
                "first_name": "first",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd",
                }, follow=True)
        self.assertRedirects(response, reverse("external"))
        self.assertEqual(1, ProfileRequest.objects.filter(username="request").count())

    def test_bad_username(self):
        usernames = [
            "user&name",
            "user.name",
            "user,name",
            "user>name",
            "user<name",
            "user^name",
            "user%name",
            "user:name",
            "user+name",
            "\"username",
            "~username",
            "\'username",
            ]

        for username in usernames:
            response = self.client.post("/request_profile/", {
                    "username": username,
                    "first_name": "first",
                    "last_name": "last",
                    "email": "request@email.com",
                    "affiliation_with_the_house": UserProfile.RESIDENT,
                    "password": "pwd",
                    "confirm_password": "pwd",
                    })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, MESSAGES["INVALID_USERNAME"])
            self.assertEqual(0, ProfileRequest.objects.filter(username=username).count())

    def test_good_username(self):
        usernames = [
            "u",
            "U",
            "1",
            "_",
            "____________________",
            "aA_1",
            "zZ_9",
            "9_Fg",
            ]

        for username in usernames:
            response = self.client.post("/request_profile/", {
                    "username": username,
                    "first_name": "first",
                    "last_name": "last",
                    "email": "request@email.com",
                    "affiliation_with_the_house": UserProfile.RESIDENT,
                    "password": "pwd",
                    "confirm_password": "pwd",
                    }, follow=True)
            self.assertRedirects(response, reverse("external"))
            self.assertEqual(1, ProfileRequest.objects.filter(username=username).count())
            ProfileRequest.objects.get(username=username).delete()

    def test_duplicate_user(self):
        u = User.objects.create_user(username="request")

        response = self.client.post("/request_profile/", {
                "username": u.username,
                "first_name": "first",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd",
                }, follow=True)
        self.assertContains(
            response, MESSAGES["USERNAME_TAKEN"].format(username=u.username)
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, ProfileRequest.objects.filter(username="request").count())

    def test_duplicate_request(self):
        pr = ProfileRequest(
            username="request",
            first_name="Tester",
            last_name="Tested",
            )
        pr.save()

        response = self.client.post("/request_profile/", {
                "username": "request2",
                "first_name": pr.first_name,
                "last_name": pr.last_name,
                "email": "request2@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd",
                }, follow=True)
        self.assertContains(
            response,
            MESSAGES["PROFILE_TAKEN"].format(first_name=pr.first_name,
                                             last_name=pr.last_name),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, ProfileRequest.objects.filter(username="request2").count())

    def test_bad_profile_requests(self):
        response = self.client.post("/request_profile/", {
                "username": "request",
                "first_name": "first",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd2",
                }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords don&#39;t match.")
        self.assertEqual(0, ProfileRequest.objects.filter(username="request").count())

        response = self.client.post("/request_profile/", {
                "username": "request",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd2",
                }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertEqual(0, ProfileRequest.objects.filter(username="request").count())

        response = self.client.post("/request_profile/", {
                "username": "*******", # hunter2
                "first_name": "first",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": UserProfile.RESIDENT,
                "password": "pwd",
                "confirm_password": "pwd2",
                }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, MESSAGES["INVALID_USERNAME"])
        self.assertEqual(0, ProfileRequest.objects.filter(username="request").count())

        response = self.client.post("/request_profile/", {
                "username": "request",
                "first_name": "first",
                "last_name": "last",
                "email": "request@email.com",
                "affiliation_with_the_house": "123",
                "password": "pwd",
                "confirm_password": "pwd",
                }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Select a valid choice. 123 is not one of the available choices.",
            )
        self.assertEqual(0, ProfileRequest.objects.filter(username="request").count())

class TestUtilities(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="u", password="pwd")
        self.su = User.objects.create_user(username="su", password="pwd")
        self.su.is_staff, self.su.is_superuser = True, True
        self.su.save()

    def test_site_map(self):
        response = self.client.get("/site_map/")
        self.assertEqual(response.status_code, 200)

        self.client.login(username="u", password="pwd")
        response = self.client.get("/site_map/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.client.login(username="su", password="pwd")
        response = self.client.get("/site_map/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_help_page(self):
        response = self.client.get("/help/")
        self.assertEqual(response.status_code, 200)

        self.client.login(username="u", password="pwd")
        response = self.client.get("/help/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.client.login(username="su", password="pwd")
        response = self.client.get("/help/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()

class TestSocialRequest(TestCase):
    def setUp(self):
        self.su = User.objects.create_user(username="su", password="pwd")
        self.su.is_staff, self.su.is_superuser = True, True
        self.su.save()

        self.pr = ProfileRequest(username="pr", email="pr@email.com",
                     affiliation=UserProfile.RESIDENT,
                     provider="github", uid="1234567890")
        self.pr.save()

        self.client.login(username="su", password="pwd")

    def test_profile_request_view(self):
        response = self.client.get("/custom_admin/profile_requests/{0}/"
                       .format(self.pr.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pr.email)

    def test_approve_profile_request(self):
        response = self.client.post("/custom_admin/profile_requests/{0}/"
                                    .format(self.pr.pk), {
                "username": self.pr.username,
                "first_name": "first",
                "last_name": "last",
                "email": self.pr.email,
                "phone_number": "",
                "status": self.pr.affiliation,
                "current_room": "",
                "former_rooms": "",
                "former_houses": "",
                "is_active": "on",
                "add_user": "",
                }, follow=True)

        self.assertRedirects(response, "/custom_admin/profile_requests/")
        self.assertContains(
            response,
            "User {0} was successfully added".format(self.pr.username),
            )

    def test_settings(self):
        for lib in settings.SOCIAL_AUTH_PIPELINE:
            module, func = lib.rsplit(".", 1)
            self.assertNotEqual(None, __import__(module, fromlist=[func]))
        self.assertIn("social.pipeline.social_auth.social_details",
                      settings.SOCIAL_AUTH_PIPELINE)
        self.assertIn("social.pipeline.social_auth.social_uid",
                      settings.SOCIAL_AUTH_PIPELINE)
        self.assertIn("social.pipeline.social_auth.auth_allowed",
                      settings.SOCIAL_AUTH_PIPELINE)
        self.assertIn("social.pipeline.social_auth.social_user",
                      settings.SOCIAL_AUTH_PIPELINE)
        self.assertIn("social.pipeline.user.get_username",
                      settings.SOCIAL_AUTH_PIPELINE)
        self.assertIn("base.pipeline.request_user",
                      settings.SOCIAL_AUTH_PIPELINE)

class TestProfileRequestAdmin(TestCase):
    def setUp(self):
        self.su = User.objects.create_user(username="su", password="pwd")

        self.su.is_staff, self.su.is_superuser = True, True
        self.su.save()

        self.pr = ProfileRequest(username="pr", email="pr@email.com",
                     first_name="Test First Name",
                     last_name="Test Last Name",
                     affiliation=UserProfile.RESIDENT)
        self.pr.save()

        self.client.login(username="su", password="pwd")

    def test_view(self):
        response = self.client.get("/custom_admin/profile_requests/{0}/"
                       .format(self.pr.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pr.email)

    def test_approve(self):
        response = self.client.post("/custom_admin/profile_requests/{0}/"
                                    .format(self.pr.pk), {
                "username": self.pr.username,
                "first_name": self.pr.first_name,
                "last_name": self.pr.last_name,
                "email": self.pr.email,
                "phone_number": "",
                "status": self.pr.affiliation,
                "current_room": "",
                "former_rooms": "",
                "former_houses": "",
                "is_active": "on",
                "add_user": "",
                }, follow=True)

        self.assertRedirects(response, "/custom_admin/profile_requests/")
        self.assertContains(
            response,
            "User {0} was successfully added".format(self.pr.username),
            )

        u = User.objects.get(username=self.pr.username)
        self.assertEqual(u.email, self.pr.email)

    def test_missing(self):
        response = self.client.post("/custom_admin/profile_requests/{0}/"
                                    .format(self.pr.pk + 1), {
                "username": self.pr.username,
                "first_name": self.pr.first_name,
                "last_name": self.pr.last_name,
                "email": self.pr.email,
                "phone_number": "",
                "status": self.pr.affiliation,
                "current_room": "",
                "former_rooms": "",
                "former_houses": "",
                "is_active": "on",
                "add_user": "",
                })
        self.assertEqual(response.status_code, 404)

    def test_delete(self):
        response = self.client.post("/custom_admin/profile_requests/{0}/"
                                    .format(self.pr.pk), {
                "delete_request": "",
                }, follow=True)
        self.assertRedirects(response, reverse('manage_profile_requests'))
        self.assertContains(
            response,
            MESSAGES['PREQ_DEL'].format(first_name=self.pr.first_name,
                                        last_name=self.pr.last_name,
                                        username=self.pr.username),
            )


class TestProfilePages(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="u", email="u@email.com", password="pwd")
        self.ou = User.objects.create_user(username="ou", email="ou@email.com")

        self.profile = UserProfile.objects.get(user=self.u)
        self.profile.current_room = "Test Current Room"
        self.profile.former_rooms = "Test Former Room, Test Formerer Room"
        self.profile.former_houses = "Test House, Test Houser, Test Housest"
        self.profile.phone_number = "(111) 111-1111"
        self.profile.email_visible = False
        self.profile.phone_visible = False
        self.profile.status = UserProfile.RESIDENT
        self.profile.save()

        self.oprofile = UserProfile.objects.get(user=self.ou)
        self.oprofile.current_room = "Other Test Current Room"
        self.oprofile.former_rooms = "Other Test Former Room, Test Formerer Room"
        self.oprofile.former_houses = "Other Test House, Test Houser, Test Housest"
        self.oprofile.phone_number = "(222) 222-2222"
        self.oprofile.email_visible = False
        self.oprofile.phone_visible = False
        self.oprofile.status = UserProfile.RESIDENT
        self.oprofile.save()

        self.client.login(username="u", password="pwd")

    def test_profile_page(self):
        response = self.client.get("/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update Your Profile")
        self.assertContains(response, self.u.email)
        self.assertContains(response, self.profile.current_room)
        self.assertContains(response, self.profile.former_rooms)
        self.assertContains(response, self.profile.former_houses)
        self.assertContains(response, self.profile.phone_number)

        response = self.client.get("/profile/{0}/".format(self.u.username),
                       follow=True)
        self.assertRedirects(response, "/profile/")

    def test_other_profile_page(self):
        response = self.client.get("/profile/{0}/".format(self.ou.username))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.ou.email)
        self.assertContains(
            response,
            "{0} {1}".format(self.ou.first_name, self.ou.last_name),
            )
        self.assertContains(response, UserProfile.STATUS_CHOICES[0][1])
        self.assertContains(response, self.oprofile.current_room)
        self.assertContains(response, self.oprofile.former_rooms)
        self.assertContains(response, self.oprofile.former_houses)
        self.assertNotContains(response, self.oprofile.phone_number)
        self.assertContains(response, "Threads Started")
        self.assertContains(response, "Requests Posted")

    def test_change_password(self):
        url = "/profile/"
        response = self.client.post(url, {
            "submit_password_form": "",
            "old_password": "pwd",
            "new_password1": "Jenkins",
            "new_password2": "Jenkins",
            }, follow=True)

        self.assertRedirects(response, url)
        self.assertContains(response, "Your password was successfully changed.")
        self.client.logout()
        self.assertEqual(False, self.client.login(username="u", password="pwd"))
        self.assertEqual(True, self.client.login(username="u", password="Jenkins"))

    def test_confirm_password(self):
        url = "/profile/"
        response = self.client.post(url, {
            "submit_password_form": "",
            "old_password": "pwd",
            "new_password1": "Jenkins",
            "new_password2": "Jeknins",
            })

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response, MESSAGES['USER_PW_CHANGED'].format(username=self.u.username))
        self.assertContains(
            response, "The two password fields didn't match.".replace("'", "&#39;")
            )
        self.client.logout()
        self.assertEqual(False, self.client.login(username="u", password="Jenkins"))
        self.assertEqual(True, self.client.login(username="u", password="pwd"))

    def test_visible(self):
        self.oprofile.email_visible = True
        self.oprofile.phone_visible = True
        self.oprofile.save()

        response = self.client.get("/profile/{0}/".format(self.ou.username))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ou.email)
        self.assertContains(response, self.oprofile.phone_number)

    def test_bad_profile(self):
        response = self.client.get("/profile/404/")
        self.assertEqual(response.status_code, 404)

class TestModifyUser(TestCase):
    def setUp(self):
        self.su = User.objects.create_user(username="su", password="pwd")
        self.u = User.objects.create_user(username="u", password="pwd")
        self.ou = User.objects.create_user(
            username="ou", email="ou@email.com",
            first_name="Test First", last_name="Test Last",
            )

        self.su.is_staff, self.su.is_superuser = True, True
        self.su.save()

        self.profile = UserProfile.objects.get(user=self.ou)
        self.profile.phone_number = "(222) 222-2222"
        self.profile.save()

    def test_set_visible(self):
        self.client.login(username="u", password="pwd")

        response = self.client.get("/profile/{0}/".format(self.ou.username))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.ou.email)
        self.assertNotContains(response, self.profile.phone_number)

        self.client.logout()

        self.client.login(username="su", password="pwd")

        url = "/custom_admin/modify_user/{0}/" .format(self.ou.username)
        response = self.client.post(url, {
                "email_visible_to_others": "on",
                "phone_visible_to_others": "on",
                "email": self.ou.email,
                "phone_number": self.profile.phone_number,
                "first_name": self.ou.first_name,
                "last_name": self.ou.last_name,
                "status": self.profile.status,
                "update_user_profile": "",
                }, follow=True)
        self.assertRedirects(response, url)
        self.assertContains(
            response,
            MESSAGES['USER_PROFILE_SAVED'].format(username=self.ou.username),
            )

        self.client.logout()

        self.client.login(username="u", password="pwd")

        response = self.client.get("/profile/{0}/".format(self.ou.username))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ou.email)
        self.assertContains(response, self.profile.phone_number)

    def test_set_profile_status(self):
        """
        Test modifying profiles to have different user statuses (Resident, Boarder,
        Alumni).
        """
        url = "/custom_admin/modify_user/{0}/".format(self.ou.username)

        for status, title in UserProfile.STATUS_CHOICES:
            self.client.login(username="su", password="pwd")

            response = self.client.post(url, {
                    "email_visible_to_others": "on",
                    "phone_visible_to_others": "on",
                    "email": self.ou.email,
                    "phone_number": self.profile.phone_number,
                    "first_name": self.ou.first_name,
                    "last_name": self.ou.last_name,
                    "status": status,
                    "update_user_profile": "",
                    }, follow=True)
            self.assertRedirects(response, url)
            self.assertContains(
                response,
                MESSAGES['USER_PROFILE_SAVED'].format(username=self.ou.username),
                )

            self.client.logout()

            self.client.login(username="u", password="pwd")

            response = self.client.get("/profile/{0}/".format(self.ou.username))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, title)

            self.client.logout()

    def test_change_user_password(self):
        self.client.login(username="su", password="pwd")

        url = "/custom_admin/modify_user/{0}/".format(self.u.username)
        response = self.client.post(url, {
            "change_user_password": "",
            "password1": "Leeroy",
            "password2": "Leeroy",
            }, follow=True)

        self.assertRedirects(response, url)
        self.assertContains(response,
                            MESSAGES['USER_PW_CHANGED'].format(username=self.u.username))
        self.client.logout()
        self.assertEqual(False, self.client.login(username="u", password="pwd"))
        self.assertEqual(True, self.client.login(username="u", password="Leeroy"))

    def test_confirm_user_password(self):
        self.client.login(username="su", password="pwd")

        url = "/custom_admin/modify_user/{0}/".format(self.u.username)
        response = self.client.post(url, {
            "change_user_password": "",
            "password1": "Leeroy",
            "password2": "Lereoy",
            })

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response, MESSAGES['USER_PW_CHANGED'].format(username=self.u.username))
        self.assertContains(
            response, "The two password fields didn't match.".replace("'", "&#39;")
            )
        self.client.logout()
        self.assertEqual(False, self.client.login(username="u", password="Leeroy"))
        self.assertEqual(True, self.client.login(username="u", password="pwd"))

class TestAdminFunctions(TestCase):
    def setUp(self):
        self.su = User.objects.create_user(username="su", password="pwd")
        self.u = User.objects.create_user(username="u", password="pwd")

        self.su.is_staff, self.su.is_superuser = True, True
        self.su.save()

        self.client.login(username="su", password="pwd")

    def test_add_user(self):
        response = self.client.post("/custom_admin/add_user/", {
                "username": "nu",
                "first_name": "First",
                "last_name": "Last",
                "email": "nu@email.com",
                "phone_number": "(222) 222-2222",
                "user_password": "newpwd",
                "confirm_password": "newpwd",
                "is_active": "true",
                "status": UserProfile.RESIDENT,
                 }, follow=True)
        self.assertRedirects(response, "/custom_admin/add_user/")
        self.assertContains(
            response,
            MESSAGES['USER_ADDED'].format(username="nu"),
            )

        self.assertEqual(1, User.objects.filter(username="nu").count())

        response = self.client.get("/profile/{0}/".format("nu"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "nu@email.com")
        self.assertNotContains(response, "(222) 222-2222")

        self.client.logout()

        self.assertFalse(self.client.login(username="nu", password="pwd"))
        self.assertTrue(self.client.login(username="nu", password="newpwd"))
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        User.objects.get(username="nu").delete()
        self.assertFalse(self.client.login(username="nu", password="newpwd"))

    def test_add_visible(self):
        response = self.client.post("/custom_admin/add_user/", {
                "username": "nu",
                "first_name": "First",
                "last_name": "Last",
                "email": "nu@email.com",
                "phone_number": "(222) 222-2222",
                "user_password": "newpwd",
                "confirm_password": "newpwd",
                "is_active": "true",
                "email_visible_to_others": "on",
                "phone_visible_to_others": "on",
                "status": UserProfile.RESIDENT,
                 }, follow=True)
        self.assertRedirects(response, "/custom_admin/add_user/")
        self.assertContains(
            response,
            MESSAGES['USER_ADDED'].format(username="nu"),
            )
        self.assertEqual(1, User.objects.filter(username="nu").count())

        response = self.client.get("/profile/{0}/".format("nu"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nu@email.com")
        self.assertContains(response, "(222) 222-2222")

    def test_set_add_status(self):
        """
        Test adding users with different statuses (Resident, Boarder, Alumni).
        """
        url = "/custom_admin/add_user/"

        for status, title in UserProfile.STATUS_CHOICES:
            response = self.client.post(url, {
                    "username": "nu",
                    "first_name": "First",
                    "last_name": "Last",
                    "email": "nu@email.com",
                    "phone_number": "(222) 222-2222",
                    "user_password": "newpwd",
                    "confirm_password": "newpwd",
                    "is_active": "true",
                    "status": status,
                    }, follow=True)
            self.assertRedirects(response, url)
            self.assertContains(
                response,
                MESSAGES['USER_ADDED'].format(username="nu"),
                )

            response = self.client.get("/profile/{0}/".format("nu"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, title)

            User.objects.get(username="nu").delete()

    def test_delete_user(self):
        response = self.client.post("/custom_admin/modify_user/{0}/".format(self.u.username), {
                "username": self.u.username,
                "password": "pwd",
                "delete_user": "",
                 }, follow=True)
        self.assertRedirects(response, "/custom_admin/manage_users/")
        self.assertContains(
            response,
            MESSAGES['USER_DELETED'].format(username="u"),
            )
        self.assertEqual(0, User.objects.filter(username="u").count())

        response = self.client.get("/profile/{0}/".format("u"))
        self.assertEqual(response.status_code, 404)

        self.client.logout()

        self.assertFalse(self.client.login(username="u", password="pwd"))

    def test_deleted_content(self):
        profile = UserProfile.objects.get(user=self.u)

        self.client.logout()
        self.assertTrue(self.client.login(username="u", password="pwd"))

        response = self.client.post("/threads/", {
                "submit_thread_form": "",
                "subject": "Test Subject",
                "body": "Test Body",
                }, follow=True)
        self.assertRedirects(response, "/threads/")

        self.assertEqual(1, Thread.objects.filter(owner=profile).count())
        self.assertEqual(1, Message.objects.filter(owner=profile).count())

        self.client.logout()
        self.assertTrue(self.client.login(username="su", password="pwd"))

        response = self.client.post("/custom_admin/modify_user/{0}/"
                                    .format(self.u.username), {
                "username": self.u.username,
                "password": "pwd",
                "delete_user": "",
                 }, follow=True)
        self.assertRedirects(response, "/custom_admin/manage_users/")
        self.assertContains(
            response,
            MESSAGES['USER_DELETED'].format(username="u"),
            )
        self.assertEqual(0, User.objects.filter(username="u").count())

        self.assertEqual(0, Thread.objects.filter(owner=profile).count())
        self.assertEqual(0, Message.objects.filter(owner=profile).count())

class TestMemberDirectory(TestCase):
    def setUp(self):
        self.ru = User.objects.create_user(username="ru", password="pwd",
                           email="ru@email.com")
        self.bu = User.objects.create_user(username="bu", email="bu@email.com")
        self.au = User.objects.create_user(username="au", email="au@email.com")

        self.ruprofile = UserProfile.objects.get(user=self.ru)
        self.buprofile = UserProfile.objects.get(user=self.bu)
        self.auprofile = UserProfile.objects.get(user=self.au)

        self.ruprofile.phone_number = "(000) 000-0000"

        self.buprofile.status = UserProfile.BOARDER
        self.buprofile.phone_number = "(111) 111-1111"
        self.buprofile.email_visible = True

        self.auprofile.status = UserProfile.ALUMNUS
        self.auprofile.phone_number = "(222) 222-2222"
        self.auprofile.phone_visible = True

        self.ruprofile.save()
        self.buprofile.save()
        self.auprofile.save()

        self.client.login(username="ru", password="pwd")

    def test_member_directory_view(self):
        response = self.client.get("/member_directory/")

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, self.ru.email)
        self.assertContains(response, self.bu.email)
        self.assertNotContains(response, self.au.email)

        self.assertNotContains(response, self.ruprofile.phone_number)
        self.assertNotContains(response, self.buprofile.phone_number)
        self.assertContains(response, self.auprofile.phone_number)

        self.assertContains(response, self.ru.username)
        self.assertContains(response, self.bu.username)
        self.assertContains(response, self.au.username)

        self.assertContains(response, "Residents")
        self.assertContains(response, "Boarders")
        self.assertContains(response, "Alumni")

        self.assertNotContains(response, "pwd")

class TestSearch(TestCase):
    def setUp(self):
        for key, opts in haystack.connections.connections_info.items():
            haystack.connections.reload(key)
            call_command('clear_index', interactive=False, verbosity=0)

        self.u = User.objects.create_user(username="u", password="pwd")

        self.u.first_name = "FirstName"
        self.u.last_name = "LastName"
        self.u.save()

        self.profile = UserProfile.objects.get(user=self.u)
        self.profile.phone_number = "(111) 111-1111"
        self.profile.save()

        self.sqs = SearchQuerySet()

        self.client.login(username="u", password="pwd")

    def test_search_view(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search")

    def test_model_backend(self):
        self.assertEqual(UserProfile.objects.count(),
                 self.sqs.models(UserProfile).count())
        self.assertEqual(self.profile,
                 self.sqs.facet(self.u.first_name)[0].object)
        self.assertEqual(self.profile,
                 self.sqs.facet(self.u.last_name)[0].object)
        self.assertEqual(self.profile,
                 self.sqs.facet(self.profile.phone_number)[0].object)

    # def test_search_results(self):
    #     response = self.client.get("/search/?q={0}".format(self.u.username))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertNotContains(response, "No results found.")
    #     self.assertContains(response, self.u.first_name)
    #     self.assertContains(response, self.u.last_name)

    #     response = self.client.get("/search/?q={0}".format(self.u.last_name))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertNotContains(response, "No results found.")
    #     self.assertContains(response, self.u.first_name)
    #     self.assertContains(response, self.u.last_name)

    #     # Searching by phone number not enabled
    #     number = self.profile.phone_number.replace(" ", "+") \
    #       .replace("(", "%28").replace(")", "%29")
    #     response = self.client.get("/search/?q={0}".format(number))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, "No results found.")
