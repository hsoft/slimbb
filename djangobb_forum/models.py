# coding: utf-8
from __future__ import unicode_literals

from hashlib import sha1
import os

from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


import pytz

from djangobb_forum.fields import AutoOneToOneField, JSONField
from djangobb_forum.util import convert_text_to_html
from djangobb_forum import settings as forum_settings


TZ_CHOICES = [(tz_name, tz_name) for tz_name in pytz.common_timezones]

PRIVACY_CHOICES = (
    (0, _('Display your e-mail address.')),
    (1, _('Hide your e-mail address but allow form e-mail.')),
    (2, _('Hide your e-mail address and disallow form e-mail.')),
)

MARKUP_CHOICES = [('bbcode', 'bbcode')]
try:
    import markdown
    del markdown
    MARKUP_CHOICES.append(("markdown", "markdown"))
except ImportError:
    pass

@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(_('Name'), max_length=80)
    groups = models.ManyToManyField(Group, blank=True, verbose_name=_('Groups'), help_text=_('Only users from these groups can see this category'))
    position = models.IntegerField(_('Position'), blank=True, default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name

    def forum_count(self):
        return self.forums.all().count()

    @property
    def topics(self):
        return Topic.objects.filter(forum__category__id=self.id).select_related()

    @property
    def posts(self):
        return Post.objects.filter(topic__forum__category__id=self.id).select_related()

    def has_access(self, user):
        if user.is_superuser:
            return True
        if self.groups.exists():
            if user.is_authenticated():
                if not self.groups.filter(user__pk=user.id).exists():
                    return False
            else:
                return False
        return True


@python_2_unicode_compatible
class Forum(models.Model):
    category = models.ForeignKey(Category, related_name='forums', verbose_name=_('Category'))
    name = models.CharField(_('Name'), max_length=80)
    position = models.IntegerField(_('Position'), blank=True, default=0)
    description = models.TextField(_('Description'), blank=True, default='')
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Moderators'))
    updated = models.DateTimeField(_('Updated'), auto_now=True)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)
    topic_count = models.IntegerField(_('Topic count'), blank=True, default=0)
    last_post = models.ForeignKey('Post', related_name='last_forum_post', blank=True, null=True)

    class Meta:
        ordering = ['position']
        verbose_name = _('Forum')
        verbose_name_plural = _('Forums')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('djangobb:forum', args=[self.id])

    @property
    def posts(self):
        return Post.objects.filter(topic__forum__id=self.id).select_related()


@python_2_unicode_compatible
class Topic(models.Model):
    forum = models.ForeignKey(Forum, related_name='topics', verbose_name=_('Forum'))
    name = models.CharField(_('Subject'), max_length=255)
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'))
    views = models.IntegerField(_('Views count'), blank=True, default=0)
    sticky = models.BooleanField(_('Sticky'), blank=True, default=False)
    closed = models.BooleanField(_('Closed'), blank=True, default=False)
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='subscriptions', verbose_name=_('Subscribers'), blank=True)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)
    last_post = models.ForeignKey('Post', related_name='last_topic_post', blank=True, null=True)

    class Meta:
        ordering = ['-updated']
        get_latest_by = 'updated'
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        try:
            last_post = self.posts.latest()
            last_post.last_forum_post.clear()
        except Post.DoesNotExist:
            pass
        else:
            last_post.last_forum_post.clear()
        forum = self.forum
        super(Topic, self).delete(*args, **kwargs)
        try:
            forum.last_post = Topic.objects.filter(forum__id=forum.id).latest().last_post
        except Topic.DoesNotExist:
            forum.last_post = None
        forum.topic_count = Topic.objects.filter(forum__id=forum.id).count()
        forum.post_count = Post.objects.filter(topic__forum__id=forum.id).count()
        forum.save()

    @property
    def head(self):
        try:
            return self.posts.select_related().order_by('created')[0]
        except IndexError:
            return None

    @property
    def reply_count(self):
        return self.post_count - 1

    def get_absolute_url(self):
        return reverse('djangobb:topic', args=[self.id])

    def update_read(self, user):
        tracking = user.posttracking
        #if last_read > last_read - don't check topics
        if tracking.last_read and (tracking.last_read > self.last_post.created):
            return
        if isinstance(tracking.topics, dict):
            #clear topics if len > 5Kb and set last_read to current time
            if len(tracking.topics) > 5120:
                tracking.topics = None
                tracking.last_read = timezone.now()
                tracking.save()
            #update topics if exist new post or does't exist in dict
            if self.last_post_id > tracking.topics.get(str(self.id), 0):
                tracking.topics[str(self.id)] = self.last_post_id
                tracking.save()
        else:
            #initialize topic tracking dict
            tracking.topics = {self.id: self.last_post_id}
            tracking.save()


