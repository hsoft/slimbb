from django.utils import translation, timezone
from django.conf import settings as global_settings
import pytz

class ForumMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            profile = request.user.forum_profile
            language = translation.get_language_from_request(request)

            if not profile.language:
                profile.language = language
                profile.save()

            if profile.language and profile.language != language:
                request.session['django_language'] = profile.language
                translation.activate(profile.language)
                request.LANGUAGE_CODE = translation.get_language()


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            profile = request.user.forum_profile
            try:
                timezone.activate(profile.time_zone)
            except pytz.UnknownTimeZoneError:
                profile.time_zone = global_settings.TIME_ZONE
                profile.save()
