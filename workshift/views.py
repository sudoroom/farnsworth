
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from base.decorators import workshift_required
from base.models import UserProfile
from workshift.decorators import workshift_profile_required
from workshift.models import Semester, WorkshiftProfile

@profile_required
def workshift_view(request):
	"""
	Displays a table of the workshifts for the week, shift assignees,
	accumulated statistics (Down hours), reminders for any upcoming shifts, and
	links to sign off on shifts. Also links to the rest of the workshift pages.
	"""
	pass

@profile_required
def preferences_view(request, semester):
	"""

	"""
	page_name = "Workshift Preferences"
	profile = get_object_or_404(WorkshiftProfile, user=request.user,
								semester=semester)
	return render_to_response("workshift_preferences.html", {
		"page_name": page_name,
		"profile": profile,
	}, context_instance=RequestContext(request))

@workshift_required
def manage_preferences_view(request, semester):
	"""
	View all members' preferences. This view also includes forms to create an
	entire semester's worth of weekly workshifts.
	"""
	page_name = "Manage Member Preferences"
	profiles = WorkshiftProfile.objects.filter(semester=semester)
	return render_to_response("workshift_manage_preferences.html", {
		"page_name": page_name,
		"profiles": profiles,
	}, context_instance=RequestContext(request))

@workshift_required
def start_semester_view(request):
	"""
	Initiates a semester's worth of workshift, with the option to copy workshift
	types from the previous semester.
	"""
	pass

@workshift_required
def add_workshift_view(request):
	pass
