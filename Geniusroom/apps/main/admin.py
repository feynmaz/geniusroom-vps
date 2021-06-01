from django.contrib import admin
from django.db.models import query

from .models import AdvUser, SubRubric, SuperRubric
from .models import Article, AdditionalImage, Comment
from .utilities import send_activation_notification, send_new_comment_notification
from .forms import SubRubricForm

import datetime


def send_activation_notification(modeladmin, request, queryset):
    for rec in queryset:
        if not rec.is_activated:
            send_activation_notification(rec)

    modeladmin.message_user(request, 'Письма с требованиями отправлены')


send_activation_notification.short_description = 'Отправка писем с требованиям активации'


class NonactivatedFilter(admin.SimpleListFilter):
    title = 'Прошли активацию?'
    parameter_name = 'actstate'

    def lookups(self, request, model_admin):
        return (
            ('activated', 'Прошли'),
            ('threedays', 'Не прошли в течение более 3-х дней'),
            ('week', 'Не прошли в течение недели'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'activated':
            return queryset.filter(is_active=True, is_activated=True)
        elif val == 'threedays':
            d = datetime.date.today() - datetime.timedelta(days=3)
            return queryset.filter(is_active=False, is_activated=False, date_joined__date__lt=d)


class AdvUserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_activated', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = (NonactivatedFilter,)
    fields = (
        ('username', 'email'),
        ('first_name', 'last_name'),
        ('send_messages', 'is_active', 'is_activated'),
        ('is_staff', 'is_superuser'),
        'groups',
        'user_permisions',
        ('last_login', 'date_joined')
    )
    readonly_fields = ('last_login', 'date_joined')
    actions = (send_activation_notification,)


admin.site.register(AdvUser, AdvUserAdmin)


class SubRubricAdmin(admin.ModelAdmin):
    form = SubRubricForm


admin.site.register(SubRubric, SubRubricAdmin)


class SubRubricInline(admin.TabularInline):
    model = SubRubric
    fk_name = 'super_rubric'


class SuperRubricAdmin(admin.ModelAdmin):
    exclude = ('super_rubric',)
    inlines = (SubRubricInline,)


admin.site.register(SuperRubric, SuperRubricAdmin)


class AdditionalImageInline(admin.TabularInline):
    model = AdditionalImage


class ArticleAdmin(admin.ModelAdmin):
    list_display = ('rubric', 'title', 'content', 'characters', 'source', 'author', 'created_at')
    fields = (
        ('rubric', 'author'),
        'title', 'content', 'characters', 'source', 'image', 'is_active'
    )
    inlines = (AdditionalImageInline,)
    # actions = (send_new_comment_notification,)


admin.site.register(Article, ArticleAdmin)


class CommentAdmin(admin.ModelAdmin):
    model = Comment


admin.site.register(Comment, CommentAdmin)