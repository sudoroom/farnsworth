'''
Project: Farnsworth

Author: Karandeep Singh Nagra
'''

from django.contrib import admin
from events.models import Event

class EventAdmin(admin.ModelAdmin):
	list_display = ('owner', 'title', 'start_time', 'end_time', 'post_date')
	search_fields = ('title', 'owner', 'description', 'start_time', 'end_time', 'post_date')
	list_filter = ('owner', 'title', 'start_time', 'end_time', 'post_date')
	date_hierarchy = ('start_time')
	ordering = ('-start_time',)

admin.site.register(Event, EventAdmin)
