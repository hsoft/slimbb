# coding: utf-8


from django.conf import settings

from . import settings as slimbb_settings


def forum_settings(request):
    return {
        'forum_settings': slimbb_settings,
        'DEBUG': settings.DEBUG,
    }
