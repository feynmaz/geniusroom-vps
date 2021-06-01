from django.core import validators
from django import forms
from django.core.exceptions import ValidationError
from django.forms import fields, models
from django.contrib.auth import password_validation
from django.forms import inlineformset_factory
from captcha.fields import CaptchaField

from .apps import user_registered
from .models import AdvUser, Article, SuperRubric, SubRubric, AdditionalImage, Comment


class ChangeUserInfoForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Адрес электронной почты')

    class Meta:
        model = AdvUser
        fields = ('username', 'email', 'first_name', 'last_name', 'send_messages')


class RegisterUserForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Адрес электронной почты')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput,
                                help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label='Пароль (повторно)', widget=forms.PasswordInput,
                                help_text='Введите тот же самый пароль для проверки')

    def clean_password1(self):
        password1 = self.cleaned_data['password1']
        if password1:
            password_validation.validate_password(password1)
        return password1

    def clean(self):
        super().clean()
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 and password2 and password1 != password2:
            errors = {'password2': ValidationError(
                'Введенные пароли не совпадают', code='password_mismatch'
            )}
            raise ValidationError(errors)

    def save(self, commit=True):
        user = super().save(commit=True)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False
        user.is_activated = False
        if commit:
            user.save()
        user_registered.send(RegisterUserForm, instance=user)
        return user

    class Meta:
        model = AdvUser
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'send_messages')


class SubRubricForm(forms.ModelForm):
    super_rubric = forms.ModelChoiceField(queryset=SuperRubric.objects.all(),
                                          empty_label=None, label='Надрубрика', required=True)

    class Meta:
        model = SubRubric
        fields = '__all__'


class SearchForm(forms.Form):
    keyword = forms.CharField(required=False, max_length=20, label='')


class ArticleForm(forms.ModelForm):
    characters = forms.CharField(widget=forms.Textarea, label='Упоминаются',
                                 validators=[validators.RegexValidator
                                             (regex=r'(.+\s{1}\(\d{4}\-(?:\d{4}|\d{0})\)(\,\s)?)+')],
                                 error_messages={
                                     'invalid': 'Введите в формате: "<имя> (<год_рождения>-<год_смерти>)"'
                                 }
                                 )

    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'author': forms.HiddenInput
        }

    def clean_image(self):
        val = self.cleaned_data['image']

        if 'image' in self.changed_data:
            from PIL import Image
            img = Image.open(val.file)
            fmt = img.format.lower()

            w = img.size[0]
            h = img.size[1]

            if w > h:
                quotient = h / w
                resized = img.resize(size=(300, round(300 * quotient)))
            else:
                quotient = w / h
                resized = img.resize(size=(round(300 * quotient), 300))

            val.file = type(val.file)()
            resized.save(val.file, fmt)

        return val


AIFormSet = inlineformset_factory(Article, AdditionalImage, fields='__all__')


class UserCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {
            'article': forms.HiddenInput
        }


class GuestCommentForm(forms.ModelForm):
    captcha = CaptchaField(label='Введите текст с картинки', error_messages={
        'invalid': 'Неправильный текст'
    })

    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {
            'article': forms.HiddenInput
        }