@python_2_unicode_compatible
class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name='posts', verbose_name=_('Topic'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Updated by'), blank=True, null=True)
    markup = models.CharField(_('Markup'), max_length=15, default=forum_settings.DEFAULT_MARKUP, choices=MARKUP_CHOICES)
    body = models.TextField(_('Message'))
    body_html = models.TextField(_('HTML version'))
    user_ip = models.GenericIPAddressField(_('User IP'), blank=True, null=True)


    class Meta:
        ordering = ['created']
        get_latest_by = 'created'
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')

    def save(self, *args, **kwargs):
        self.body_html = convert_text_to_html(self.body, self.markup)
        super(Post, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        self_id = self.id
        head_post_id = self.topic.posts.order_by('created')[0].id
        forum = self.topic.forum
        topic = self.topic
        profile = self.user.forum_profile
        self.last_topic_post.clear()
        self.last_forum_post.clear()
        super(Post, self).delete(*args, **kwargs)
        #if post was last in topic - remove topic
        if self_id == head_post_id:
            topic.delete()
        else:
            try:
                topic.last_post = Post.objects.filter(topic__id=topic.id).latest()
            except Post.DoesNotExist:
                topic.last_post = None
            topic.post_count = Post.objects.filter(topic__id=topic.id).count()
            topic.save()
        try:
            forum.last_post = Post.objects.filter(topic__forum__id=forum.id).latest()
        except Post.DoesNotExist:
            forum.last_post = None
        #TODO: for speedup - save/update only changed fields
        forum.post_count = Post.objects.filter(topic__forum__id=forum.id).count()
        forum.topic_count = Topic.objects.filter(forum__id=forum.id).count()
        forum.save()
        profile.post_count = Post.objects.filter(user__id=self.user_id).count()
        profile.save()

    def get_absolute_url(self):
        return reverse('djangobb:post', args=[self.id])

    def summary(self):
        LIMIT = 50
        tail = len(self.body) > LIMIT and '...' or ''
        return self.body[:LIMIT] + tail

    __str__ = summary


class Profile(models.Model):
    user = AutoOneToOneField(settings.AUTH_USER_MODEL, related_name='forum_profile', verbose_name=_('User'))
    signature = models.TextField(_('Signature'), blank=True, default='', max_length=forum_settings.SIGNATURE_MAX_LENGTH)
    signature_html = models.TextField(_('Signature'), blank=True, default='', max_length=forum_settings.SIGNATURE_MAX_LENGTH)
    time_zone = models.CharField(_('Time zone'),max_length=50, choices=TZ_CHOICES, default=settings.TIME_ZONE)
    language = models.CharField(_('Language'), max_length=5, default='', choices=settings.LANGUAGES)
    show_signatures = models.BooleanField(_('Show signatures'), blank=True, default=True)
    privacy_permission = models.IntegerField(_('Privacy permission'), choices=PRIVACY_CHOICES, default=1)
    auto_subscribe = models.BooleanField(_('Auto subscribe'), help_text=_("Auto subscribe all topics you have created or reply."), blank=True, default=False)
    markup = models.CharField(_('Default markup'), max_length=15, default=forum_settings.DEFAULT_MARKUP, choices=MARKUP_CHOICES)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def last_post(self):
        posts = Post.objects.filter(user__id=self.user_id).order_by('-created')
        if posts:
            return posts[0].created
        else:
            return None


@python_2_unicode_compatible
class PostTracking(models.Model):
    """
    Model for tracking read/unread posts.
    In topics stored ids of topics and last_posts as dict.
    """

    user = AutoOneToOneField(settings.AUTH_USER_MODEL)
    topics = JSONField(null=True, blank=True)
    last_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Post tracking')
        verbose_name_plural = _('Post tracking')

    def __str__(self):
        return self.user.username


@python_2_unicode_compatible
class Report(models.Model):
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reported_by', verbose_name=_('Reported by'))
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    zapped = models.BooleanField(_('Zapped'), blank=True, default=False)
    zapped_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='zapped_by', blank=True, null=True, verbose_name=_('Zapped by'))
    created = models.DateTimeField(_('Created'), blank=True)
    reason = models.TextField(_('Reason'), blank=True, default='', max_length='1000')

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')

    def __str__(self):
        return '%s %s' % (self.reported_by , self.zapped)


@python_2_unicode_compatible
class Ban(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_('Banned user'), related_name='ban_users')
    ban_start = models.DateTimeField(_('Ban start'), default=timezone.now)
    ban_end = models.DateTimeField(_('Ban end'), blank=True, null=True)
    reason = models.TextField(_('Reason'))

    class Meta:
        verbose_name = _('Ban')
        verbose_name_plural = _('Bans')

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        self.user.is_active = False
        self.user.save()
        super(Ban, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.user.is_active = True
        self.user.save()
        super(Ban, self).delete(*args, **kwargs)


@python_2_unicode_compatible
class Attachment(models.Model):
    post = models.ForeignKey(Post, verbose_name=_('Post'), related_name='attachments')
    size = models.IntegerField(_('Size'))
    content_type = models.CharField(_('Content type'), max_length=255)
    path = models.CharField(_('Path'), max_length=255)
    name = models.TextField(_('Name'))
    hash = models.CharField(_('Hash'), max_length=40, blank=True, default='', db_index=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Attachment, self).save(*args, **kwargs)
        if not self.hash:
            self.hash = sha1((str(self.id) + settings.SECRET_KEY).encode('ascii')).hexdigest()
        super(Attachment, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('djangobb:forum_attachment', args=[self.hash])

    def get_absolute_path(self):
        return os.path.join(settings.MEDIA_ROOT, forum_settings.ATTACHMENT_UPLOAD_TO,
                            self.path)

