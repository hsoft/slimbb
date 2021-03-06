# coding: utf-8
from __future__ import unicode_literals

import math
from datetime import timedelta
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from haystack.query import SearchQuerySet, SQ

from . import settings as forum_settings
from .forms import AddPostForm, EditPostForm, PostSearchForm, EssentialsProfileForm, ReportForm
from .models import Category, Forum, Topic, Post, \
    Attachment, PostTracking
from .templatetags import forum_extras
from .templatetags.forum_extras import forum_moderated_by
from .util import build_form, convert_text_to_html, get_page


User = get_user_model()

def index(request):
    _forums = Forum.objects.all()
    user = request.user
    if not user.is_superuser:
        user_groups = user.groups.all() or [] # need 'or []' for anonymous user otherwise: 'EmptyManager' object is not iterable
        _forums = _forums.filter(Q(category__groups__in=user_groups) | Q(category__groups__isnull=True))

    _forums = _forums.select_related('last_post__topic', 'last_post__user', 'category')

    cats = {}
    forums = {}
    for forum in _forums:
        cat = cats.setdefault(forum.category.id,
            {'id': forum.category.id, 'cat': forum.category, 'forums': []})
        cat['forums'].append(forum)
        forums[forum.id] = forum

    cmpkey = lambda x: x['cat'].position
    cats = sorted(cats.values(), key=cmpkey)

    to_return = {
        'cats': cats,
        'posts': Post.objects.count(),
        'topics': Topic.objects.count(),
        'users': User.objects.count(),
    }
    return render(request, 'slimbb/index.html', to_return)


