import pydash
from core import get_env
from django.conf import settings
from linebot.models import SourceGroup, SourceRoom

BOT_NAME = get_env('BOT_NAME', settings.APP_NAME)
BOT_ID = get_env('BOT_ID', pydash.slugify(BOT_NAME, '_'))
BOT_CHANNEL_SECRET = get_env('BOT_CHANNEL_SECRET')
BOT_CHANNEL_ACCESS_TOKEN = get_env('BOT_CHANNEL_ACCESS_TOKEN')


def get_cache_prefix(event):
    prefix = 'LineBot-%s' % BOT_ID

    return prefix + '-' + get_player_identity(event)


def get_player_identity(event):
    if isinstance(event.source, SourceGroup):
        return 'g-' + event.source.group_id
    elif isinstance(event.source, SourceRoom):
        return 'r-' + event.source.room_id

    return 'u-' + event.source.user_id


def get_participant_identity(event):
    if isinstance(event.source, SourceGroup):
        return event.source.user_id
    elif isinstance(event.source, SourceRoom):
        return event.source.user_id

    return event.source.user_id
