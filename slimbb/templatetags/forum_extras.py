# -*- coding: utf-8
from __future__ import unicode_literals

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_text
from django.conf import settings
from django.utils.html import escape
from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import naturalday

from ..models import Report


register = template.Library()

# TODO:
# * rename all tags with forum_ prefix

@register.filter
def profile_link(user):
    data = '<a href="%s">%s</a>' % (\
        reverse('slimbb:forum_profile', args=[user.username]), user.username)
    return mark_safe(data)


@register.tag
def forum_time(parser, token):
    try:
        tag, time = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('forum_time requires single argument')
    else:
        return ForumTimeNode(time)


class ForumTimeNode(template.Node):
    def __init__(self, time):
        self.time = template.Variable(time)

    def render(self, context):
        time = timezone.localtime(self.time.resolve(context))
        formatted_time = '%s %s' % (naturalday(time), time.strftime('%H:%M:%S'))
        formatted_time = mark_safe(formatted_time)
        return formatted_time


@register.simple_tag
def link(object, anchor=''):
    """
    Return A tag with link to object.
    """

    url = hasattr(object, 'get_absolute_url') and object.get_absolute_url() or None
    anchor = anchor or smart_text(object)
    return mark_safe('<a href="%s">%s</a>' % (url, escape(anchor)))


@register.filter
def has_unreads(topic, user):
    """
    Check if topic has messages which user didn't read.
    """
    if not user.is_authenticated() or\
        (user.posttracking.last_read is not None and\
         user.posttracking.last_read > topic.updated):
            return False
    else:
        if isinstance(user.posttracking.topics, dict):
            if topic.last_post_id > user.posttracking.topics.get(str(topic.id), 0):
                return True
            else:
                return False
        return True

@register.filter
def forum_unreads(forum, user):
    """
    Check if forum has topic which user didn't read.
    """
    if not user.is_authenticated():
        return False
    else:
        if isinstance(user.posttracking.topics, dict):
            topics = forum.topics.all().only('last_post')
            if user.posttracking.last_read:
                topics = topics.filter(updated__gte=user.posttracking.last_read)
            for topic in topics:
                if topic.last_post_id > user.posttracking.topics.get(str(topic.id), 0):
                    return True
        return False


@register.filter
def forum_moderated_by(topic, user):
    """
    Check if user is moderator of topic's forum.
    """

    return user.is_superuser or user in topic.forum.moderators.all()


@register.filter
def forum_editable_by(post, user):
    """
    Check if the post could be edited by the user.
    """

    if user.is_superuser:
        return True
    if post.user == user:
        return True
    if user in post.topic.forum.moderators.all():
        return True
    return False


@register.filter
def forum_posted_by(post, user):
    """
    Check if the post is writed by the user.
    """

    return post.user == user


@register.filter
def forum_equal_to(obj1, obj2):
    """
    Check if objects are equal.
    """

    return obj1 == obj2


@register.filter
def attachment_link(attach):
    from django.template.defaultfilters import filesizeformat
    if attach.content_type in ['image/png', 'image/gif', 'image/jpeg']:
        img = '<img src="%sslimbb/img/attachment/image.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['application/x-tar', 'application/zip']:
        img = '<img src="%sslimbb/img/attachment/compress.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['text/plain']:
        img = '<img src="%sslimbb/img/attachment/text.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['application/msword']:
        img = '<img src="%sslimbb/img/attachment/doc.png" alt="attachment" />' % (settings.STATIC_URL)
    else:
        img = '<img src="%sslimbb/img/attachment/unknown.png" alt="attachment" />' % (settings.STATIC_URL)
    attachment = '%s <a href="%s">%s</a> (%s)' % (img, attach.get_absolute_url(), attach.name, filesizeformat(attach.size))
    return mark_safe(attachment)


@register.simple_tag
def new_reports():
    return Report.objects.filter(zapped=False).count()


# http://stackoverflow.com/a/16609498
@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()
