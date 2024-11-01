from django.contrib import admin
from django.contrib.admin.models import LogEntry


# Register your models here.
admin.site.site_header  =  "Админка"  
admin.site.site_title  =  "Админка"
admin.site.index_title  =  "Админка"



class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    list_filter = ( 'user', 'action_flag', 'action_time', 'content_type')
    search_fields = ('user__username', 'object_repr', 'change_message')

admin.site.register(LogEntry, LogEntryAdmin)