@transaction.atomic
def moderate(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    if request.user.is_superuser or request.user in forum.moderators.all():
        topic_ids = request.POST.getlist('topic_id')
        if 'move_topics' in request.POST:
            return render(request, 'slimbb/move_topic.html', {
                'categories': Category.objects.all(),
                'topic_ids': topic_ids,
                'exclude_forum': forum,
            })
        elif 'delete_topics' in request.POST:
            for topic_id in topic_ids:
                topic = get_object_or_404(Topic, pk=topic_id)
                topic.delete()
            messages.success(request, _("Topics deleted"))
            return HttpResponseRedirect(reverse('slimbb:index'))
        elif 'open_topics' in request.POST:
            for topic_id in topic_ids:
                open_close_topic(request, topic_id, 'o')
            messages.success(request, _("Topics opened"))
            return HttpResponseRedirect(reverse('slimbb:index'))
        elif 'close_topics' in request.POST:
            for topic_id in topic_ids:
                open_close_topic(request, topic_id, 'c')
            messages.success(request, _("Topics closed"))
            return HttpResponseRedirect(reverse('slimbb:index'))

        return render(request, 'slimbb/moderate.html', {
                'forum': forum,
                'topics_page': get_page(topics, request, forum_settings.FORUM_PAGE_SIZE),
                'posts': forum.posts.count(),
        })
    else:
        raise Http404


def search(request):
    # TODO: used forms in every search type

    def _render_search_form(form=None):
        return render(request, 'slimbb/search_form.html', {'categories': Category.objects.all(),
                'form': form,
                })

    if not 'action' in request.GET:
        return _render_search_form(form=PostSearchForm())

    if request.GET.get("show_as") == "posts":
        show_as_posts = True
        template_name = 'slimbb/search_posts.html'
    else:
        show_as_posts = False
        template_name = 'slimbb/search_topics.html'

    context = {}

    # Create 'user viewable' pre-filtered topics/posts querysets
    viewable_category = Category.objects.all()
    topics = Topic.objects.all().order_by("-last_post__created")
    posts = Post.objects.all().order_by('-created')
    user = request.user
    if not user.is_superuser:
        user_groups = user.groups.all() or [] # need 'or []' for anonymous user otherwise: 'EmptyManager' object is not iterable
        viewable_category = viewable_category.filter(Q(groups__in=user_groups) | Q(groups__isnull=True))

        topics = Topic.objects.filter(forum__category__in=viewable_category)
        posts = Post.objects.filter(topic__forum__category__in=viewable_category)

    base_url = None
    _generic_context = True

    action = request.GET['action']
    if action == 'show_24h':
        date = timezone.now() - timedelta(days=1)
        if show_as_posts:
            context["posts"] = posts.filter(Q(created__gte=date) | Q(updated__gte=date))
        else:
            context["topics"] = topics.filter(Q(last_post__created__gte=date) | Q(last_post__updated__gte=date))
        _generic_context = False
    elif action == 'show_new':
        if not user.is_authenticated():
            raise Http404("Search 'show_new' not available for anonymous user.")
        try:
            last_read = PostTracking.objects.get(user=user).last_read
        except PostTracking.DoesNotExist:
            last_read = None

        if last_read:
            if show_as_posts:
                context["posts"] = posts.filter(Q(created__gte=last_read) | Q(updated__gte=last_read))
            else:
                context["topics"] = topics.filter(Q(last_post__created__gte=last_read) | Q(last_post__updated__gte=last_read))
            _generic_context = False
        else:
            #searching more than forum_settings.SEARCH_PAGE_SIZE in this way - not good idea :]
            topics_id = [topic.id for topic in topics[:forum_settings.SEARCH_PAGE_SIZE] if forum_extras.has_unreads(topic, user)]
            topics = Topic.objects.filter(id__in=topics_id) # to create QuerySet

    elif action == 'show_unanswered':
        topics = topics.filter(post_count=1)
    elif action == 'show_subscriptions':
        topics = topics.filter(subscribers__id=user.id)
    elif action == 'show_user':
        # Show all posts from user or topics started by user
        if not user.is_authenticated():
            raise Http404("Search 'show_user' not available for anonymous user.")

        user_id = request.GET.get("user_id", user.id)
        try:
            user_id = int(user_id)
        except ValueError:
            raise SuspiciousOperation()

        if user_id != user.id:
            try:
                search_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, _("Error: User unknown!"))
                return HttpResponseRedirect(request.path)
            messages.info(request, _("Filter by user '%(username)s'.") % {'username': search_user.username})

        if show_as_posts:
            posts = posts.filter(user__id=user_id)
        else:
            # show as topic
            topics = topics.filter(posts__user__id=user_id).order_by("-last_post__created").distinct()

        base_url = "?action=show_user&user_id=%s&show_as=" % user_id
    elif action == 'search':
        form = PostSearchForm(request.GET)
        if not form.is_valid():
            return _render_search_form(form)

        keywords = form.cleaned_data['keywords']
        author = form.cleaned_data['author']
        forum = form.cleaned_data['forum']
        search_in = form.cleaned_data['search_in']
        sort_by = form.cleaned_data['sort_by']
        sort_dir = form.cleaned_data['sort_dir']

        query = SearchQuerySet().models(Post)

        if author:
            query = query.filter(author__username=author)

        if forum != '0':
            query = query.filter(forum__id=forum)

        if keywords:
            if search_in == 'all':
                query = query.filter(SQ(topic=keywords) | SQ(text=keywords))
            elif search_in == 'message':
                query = query.filter(text=keywords)
            elif search_in == 'topic':
                query = query.filter(topic=keywords)

        order = {'0': 'created',
                 '1': 'author',
                 '2': 'topic',
                 '3': 'forum'}.get(sort_by, 'created')
        if sort_dir == 'DESC':
            order = '-' + order

        post_pks = query.values_list("pk", flat=True)

        if not show_as_posts:
            # TODO: We have here a problem to get a list of topics without double entries.
            # Maybe we must add a search index over topics?

            # Info: If whoosh backend used, setup HAYSTACK_ITERATOR_LOAD_PER_QUERY
            #    to a higher number to speed up
            context["topics"] = topics.filter(posts__in=post_pks).distinct()
        else:
            # FIXME: How to use the pre-filtered query from above?
            posts = posts.filter(pk__in=post_pks).order_by(order)
            context["posts"] = posts

        get_query_dict = request.GET.copy()
        get_query_dict.pop("show_as")
        base_url = "?%s&show_as=" % get_query_dict.urlencode()
        _generic_context = False

    if _generic_context:
        if show_as_posts:
            context["posts"] = posts.filter(topic__in=topics).order_by('-created')
        else:
            context["topics"] = topics

    if base_url is None:
        base_url = "?action=%s&show_as=" % action

    if show_as_posts:
        context['posts_page'] = get_page(context['posts'], request, forum_settings.SEARCH_PAGE_SIZE)
        context["as_topic_url"] = base_url + "topics"
        post_count = context["posts"].count()
        messages.success(request, _("Found %i posts.") % post_count)
    else:
        context['topics_page'] = get_page(context['topics'], request, forum_settings.SEARCH_PAGE_SIZE)
        context["as_post_url"] = base_url + "posts"
        topic_count = context["topics"].count()
        messages.success(request, _("Found %i topics.") % topic_count)

    return render(request, template_name, context)


