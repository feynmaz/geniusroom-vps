from django.urls import path, include
from .views import DeleteUserView, index, other_page, profile
from .views import GRLoginView, GRLogoutView
from .views import ChangeUserInfoView, GRPasswordChangeView
from .views import RegisterUserView, RegisterDoneView
from .views import user_activate, by_rubric, detail
from .views import profile_article_detail, profile_article_add, profile_article_delete, profile_article_change, detail_img

app_name = 'main'

urlpatterns = [
    path('', index, name='index'),

    path('<int:rubric_pk>/<int:pk>/<str:img>', detail_img, name='detail_img'),
    path('<int:rubric_pk>/<int:pk>/', detail, name='detail'),
    path('<int:pk>/', by_rubric, name='by_rubric'),


    path('accounts/', include([

        path('login/', GRLoginView.as_view(), name='login'),
        path('logout/', GRLogoutView.as_view(), name='logout'),

        path('profile/<int:pk>/', profile_article_detail, name='profile_article_detail'),
        path('profile/', profile, name='profile'),
        path('profile/change/<int:pk>/', profile_article_change, name='profile_article_change'),
        path('profile/delete/<int:pk>/', profile_article_delete, name='profile_article_delete'),
        path('profile/change', ChangeUserInfoView.as_view(), name='profile_change'),
        path('profile/delete/', DeleteUserView.as_view(), name='profile_delete'),
        path('profile/add', profile_article_add, name='profile_article_add'),

        path('password/change', GRPasswordChangeView.as_view(), name='password_change'),
        path('register/done', RegisterDoneView.as_view(), name='register_done'),
        path('register/activate/<str:sign>/', user_activate, name='register_activate'),
        path('register/', RegisterUserView.as_view(), name='register'),

    ])),

    path('<str:page>/', other_page, name='other'),
]