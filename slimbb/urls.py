from django.conf.urls import url

from . import settings as forum_settings
from . import views as forum_views
from .feeds import LastPosts, LastTopics, LastPostsOnForum, \
     LastPostsOnCategory, LastPostsOnTopic


urlpatterns = [

    # Forum
    url('^$', forum_views.index, name='index'),
    url('^(?P<forum_id>\d+)/$', forum_views.show_forum, name='forum'),
    url('^moderate/(?P<forum_id>\d+)/$', forum_views.moderate, name='moderate'),
    url('^search/$', forum_views.search, name='search'),
    url('^misc/$', forum_views.misc, name='misc'),

    # User
    url('^user/(?P<username>.*)/$', forum_views.user, name='forum_profile'),
    url('^users/$', forum_views.users, name='forum_users'),

    # Topic
    url('^topic/(?P<topic_id>\d+)/$', forum_views.show_topic, name='topic'),
    url('^(?P<forum_id>\d+)/topic/add/$', forum_views.add_topic, name='add_topic'),
    url('^topic/(?P<topic_id>\d+)/delete_posts/$', forum_views.delete_posts, name='delete_posts'),
    url('^topic/move/$', forum_views.move_topic, name='move_topic'),
    url('^topic/(?P<topic_id>\d+)/stick_unstick/(?P<action>[s|u])/$', forum_views.stick_unstick_topic, name='stick_unstick_topic'),
    url('^topic/(?P<topic_id>\d+)/open_close/(?P<action>[c|o])/$', forum_views.open_close_topic, name='open_close_topic'),

    # Post
    url('^post/(?P<post_id>\d+)/$', forum_views.show_post, name='post'),
    url('^post/(?P<post_id>\d+)/edit/$', forum_views.edit_post, name='edit_post'),
    url('^post/(?P<post_id>\d+)/delete/$', forum_views.delete_post, name='delete_post'),
    # Post preview
    url(r'^preview/$', forum_views.post_preview, name='post_preview'),

    # Subscription
    url('^subscription/topic/(?P<topic_id>\d+)/delete/$', forum_views.delete_subscription, name='forum_delete_subscription'),
    url('^subscription/topic/(?P<topic_id>\d+)/add/$', forum_views.add_subscription, name='forum_add_subscription'),

    # Feeds
    url(r'^feeds/posts/$', LastPosts(), name='forum_posts_feed'),
    url(r'^feeds/topics/$', LastTopics(), name='forum_topics_feed'),
    url(r'^feeds/topic/(?P<topic_id>\d+)/$', LastPostsOnTopic(), name='forum_topic_feed'),
    url(r'^feeds/forum/(?P<forum_id>\d+)/$', LastPostsOnForum(), name='forum_forum_feed'),
    url(r'^feeds/category/(?P<category_id>\d+)/$', LastPostsOnCategory(), name='forum_category_feed'),
]

### EXTENSIONS ###

# ATTACHMENT Extension
if (forum_settings.ATTACHMENT_SUPPORT):
    urlpatterns += [
        url('^attachment/(?P<hash>\w+)/$', forum_views.show_attachment, name='forum_attachment'),
    ]