@login_required
def misc(request):
    if 'action' in request.GET:
        action = request.GET['action']
        if action == 'markread':
            user = request.user
            PostTracking.objects.filter(user__id=user.id).update(last_read=timezone.now(), topics=None)
            messages.info(request, _("All topics marked as read."))
            return HttpResponseRedirect(reverse('slimbb:index'))

        elif action == 'report':
            if request.GET.get('post_id', ''):
                post_id = request.GET['post_id']
                post = get_object_or_404(Post, id=post_id)
                form = build_form(ReportForm, request, reported_by=request.user, post=post_id)
                if request.method == 'POST' and form.is_valid():
                    form.save()
                    messages.info(request, _("Post reported."))
                    return HttpResponseRedirect(post.get_absolute_url())
                return render(request, 'slimbb/report.html', {'form':form})


def show_forum(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    if not forum.category.has_access(request.user):
        raise PermissionDenied
    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    moderator = request.user.is_superuser or\
        request.user in forum.moderators.all()

    categories = []
    for category in Category.objects.all():
        if category.has_access(request.user):
            categories.append(category)

    to_return = {
        'categories': categories,
        'forum': forum,
        'posts': forum.post_count,
        'topics_page': get_page(topics, request, forum_settings.FORUM_PAGE_SIZE),
        'moderator': moderator,
    }
    return render(request, 'slimbb/forum.html', to_return)


@transaction.atomic
def show_topic(request, topic_id):
    """
    * Display a topic
    * save a reply
    """
    post_request = request.method == "POST"
    user_is_authenticated = request.user.is_authenticated()
    if post_request and not user_is_authenticated:
        # Info: only user that are logged in should get forms in the page.
        raise PermissionDenied

    topic = get_object_or_404(Topic.objects.select_related(), pk=topic_id)
    if not topic.forum.category.has_access(request.user):
        raise PermissionDenied

    last_post = topic.last_post

    if request.user.is_authenticated():
        topic.update_read(request.user)
    posts = topic.posts.all().select_related()

    moderator = request.user.is_superuser or request.user in topic.forum.moderators.all()
    if user_is_authenticated and request.user in topic.subscribers.all():
        subscribed = True
    else:
        subscribed = False

    # reply form
    reply_form = None
    form_url = None
    back_url = None
    if user_is_authenticated and not topic.closed:
        form_url = request.path + "#reply" # if form validation failed: browser should scroll down to reply form ;)
        back_url = request.path
        ip = request.META.get('REMOTE_ADDR', None)
        post_form_kwargs = {"topic":topic, "user":request.user, "ip":ip}
        if post_request and AddPostForm.FORM_NAME in request.POST:
            reply_form = AddPostForm(request.POST, request.FILES, **post_form_kwargs)
            if reply_form.is_valid():
                post = reply_form.save()
                messages.success(request, _("Your reply saved."))
                return HttpResponseRedirect(post.get_absolute_url())
        else:
            reply_form = AddPostForm(
                initial={
                    'subscribe': request.user.forum_profile.auto_subscribe,
                },
                **post_form_kwargs
            )

    view_data = {
        'categories': Category.objects.all(),
        'topic': topic,
        'posts_page': get_page(posts, request, forum_settings.TOPIC_PAGE_SIZE),
    }
    view_data.update({
        'last_post': last_post,
        'form_url': form_url,
        'reply_form': reply_form,
        'back_url': back_url,
        'moderator': moderator,
        'subscribed': subscribed,
    })
    return render(request, 'slimbb/topic.html', view_data)


@login_required
@transaction.atomic
def add_topic(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    if not forum.category.has_access(request.user):
        raise PermissionDenied

    ip = request.META.get('REMOTE_ADDR', None)
    post_form_kwargs = {"forum": forum, "user": request.user, "ip": ip, }

    if request.method == 'POST':
        form = AddPostForm(request.POST, request.FILES, **post_form_kwargs)
        if form.is_valid():
            all_valid = True
        else:
            all_valid = False

        if all_valid:
            post = form.save()
            messages.success(request, _("Topic saved."))
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = AddPostForm(
            initial={
                'subscribe': request.user.forum_profile.auto_subscribe,
            },
            **post_form_kwargs
        )

    context = {
        'forum': forum,
        'form': form,
        'form_url': request.path,
        'back_url': forum.get_absolute_url(),
    }
    return render(request, 'slimbb/add_topic.html', context)


@transaction.atomic
def user(request, username):
    user = get_object_or_404(User, username=username)
    if request.user.is_authenticated() and user == request.user or request.user.is_superuser:
        form = build_form(EssentialsProfileForm, request, instance=user.forum_profile, extra_args={'request': request})
        if request.method == 'POST' and form.is_valid():
            form.save()
            profile_url = reverse('slimbb:forum_profile', args=[user.username])
            messages.success(request, _("User profile saved."))
            return HttpResponseRedirect(profile_url)
        return render(request, 'slimbb/profile.html', {
            'profile': user,
            'form': form,
        })
    else:
        template = 'slimbb/user.html'
        topic_count = Topic.objects.filter(user__id=user.id).count()
        if user.forum_profile.post_count < forum_settings.POST_USER_SEARCH and not request.user.is_authenticated():
            messages.error(request, _("Please sign in."))
            return HttpResponseRedirect(settings.LOGIN_URL + '?next=%s' % request.path)
        return render(request, template, {'profile': user,
                'topic_count': topic_count,
               })


def show_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    count = post.topic.posts.filter(created__lt=post.created).count() + 1
    page = math.ceil(count / float(forum_settings.TOPIC_PAGE_SIZE))
    url = '%s?page=%d#post-%d' % (reverse('slimbb:topic', args=[post.topic.id]), page, post.id)
    return HttpResponseRedirect(url)


@login_required
@transaction.atomic
def edit_post(request, post_id):
    from .templatetags.forum_extras import forum_editable_by

    post = get_object_or_404(Post, pk=post_id)
    topic = post.topic
    if not forum_editable_by(post, request.user):
        messages.error(request, _("No permissions to edit this post."))
        return HttpResponseRedirect(post.get_absolute_url())
    form = build_form(EditPostForm, request, topic=topic, instance=post)
    if form.is_valid():
        post = form.save(commit=False)
        post.updated_by = request.user
        post.save()
        messages.success(request, _("Post updated."))
        return HttpResponseRedirect(post.get_absolute_url())

    return render(request, 'slimbb/edit_post.html', {'form': form,
            'post': post,
            })


@login_required
@transaction.atomic
def delete_posts(request, topic_id):

    topic = Topic.objects.select_related().get(pk=topic_id)

    if forum_moderated_by(topic, request.user):
        deleted = False
        post_list = request.POST.getlist('post')
        for post_id in post_list:
            if not deleted:
                deleted = True
            delete_post(request, post_id)
        if deleted:
            messages.success(request, _("Post deleted."))
            return HttpResponseRedirect(topic.get_absolute_url())

    last_post = topic.posts.latest()

    if request.user.is_authenticated():
        topic.update_read(request.user)

    posts = topic.posts.all().select_related()

    form = AddPostForm(topic=topic)

    moderator = request.user.is_superuser or\
        request.user in topic.forum.moderators.all()
    if request.user.is_authenticated() and request.user in topic.subscribers.all():
        subscribed = True
    else:
        subscribed = False
    return render(request, 'slimbb/delete_posts.html', {
        'topic': topic,
        'last_post': last_post,
        'form': form,
        'moderator': moderator,
        'subscribed': subscribed,
        'posts_page': get_page(posts, request, forum_settings.TOPIC_PAGE_SIZE),
    })


@login_required
@transaction.atomic
def move_topic(request):
    if 'topic_id' in request.GET:
        #if move only 1 topic
        topic_ids = [request.GET['topic_id']]
    else:
        topic_ids = request.POST.getlist('topic_id')
    first_topic = topic_ids[0]
    topic = get_object_or_404(Topic, pk=first_topic)
    from_forum = topic.forum
    if 'to_forum' in request.POST:
        to_forum_id = int(request.POST['to_forum'])
        to_forum = get_object_or_404(Forum, pk=to_forum_id)
        for topic_id in topic_ids:
            topic = get_object_or_404(Topic, pk=topic_id)
            if topic.forum != to_forum:
                if forum_moderated_by(topic, request.user):
                    topic.forum = to_forum
                    topic.save()

        #TODO: not DRY
        try:
            last_post = Post.objects.filter(topic__forum__id=from_forum.id).latest()
        except Post.DoesNotExist:
            last_post = None
        from_forum.last_post = last_post
        from_forum.topic_count = from_forum.topics.count()
        from_forum.post_count = from_forum.posts.count()
        from_forum.save()
        messages.success(request, _("Topic moved."))
        return HttpResponseRedirect(to_forum.get_absolute_url())

    return render(request, 'slimbb/move_topic.html', {'categories': Category.objects.all(),
            'topic_ids': topic_ids,
            'exclude_forum': from_forum,
            })


@login_required
@transaction.atomic
def stick_unstick_topic(request, topic_id, action):
    topic = get_object_or_404(Topic, pk=topic_id)
    if forum_moderated_by(topic, request.user):
        if action == 's':
            topic.sticky = True
            messages.success(request, _("Topic marked as sticky."))
        elif action == 'u':
            messages.success(request, _("Sticky flag removed from topic."))
            topic.sticky = False
        topic.save()
    return HttpResponseRedirect(topic.get_absolute_url())


@login_required
@transaction.atomic
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    topic = post.topic
    forum = post.topic.forum

    if not (request.user.is_superuser or\
        request.user in post.topic.forum.moderators.all() or \
        (post.user == request.user)):
        messages.success(request, _("You haven't the permission to delete this post."))
        return HttpResponseRedirect(post.get_absolute_url())

    post.delete()
    messages.success(request, _("Post deleted."))

    try:
        Topic.objects.get(pk=topic.id)
    except Topic.DoesNotExist:
        #removed latest post in topic
        return HttpResponseRedirect(forum.get_absolute_url())
    else:
        return HttpResponseRedirect(topic.get_absolute_url())


@login_required
@transaction.atomic
def open_close_topic(request, topic_id, action):
    topic = get_object_or_404(Topic, pk=topic_id)
    if forum_moderated_by(topic, request.user):
        if action == 'c':
            topic.closed = True
            messages.success(request, _("Topic closed."))
        elif action == 'o':
            topic.closed = False
            messages.success(request, _("Topic opened."))
        topic.save()
    return HttpResponseRedirect(topic.get_absolute_url())


@login_required
@transaction.atomic
def delete_subscription(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.remove(request.user)
    messages.info(request, _("Topic subscription removed."))
    if 'from_topic' in request.GET:
        return HttpResponseRedirect(reverse('slimbb:topic', args=[topic.id]))
    else:
        return HttpResponseRedirect(reverse('slimbb:forum_profile', args=[request.user.username]))


@login_required
@transaction.atomic
def add_subscription(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.add(request.user)
    messages.success(request, _("Topic subscribed."))
    return HttpResponseRedirect(reverse('slimbb:topic', args=[topic.id]))


@login_required
def show_attachment(request, hash):
    attachment = get_object_or_404(Attachment, hash=hash)
    file_data = open(attachment.get_absolute_path(), 'rb').read()
    response = HttpResponse(file_data, content_type=attachment.content_type)
    response['Content-Disposition'] = smart_str('attachment; filename="%s"' % attachment.name)
    return response


@login_required
@csrf_exempt
def post_preview(request):
    '''Preview for markitup'''
    data = request.POST.get('data', '')
    data = convert_text_to_html(data)
    return render(request, 'slimbb/post_preview.html', {'data': data})
