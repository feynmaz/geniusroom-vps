from django.apps import AppConfig
from django.dispatch import Signal

from .utilities import send_activation_notification, send_new_comment_notification


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'Geniusroom.apps.main'
    verbose_name = 'Великие музыканты'


def user_registered_dispatcher(sender, **kwargs):
    send_activation_notification(kwargs['instance'])


user_registered = Signal(providing_args=['instance'])
user_registered.connect(user_registered_dispatcher)
