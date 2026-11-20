from django.urls import path
from . import views

urlpatterns = [
    path('', views.supplier_list_view, name='supplier_list'),
    path('add/', views.supplier_create_view, name='supplier_create'),
    path('<int:pk>/', views.supplier_detail_view, name='supplier_detail'),
    path('<int:pk>/edit/', views.supplier_update_view, name='supplier_update'),
    path('<int:pk>/delete/', views.supplier_delete_view, name='supplier_delete'),
]
