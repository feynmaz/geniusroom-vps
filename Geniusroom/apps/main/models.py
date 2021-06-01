from enum import unique
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.constraints import Deferrable
from django.db.models.fields import TextField
from django.db.models.fields.related import ForeignKey
from .utilities import get_timestamp_path, send_new_comment_notification
from django.db.models.signals import post_save
from django.core import validators


class AdvUser(AbstractUser):
    # by default: ('username', 'email', 'first_name', 'last_name')
    is_activated = models.BooleanField(default=True, db_index=True, verbose_name='Прошел активацию')
    send_messages = models.BooleanField(default=True, verbose_name='Подписаться на уведомления')

    def delete(self, *args, **kwargs):
        for article in self.article_set.all():
            article.delete()
        super().delete(*args, **kwargs)

    class Meta(AbstractUser.Meta):
        pass


# использование прокси-моделей. Таблица в бд создается одна - только для Rubric
class Rubric(models.Model):
    name = models.CharField(max_length=20, db_index=True, unique=True, verbose_name='Название')
    order = models.SmallIntegerField(default=0, db_index=True, verbose_name='Порядок')
    super_rubric = models.ForeignKey('SuperRubric',
                                     on_delete=models.PROTECT, null=True, blank=True, verbose_name='Надрубрика')


class SuperRubricManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=True)


class SuperRubric(Rubric):
    objects = SuperRubricManager()

    def __str__(self):
        return self.name

    class Meta:
        proxy = True
        ordering = ('order',)
        verbose_name = 'Надрубрика'
        verbose_name_plural = 'Надрубрики'


class SubRubricManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=False)


class SubRubric(Rubric):
    objects = SubRubricManager()

    def __str__(self):
        return '%s - %s' % (self.super_rubric.name, self.name)

    class Meta:
        proxy = True
        ordering = ('super_rubric__order', 'order')
        verbose_name = 'Подрубрика'
        verbose_name_plural = 'Подрубрики'


class Article(models.Model):
    rubric = models.ForeignKey(SubRubric, on_delete=models.PROTECT, verbose_name='Подрубрика')
    title = models.CharField(max_length=40, verbose_name='Название статьи')
    content = models.TextField(verbose_name='Текст статьи')
    source = models.TextField(verbose_name='Источник')
    characters = models.TextField(verbose_name='Упоминаются',
                                  validators=[validators.RegexValidator
                                              (regex=r'(.+\s{1}\(\d{4}\-(?:\d{4}|\d{0})\)(\,\s)?)+')],
                                  error_messages={
                                      'invalid': 'Введите в формате: "<имя> (<год_рождения>-<год_смерти>)"'
                                  })
    image = models.ImageField(blank=True, upload_to=get_timestamp_path, verbose_name='Основная иллюстрация')
    author = ForeignKey(AdvUser, on_delete=models.CASCADE, verbose_name='Автор')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Показывать в списке')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Опубликовано')

    def delete(self, *args, **kwargs):
        for ai in self.additionalimage_set.all():
            ai.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-created_at']
        get_latest_by = 'created_at'


class AdditionalImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Статья')
    image = models.ImageField(upload_to=get_timestamp_path, verbose_name='Изображение')
    caption = models.CharField(max_length=200, null=True, blank=True, default="", verbose_name='Подпись')

    class Meta:
        verbose_name = 'Дополнительная иллюстрация'
        verbose_name_plural = 'Дополнительные иллюстрации'


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Статья')
    author = models.CharField(max_length=30, verbose_name='Имя автора')
    content = models.TextField(verbose_name='Содержание')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Показывать')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата публикации')

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']


def post_save_dispatcher(sender, **kwargs):
    author = kwargs['instance'].article.author
    if kwargs['created'] and author.send_messages:
        send_new_comment_notification(kwargs['instance'])


post_save.connect(post_save_dispatcher, sender=Comment)
