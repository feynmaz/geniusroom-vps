from django import template
from django.core import paginator
from django.db.models import query, Q
from django.forms import formsets
from django.http import HttpResponse, Http404, request
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.core.signing import BadSignature
from django.core.mail import send_mail
from django.contrib.auth import logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.generic.base import TemplateView
from django.http import FileResponse

from .models import AdvUser, Rubric, SubRubric, Article, Comment
from .forms import AIFormSet, ArticleForm, ChangeUserInfoForm, RegisterUserForm, SearchForm, UserCommentForm, GuestCommentForm
from .utilities import signer
from Geniusroom.settings import MEDIA_URL


def index(request):
    articles = Article.objects.filter(is_active=True)[:10]
    context = {'articles': articles}
    return render(request, template_name='main/index.html', context=context)


def other_page(request, page):
    try:
        template = 'main/' + page + '.html'
    except TemplateDoesNotExist:
        raise Http404

    return render(request, template_name=template)


class GRLoginView(LoginView):
    template_name = 'main/login.html'


@login_required
def profile(request):
    articles = Article.objects.filter(author=request.user.pk)
    context = {
        'articles': articles
    }
    return render(request, 'main/profile.html', context)


class GRLogoutView(LoginRequiredMixin, LogoutView):
    template_name = 'main/logout.html'


class ChangeUserInfoView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = AdvUser
    template_name = 'main/change_user_info.html'
    form_class = ChangeUserInfoForm
    success_url = reverse_lazy('main:profile')
    success_message = 'Данные пользователя изменены'

    def setup(self, request, *args, **kwargs):
        self.user_id = request.user.pk
        return super().setup(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)


# TODO: реализовать PasswordResetView (c. 305)
class GRPasswordChangeView(SuccessMessageMixin, LoginRequiredMixin, PasswordChangeView):
    template_name = 'main/password_change.html'
    success_message = 'Пароль пользователя изменен'
    success_url = reverse_lazy('main:profile')


class RegisterUserView(CreateView):
    model = AdvUser
    template_name = 'main/register_user.html'
    form_class = RegisterUserForm
    success_url = reverse_lazy('main:register_done')


class RegisterDoneView(TemplateView):
    template_name = 'main/register_done.html'


class DeleteUserView(LoginRequiredMixin, DeleteView):
    model = AdvUser
    template_name = 'main/delete_user.html'
    success_url = reverse_lazy('main:index')

    def setup(self, request, *args, **kwargs):
        self.user_id = request.user.pk
        return super().setup(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.add_message(request, messages.SUCCESS, 'Пользователь удален')
        return super().post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)


def user_activate(request, sign):
    try:
        username = signer.unsign(sign)
    except BadSignature:
        return render(request, 'main/bad_signature.html')

    user = get_object_or_404(AdvUser, username=username)

    if user.is_activated:
        template = 'main/user_is_activated.html'
    else:
        template = 'main/activation_done.html'
        user.is_active = True
        user.is_activated = True
        user.save()

    return render(request, template)


def by_rubric(request, pk):
    rubric = get_object_or_404(SubRubric, pk=pk)
    # articles = Article.objects.filter(is_active=True, rubric=pk)
    articles = Article.objects.raw("""
        select * 
        from main_article 
        where 1=1 
            and is_active = 1
            and rubric_id = %s
    """, [pk])

    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        q = Q(title__icontains=keyword) | Q(content__icontains=keyword)
        articles = articles.filter(q)
    else:
        keyword = ''

    form = SearchForm(initial={'keyword': keyword})

    paginator = Paginator(articles, 2)  # по 2 на страницу
    if 'page' in request.GET:
        page_num = request.GET['page']
    else:
        page_num = 1

    page = paginator.get_page(page_num)
    context = {
        'rubric': rubric,
        'page': page,
        'articles': articles,
        'form': form,
    }
    return render(request, 'main/by_rubric.html', context)


def detail(request, rubric_pk, pk):
    article = get_object_or_404(Article, pk=pk)
    ais = article.additionalimage_set.all()
    comments = Comment.objects.filter(article=pk, is_active=True)
    initial = {
        'article': article.pk
    }
    if request.user.is_authenticated:
        initial['author'] = request.user.username
        form_class = UserCommentForm
    else:
        form_class = GuestCommentForm

    form = form_class(initial=initial)
    if request.method == 'POST':
        c_form = form_class(request.POST)
        if c_form.is_valid():
            c_form.save()
            messages.add_message(request, messages.SUCCESS,
                                 'Комментарий добавлен')
        else:
            form = c_form
            messages.add_message(request, messages.WARNING,
                                 'Комментарий не добавлен')

    context = {
        'article': article,
        'ais': ais,
        'comments': comments,
        'form': form,
    }
    return render(request, 'main/detail.html', context)


def profile_article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    subrubric = get_object_or_404(SubRubric, pk=article.rubric.pk)
    ais = article.additionalimage_set.all()
    comments = Comment.objects.filter(article=pk, is_active=True)
    context = {
        'article': article,
        'ais': ais,
        'subrubric': subrubric,
        'comments': comments,
    }

    return render(request, 'main/author_detail.html', context)


@login_required
def profile_article_add(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        formset = AIFormSet()
        if form.is_valid():
            article = form.save()
            formset = AIFormSet(request.POST, request.FILES, instance=article)

            if formset.is_valid():
                formset.save()
                messages.add_message(request, messages.SUCCESS, 'Статья добавлена')
                return redirect('main:profile')

    else:
        form = ArticleForm(initial={
            'author': request.user.pk
        })
        formset = AIFormSet()

    context = {
        'form': form,
        'formset': formset,
    }

    return render(request, 'main/profile_article_add.html', context)


@login_required
def profile_article_change(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save()
            formset = AIFormSet(request.POST, request.FILES, instance=article)
            if formset.is_valid():
                formset.save()
                messages.add_message(request, messages.SUCCESS,
                                     'Статья исправлена')
                return redirect('main:profile')
    else:
        form = ArticleForm(instance=article)
        formset = AIFormSet(instance=article)
    context = {
        'form': form,
        'formset': formset
    }
    return render(request, 'main/profile_article_change.html', context)


@login_required
def profile_article_delete(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        article.delete()
        messages.add_message(request, messages.SUCCESS,
                             'Статья удалена')
        return redirect('main:profile')
    else:
        context = {
            'article': article
        }
        return render(request, 'main/profile_article_delete.html', context)


def detail_img(request, rubric_pk, pk, img):
    path = MEDIA_URL + img
    return FileResponse(open(path, 'rb'))