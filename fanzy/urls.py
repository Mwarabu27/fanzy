from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from core.views import FanzyLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', FanzyLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('core.urls')),
]
