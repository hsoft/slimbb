# coding: utf-8

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from djangobb_forum.models import Category, Forum, Topic, Post, Profile, \
    Report, Ban, Attachment, PostTracking


class BaseModelAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        # disabled, because delete_selected ignoring delete model method
        actions = super(BaseModelAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class CategoryAdmin(BaseModelAdmin):
    list_display = ['name', 'position', 'forum_count']

class ForumAdmin(BaseModelAdmin):
    list_display = ['name', 'category', 'position', 'topic_count']
    raw_id_fields = ['moderators', 'last_post']

class TopicAdmin(BaseModelAdmin):
    def subscribers2(self, obj):
        return ", ".join([user.username for user in obj.subscribers.all()])
    subscribers2.short_description = _("subscribers")

    list_display = ['name', 'forum', 'created', 'head', 'post_count', 'subscribers2']
    search_fields = ['name']
    raw_id_fields = ['user', 'subscribers', 'last_post']

class PostAdmin(BaseModelAdmin):
    list_display = ['topic', 'user', 'created', 'updated', 'summary']
    search_fields = ['body']
    raw_id_fields = ['topic', 'user', 'updated_by']

class ProfileAdmin(BaseModelAdmin):
    list_display = ['user', 'time_zone', 'language']
    raw_id_fields = ['user']

class PostTrackingAdmin(BaseModelAdmin):
    list_display = ['user', 'last_read', 'topics']
    raw_id_fields = ['user']

class ReportAdmin(BaseModelAdmin):
    list_display = ['reported_by', 'post', 'zapped', 'zapped_by', 'created', 'reason', 'link_to_post']
    raw_id_fields = ['reported_by', 'post', 'zapped_by']
    list_filter = ('zapped', 'created')

    def link_to_post(self, instance):
        return '<a href="%(link)s">#%(pk)s</a>' % {'link': instance.post.get_absolute_url(), 'pk': instance.post.pk}
    link_to_post.short_description = _("Link to post")
    link_to_post.allow_tags = True

    def save_model(self, request, obj, form, change):
        if change and obj.zapped:
            obj.zapped_by = request.user
            obj.save()

class BanAdmin(BaseModelAdmin):
    list_display = ['user', 'ban_start', 'ban_end', 'reason']
    raw_id_fields = ['user']

class AttachmentAdmin(BaseModelAdmin):
    list_display = ['id', 'name', 'size', 'path', 'hash', ]
    search_fields = ['name']
    list_display_links = ('name',)
    list_filter = ("content_type",)


admin.site.register(Category, CategoryAdmin)
admin.site.register(Forum, ForumAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(PostTracking, PostTrackingAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Ban, BanAdmin)
admin.site.register(Attachment, AttachmentAdmin)

