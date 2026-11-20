from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/add/', views.staff_create_view, name='staff_create'),
    path('staff/<int:pk>/toggle/', views.staff_toggle_active_view, name='staff_toggle'),
    path('staff/<int:pk>/delete/', views.staff_delete_view, name='staff_delete'),
]
