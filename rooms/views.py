
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from base.decorators import profile_required, admin_required
from base.models import UserProfile
from rooms.models import Room
from rooms.forms import RoomForm, RoomForm

@profile_required
def list_rooms(request):
	rooms = Room.objects.all()
	residents = [UserProfile.objects.filter(current_room=i) for i in rooms]
	page_name = "Room List"
	can_add = request.user.is_superuser
	return render_to_response('list_rooms.html', {
		'page_name': page_name,
		'room_tuples': zip(rooms, residents),
		'can_add': can_add,
	}, context_instance=RequestContext(request))

@admin_required
def add_room(request):
	page_name = "Add Room"
	add_form = RoomForm(request.POST or None)

	if add_form.is_valid():
		add_form.save()
		return HttpResponseRedirect(reverse('rooms:list'))

	return render_to_response('add_room.html', {
		'page_name': page_name,
		'add_form': add_form,
	}, context_instance=RequestContext(request))

@profile_required
def view_room(request, room_title):
	room = get_object_or_404(Room, title=room_title)
	page_name = room_title
	if room.unofficial_name:
		page_name += " ({0})".format(room.unofficial_name)
	profile = UserProfile.objects.get(user=request.user)
	can_edit = (room == profile.current_room or request.user.is_superuser)
	residents = UserProfile.objects.filter(current_room=room)

	return render_to_response('view_room.html', {
		'page_name': page_name,
		'can_edit': can_edit,
		'room': room,
		'residents': residents,
	}, context_instance=RequestContext(request))

@admin_required
def edit_room(request, room_title):
	room = get_object_or_404(Room, title=room_title)
	page_name = "Edit {0}".format(room_title)
	if room.unofficial_name:
		page_name += " ({0})".format(room.unofficial_name)
	edit_form = RoomForm(request.POST or None, instance=room)

	if edit_form.is_valid():
		room = edit_form.save()
		return HttpResponseRedirect(reverse('rooms:view', kwargs={'room_title': room.title}))

	return render_to_response('edit_room.html', {
		'page_name': page_name,
		'room': room,
		'edit_form': edit_form,
	}, context_instance=RequestContext(request))
