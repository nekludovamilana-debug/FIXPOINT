from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
 
from main import views
 
urlpatterns = [
    # Админ-панель Django
    path('admin/', admin.site.urls),
 
    # Главная страница
    path('', views.home, name='home'),
 
    # Заявки
    path('request/', views.create_request, name='create_request'),
    path('success/', views.request_success, name='request_success'),
 
    # Регистрация и обычная авторизация клиентов
    path('accounts/register/', views.register, name='register'),
 
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login'
    ),
 
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
 
    # Отдельный вход мастера
    path(
        'master/login/',
        views.master_login,
        name='master_login'
    ),
 
    # Личный кабинет
    path('account/', views.account, name='account'),
 
    # Панель мастера
    path('master/', views.master_panel, name='master_panel'),
 
    # Подробности заявки
    path(
        'repair/<int:repair_id>/',
        views.repair_detail,
        name='repair_detail'
    ),
 
    # Склад запчастей
    path('master/stock/', views.stock_list, name='stock_list'),
 
    path(
        'master/stock/add/',
        views.add_stock_part,
        name='add_stock_part'
    ),
 
    path(
        'master/stock/edit/<int:part_id>/',
        views.edit_stock_part,
        name='edit_stock_part'
    ),
 
    path(
        'master/stock/delete/<int:part_id>/',
        views.delete_stock_part,
        name='delete_stock_part'
    ),
 
    # Отчёты и аналитика
    path(
        'master/reports/',
        views.reports,
        name='reports'
    ),
 
    # Экспорт Excel
    path(
        'master/reports/export/',
        views.export_reports,
        name='export_reports'
    ),
 
    # Экспорт PDF
    path(
        'master/reports/export/pdf/',
        views.export_reports_pdf,
        name='export_reports_pdf'
    ),
 
    # Управление сотрудниками
    path('master/employees/', views.employee_list, name='employee_list'),
    path('master/employees/add/', views.employee_add, name='employee_add'),

    # Управление услугами
    path(
        'master/services/',
        views.service_list,
        name='service_list'
    ),
 
    path(
        'master/services/add/',
        views.add_service,
        name='add_service'
    ),
 
    path(
        'master/services/edit/<int:service_id>/',
        views.edit_service,
        name='edit_service'
    ),
 
    path(
        'master/services/delete/<int:service_id>/',
        views.delete_service,
        name='delete_service'
    ),
]
 
# Отображение загруженных фотографий в режиме разработки
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
 