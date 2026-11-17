from decimal import Decimal
from datetime import timedelta
from io import BytesIO
import os
 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
 
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
 
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
 
from .forms import RepairRequestForm, RepairCommentForm, RepairPartUsageForm, RepairLaborCostForm
from .models import Service, RepairRequest, StockPart, RepairStatusHistory, RepairPartUsage
from .registration_form import RegistrationForm
from .stock_form import StockPartForm
from .service_form import ServiceForm
from .employee_form import EmployeeCreationForm
 

def register_pdf_fonts():
    font_paths = [
        (
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/arialbd.ttf'
        ),
        (
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ),
    ]
 
    for regular_path, bold_path in font_paths:
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(
                TTFont('RepairFont', regular_path)
            )
 
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(
                    TTFont('RepairFont-Bold', bold_path)
                )
            else:
                pdfmetrics.registerFont(
                    TTFont('RepairFont-Bold', regular_path)
                )
 
            return
 
    raise FileNotFoundError(
        'Не найден шрифт Arial или DejaVuSans для создания PDF.'
    )
 
# Общая функция фильтрации отчётов по датам
def filter_report_repairs(request):
    repairs = RepairRequest.objects.all()
 
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
 
    parsed_start = parse_date(start_date) if start_date else None
    parsed_end = parse_date(end_date) if end_date else None
 
    if start_date and not parsed_start:
        start_date = ''
 
    if end_date and not parsed_end:
        end_date = ''
 
    if parsed_start and parsed_end and parsed_start > parsed_end:
        parsed_start = None
        parsed_end = None
        start_date = ''
        end_date = ''
 
    if parsed_start:
        repairs = repairs.filter(
            created_at__date__gte=parsed_start
        )
 
    if parsed_end:
        repairs = repairs.filter(
            created_at__date__lte=parsed_end
        )
 
    return repairs, parsed_start, parsed_end
 
# Главная страница
def home(request):
    services = Service.objects.filter(is_active=True)
    categories = []
 
    for category_code, category_name in Service.CATEGORY_CHOICES:
        category_services = services.filter(category=category_code)
 
        if category_services.exists():
            categories.append({
                'name': category_name,
                'services': category_services
            })
 
    return render(request, 'main/index.html', {
        'categories': categories
    })
 
# Создание заявки с фотографией
@login_required(login_url='login')
def create_request(request):
    if request.method == 'POST':
        form = RepairRequestForm(
            request.POST,
            request.FILES
        )
 
        if form.is_valid():
            repair_request = form.save(commit=False)
 
            if request.user.is_authenticated:
                repair_request.user = request.user
 
            if repair_request.service:
                repair_request.service_price = repair_request.service.price
 
            repair_request.save()
            RepairStatusHistory.objects.create(
                repair=repair_request,
                old_status='',
                new_status=repair_request.status,
                comment='Заявка создана',
                changed_by=request.user,
            )
 
            return redirect('request_success')
 
    else:
        form = RepairRequestForm()
 
    return render(request, 'main/request_form.html', {
        'form': form
    })
 
# Успешная отправка заявки
def request_success(request):
    return render(request, 'main/request_success.html')
 
# Регистрация клиента
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
 
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
 
    else:
        form = RegistrationForm()
 
    return render(request, 'registration/register.html', {
        'form': form
    })
 
# Отдельный вход мастера
def master_login(request):
    error = ''
 
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
 
        user = authenticate(
            request,
            username=username,
            password=password
        )
 
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('master_panel')
 
        error = 'Неверный логин, пароль или недостаточно прав.'
 
    return render(request, 'main/master_login.html', {
        'error': error
    })
 
# Личный кабинет клиента
@login_required
def account(request):
    repairs = request.user.repair_requests.all().order_by('-created_at')
 
    return render(request, 'main/account.html', {
        'repairs': repairs
    })
 
# Панель мастера: суперпользователь распределяет заявки, мастер видит назначенные ему.
@staff_member_required(login_url='master_login')
def master_panel(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'status')
        repair_id = request.POST.get('repair_id')

        if action == 'assign':
            if not request.user.is_superuser:
                return HttpResponseForbidden('Назначать мастеров может только администратор.')
            repair = get_object_or_404(RepairRequest, id=repair_id)
            master_id = request.POST.get('assigned_master', '').strip()
            if master_id:
                master = get_object_or_404(
                    get_user_model(), id=master_id, is_staff=True
                )
                repair.assigned_master = master
            else:
                repair.assigned_master = None
            repair.save(update_fields=['assigned_master'])
            return redirect('master_panel')

        repair_queryset = RepairRequest.objects.all()
        if not request.user.is_superuser:
            repair_queryset = repair_queryset.filter(assigned_master=request.user)
        repair = get_object_or_404(repair_queryset, id=repair_id)

        if action == 'status':
            new_status = request.POST.get('status')
            valid_statuses = [choice[0] for choice in RepairRequest.STATUS_CHOICES]
            if new_status in valid_statuses and new_status != repair.status:
                old_status = repair.status
                repair.status = new_status
                repair.save(update_fields=['status'])
                RepairStatusHistory.objects.create(
                    repair=repair,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                )
        return redirect('master_panel')

    all_repairs = RepairRequest.objects.select_related(
        'user', 'service', 'assigned_master'
    ).all().order_by('-created_at')

    if not request.user.is_superuser:
        all_repairs = all_repairs.filter(assigned_master=request.user)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        all_repairs = all_repairs.filter(
            Q(customer_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(device__icontains=search_query) |
            Q(problem__icontains=search_query)
        )

    selected_status = request.GET.get('status', '')
    valid_statuses = [choice[0] for choice in RepairRequest.STATUS_CHOICES]
    if selected_status in valid_statuses:
        all_repairs = all_repairs.filter(status=selected_status)
    else:
        selected_status = ''

    selected_date = request.GET.get('date', '')
    if selected_date:
        parsed_selected_date = parse_date(selected_date)
        if parsed_selected_date:
            all_repairs = all_repairs.filter(created_at__date=parsed_selected_date)
        else:
            selected_date = ''

    visible_repairs = RepairRequest.objects.all()
    if not request.user.is_superuser:
        visible_repairs = visible_repairs.filter(assigned_master=request.user)

    statistics = {
        'total': visible_repairs.count(),
        'new': visible_repairs.filter(status='new').count(),
        'diagnostics': visible_repairs.filter(status='diagnostics').count(),
        'in_progress': visible_repairs.filter(status='in_progress').count(),
        'ready': visible_repairs.filter(status='ready').count(),
        'completed': visible_repairs.filter(status='completed').count(),
        'issued': visible_repairs.filter(status='issued').count(),
        'unassigned': RepairRequest.objects.filter(assigned_master__isnull=True).count()
            if request.user.is_superuser else 0,
    }

    paginator = Paginator(all_repairs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    masters = get_user_model().objects.filter(is_staff=True, is_active=True).order_by('username')

    return render(request, 'main/master_panel.html', {
        'repairs': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'status_choices': RepairRequest.STATUS_CHOICES,
        'statistics': statistics,
        'search_query': search_query,
        'selected_status': selected_status,
        'selected_date': selected_date,
        'masters': masters,
        'can_assign': request.user.is_superuser,
    })


# Карточка заявки: комментарии, история и списание запчастей.
@login_required
def repair_detail(request, repair_id):
    repair = get_object_or_404(
        RepairRequest.objects.select_related('assigned_master', 'service', 'user'),
        id=repair_id
    )
    is_admin = request.user.is_superuser
    is_assigned_master = request.user.is_staff and repair.assigned_master_id == request.user.id
    is_owner = repair.user_id == request.user.id

    if not (is_admin or is_assigned_master or (not request.user.is_staff and is_owner)):
        return redirect('account')

    comment_form = RepairCommentForm()
    part_form = RepairPartUsageForm()
    labor_form = RepairLaborCostForm(initial={'labor_cost': repair.labor_cost})

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'comment':
            comment_form = RepairCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.repair = repair
                comment.author = request.user
                comment.save()
                return redirect('repair_detail', repair_id=repair.id)

        elif action == 'labor_cost':
            if not (is_admin or is_assigned_master):
                return HttpResponseForbidden('Недостаточно прав для изменения стоимости работ.')
            labor_form = RepairLaborCostForm(request.POST)
            if labor_form.is_valid():
                repair.labor_cost = labor_form.cleaned_data['labor_cost']
                repair.save(update_fields=['labor_cost'])
                return redirect('repair_detail', repair_id=repair.id)

        elif action == 'add_part':
            if not (is_admin or is_assigned_master):
                return HttpResponseForbidden('Недостаточно прав для списания запчастей.')
            part_form = RepairPartUsageForm(request.POST)
            if part_form.is_valid():
                part = part_form.cleaned_data['part']
                quantity = part_form.cleaned_data['quantity']
                with transaction.atomic():
                    locked_part = StockPart.objects.select_for_update().get(pk=part.pk)
                    if locked_part.quantity < quantity:
                        part_form.add_error(
                            'quantity',
                            f'На складе доступно только {locked_part.quantity} шт.'
                        )
                    else:
                        RepairPartUsage.objects.create(
                            repair=repair,
                            part=locked_part,
                            quantity=quantity,
                            unit_price=locked_part.price,
                            used_by=request.user,
                        )
                        locked_part.quantity -= quantity
                        locked_part.save(update_fields=['quantity'])
                        return redirect('repair_detail', repair_id=repair.id)

    return render(request, 'main/repair_detail.html', {
        'repair': repair,
        'comment_form': comment_form,
        'part_form': part_form,
        'labor_form': labor_form,
        'can_manage': is_admin or is_assigned_master,
        'status_history': repair.status_history.select_related('changed_by').all(),
        'comments': repair.comments.select_related('author').all(),
        'part_usages': repair.part_usages.select_related('part', 'used_by').all(),
    })

# Склад запчастей
@staff_member_required(login_url='master_login')
def stock_list(request):
    parts = StockPart.objects.all().order_by('name')
 
    total_types = parts.count()
    total_quantity = sum(part.quantity for part in parts)
 
    low_stock = parts.filter(
        quantity__lte=models.F('min_quantity')
    ).count()
 
    total_value = sum(
        (part.price * part.quantity for part in parts),
        Decimal('0.00')
    )
 
    stock_statistics = {
        'total_types': total_types,
        'total_quantity': total_quantity,
        'low_stock': low_stock,
        'total_value': total_value,
    }
 
    return render(request, 'main/stock_list.html', {
        'parts': parts,
        'stock_statistics': stock_statistics,
    })
 
# Добавление запчасти
@staff_member_required(login_url='master_login')
def add_stock_part(request):
    if request.method == 'POST':
        form = StockPartForm(request.POST)
 
        if form.is_valid():
            form.save()
            return redirect('stock_list')
 
    else:
        form = StockPartForm()
 
    return render(request, 'main/stock_form.html', {
        'form': form
    })
 
# Редактирование запчасти
@staff_member_required(login_url='master_login')
def edit_stock_part(request, part_id):
    part = get_object_or_404(StockPart, id=part_id)
 
    if request.method == 'POST':
        form = StockPartForm(request.POST, instance=part)
 
        if form.is_valid():
            form.save()
            return redirect('stock_list')
 
    else:
        form = StockPartForm(instance=part)
 
    return render(request, 'main/stock_form.html', {
        'form': form,
        'editing': True
    })
 
# Удаление запчасти
@staff_member_required(login_url='master_login')
@require_POST
def delete_stock_part(request, part_id):
    part = get_object_or_404(StockPart, id=part_id)
    part.delete()
 
    return redirect('stock_list')
 
# Список услуг
@staff_member_required(login_url='master_login')
def service_list(request):
    services = Service.objects.all().order_by('category', 'name')
 
    return render(request, 'main/service_list.html', {
        'services': services
    })
 
# Добавление услуги
@staff_member_required(login_url='master_login')
def add_service(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
 
        if form.is_valid():
            form.save()
            return redirect('service_list')
 
    else:
        form = ServiceForm()
 
    return render(request, 'main/service_form.html', {
        'form': form,
        'editing': False
    })
 
# Редактирование услуги
@staff_member_required(login_url='master_login')
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
 
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
 
        if form.is_valid():
            form.save()
            return redirect('service_list')
 
    else:
        form = ServiceForm(instance=service)
 
    return render(request, 'main/service_form.html', {
        'form': form,
        'editing': True
    })
 
# Удаление услуги
@staff_member_required(login_url='master_login')
@require_POST
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()
 
    return redirect('service_list')
 
# Отчёты и аналитика с фильтрацией по датам
@staff_member_required(login_url='master_login')
def reports(request):
    repairs, parsed_start, parsed_end = filter_report_repairs(request)
 
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
 
    date_error = ''
 
    if start_date and not parsed_start:
        if not parse_date(start_date):
            date_error = 'Некорректная дата начала.'
            start_date = ''
 
    if end_date and not parsed_end:
        if not parse_date(end_date):
            date_error = 'Некорректная дата окончания.'
            end_date = ''
 
    if parsed_start and parsed_end and parsed_start > parsed_end:
        date_error = 'Дата начала не может быть позже даты окончания.'
        start_date = ''
        end_date = ''
 
    total_repairs = repairs.count()
 
    # Распределение заявок по статусам
    status_statistics = []
 
    for status_code, status_name in RepairRequest.STATUS_CHOICES:
        status_statistics.append({
            'name': status_name,
            'count': repairs.filter(status=status_code).count()
        })
 
    # Заявки и выручка по месяцам
    if parsed_start or parsed_end:
        monthly_repairs = repairs
    else:
        six_months_ago = timezone.now() - timedelta(days=180)
 
        monthly_repairs = repairs.filter(
            created_at__gte=six_months_ago
        )
 
    monthly_statistics = list(
        monthly_repairs
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            revenue=Sum('service_price') + Sum('labor_cost')
        )
        .order_by('month')
    )
 
    # Популярность услуг и выручка
    popular_services = Service.objects.annotate(
        request_count=Count(
            'repair_requests',
            filter=Q(repair_requests__in=repairs)
        ),
        revenue=Sum(
            'repair_requests__service_price',
            filter=Q(repair_requests__in=repairs)
        )
    ).order_by('-request_count', 'name')
 
    # Общая сумма стоимости заявок
    total_revenue = repairs.aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    # Выручка по завершённым и выданным заявкам
    completed_revenue = repairs.filter(
        status__in=['completed', 'issued']
    ).aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    fault_statistics = list(
        repairs.values('device').annotate(total=Count('id')).order_by('-total')[:8]
    )
    master_statistics = list(
        get_user_model().objects.filter(is_staff=True, assigned_repairs__in=repairs)
        .annotate(total=Count('assigned_repairs', filter=Q(assigned_repairs__in=repairs)))
        .values('username', 'total').order_by('-total')[:8]
    )

    return render(request, 'main/reports.html', {
        'fault_statistics': fault_statistics,
        'master_statistics': master_statistics,
        'total_repairs': total_repairs,
        'status_statistics': status_statistics,
        'monthly_statistics': monthly_statistics,
        'popular_services': popular_services,
        'total_revenue': total_revenue,
        'completed_revenue': completed_revenue,
        'start_date': start_date,
        'end_date': end_date,
        'date_error': date_error,
    })
 
# Экспорт отчётов в Excel
@staff_member_required(login_url='master_login')
def export_reports(request):
    repairs, parsed_start, parsed_end = filter_report_repairs(request)
 
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Отчёт'
 
    # Заголовок
    sheet.merge_cells('A1:E1')
    sheet['A1'] = 'Отчёт ремонтной мастерской'
    sheet['A1'].font = Font(
        size=16,
        bold=True,
        color='FFFFFF'
    )
    sheet['A1'].fill = PatternFill(
        start_color='263A5B',
        end_color='263A5B',
        fill_type='solid'
    )
    sheet['A1'].alignment = Alignment(
        horizontal='center',
        vertical='center'
    )
    sheet.row_dimensions[1].height = 30
 
    # Информация о периоде
    if parsed_start or parsed_end:
        period_start = parsed_start.strftime('%d.%m.%Y') if parsed_start else 'За всё время'
        period_end = parsed_end.strftime('%d.%m.%Y') if parsed_end else 'По настоящее время'
        sheet['A2'] = f'Период: {period_start} — {period_end}'
 
    # Общая статистика
    total_repairs = repairs.count()
 
    total_revenue = repairs.aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    completed_revenue = repairs.filter(
        status__in=['completed', 'issued']
    ).aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    sheet.append([])
    sheet.append(['Показатель', 'Значение'])
    sheet.append(['Всего заявок', total_repairs])
    sheet.append(['Общая выручка', float(total_revenue)])
    sheet.append([
        'Выручка по завершённым заказам',
        float(completed_revenue)
    ])
 
    # Статистика по статусам
    sheet.append([])
    sheet.append(['Статус', 'Количество заявок'])
 
    for status_code, status_name in RepairRequest.STATUS_CHOICES:
        count = repairs.filter(status=status_code).count()
        sheet.append([status_name, count])
 
    # Статистика по месяцам
    sheet.append([])
    sheet.append([
        'Месяц',
        'Количество заявок',
        'Выручка'
    ])
 
    monthly_statistics = (
        repairs
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            revenue=Sum('service_price') + Sum('labor_cost')
        )
        .order_by('month')
    )
 
    for item in monthly_statistics:
        sheet.append([
            item['month'].strftime('%m.%Y'),
            item['total'],
            float(item['revenue'] or 0)
        ])
 
    # Популярность услуг
    popular_services = (
        Service.objects
        .annotate(
            request_count=Count(
                'repair_requests',
                filter=Q(repair_requests__in=repairs)
            ),
            revenue=Sum(
                'repair_requests__service_price',
                filter=Q(repair_requests__in=repairs)
            )
        )
        .order_by('-request_count', 'name')
    )
 
    sheet.append([])
    sheet.append([
        'Услуга',
        'Категория',
        'Цена',
        'Количество заявок',
        'Выручка'
    ])
 
    for service in popular_services:
        sheet.append([
            service.name,
            service.get_category_display(),
            float(service.price),
            service.request_count,
            float(service.revenue or 0)
        ])
 
    # Оформление заголовков таблиц
    header_names = [
        'Показатель',
        'Статус',
        'Месяц',
        'Услуга'
    ]
 
    for row in sheet.iter_rows():
        if row[0].value in header_names:
            for cell in row:
                cell.font = Font(
                    bold=True,
                    color='FFFFFF'
                )
                cell.fill = PatternFill(
                    start_color='4472C4',
                    end_color='4472C4',
                    fill_type='solid'
                )
                cell.alignment = Alignment(
                    horizontal='center',
                    vertical='center'
                )
 
    # Денежный формат
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value in [
                'Общая выручка',
                'Выручка по завершённым заказам'
            ]:
                value_cell = sheet.cell(
                    row=cell.row,
                    column=2
                )
                value_cell.number_format = '#,##0.00 "₽"'
 
    for row in sheet.iter_rows():
        if row[0].value == 'Месяц':
            for data_row in range(row[0].row + 1, sheet.max_row + 1):
                if sheet.cell(data_row, 1).value is None:
                    break
                sheet.cell(data_row, 3).number_format = '#,##0.00 "₽"'
 
    for row in sheet.iter_rows():
        if row[0].value == 'Услуга':
            for data_row in range(row[0].row + 1, sheet.max_row + 1):
                if sheet.cell(data_row, 1).value is None:
                    break
                sheet.cell(data_row, 3).number_format = '#,##0.00 "₽"'
                sheet.cell(data_row, 5).number_format = '#,##0.00 "₽"'
 
    # Автоматическая ширина столбцов
    for column in sheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
 
        for cell in column:
            if cell.value is not None:
                max_length = max(
                    max_length,
                    len(str(cell.value))
                )
 
        sheet.column_dimensions[column_letter].width = min(
            max_length + 3,
            40
        )
 
    sheet.freeze_panes = 'A3'
 
    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )
 
    response['Content-Disposition'] = (
        'attachment; filename="repair_workshop_report.xlsx"'
    )
 
    workbook.save(response)
 
    return response
 
# Экспорт отчётов в PDF
@staff_member_required(login_url='master_login')
def export_reports_pdf(request):
    register_pdf_fonts()
 
    buffer = BytesIO()
 
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
 
    styles = getSampleStyleSheet()
 
    title_style = ParagraphStyle(
        'RussianTitle',
        parent=styles['Title'],
        fontName='RepairFont-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#263A5B'),
        spaceAfter=15
    )
 
    heading_style = ParagraphStyle(
        'RussianHeading',
        parent=styles['Heading2'],
        fontName='RepairFont-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#263A5B'),
        spaceBefore=12,
        spaceAfter=8
    )
 
    normal_style = ParagraphStyle(
        'RussianNormal',
        parent=styles['Normal'],
        fontName='RepairFont',
        fontSize=9,
        leading=12
    )
 
    story = []
 
    story.append(Paragraph(
        'Отчёт ремонтной мастерской',
        title_style
    ))
 
    story.append(Paragraph(
        f'Дата формирования: {timezone.localtime().strftime("%d.%m.%Y %H:%M")}',
        normal_style
    ))
 
    repairs, parsed_start, parsed_end = filter_report_repairs(request)
 
    if parsed_start or parsed_end:
        period_start = parsed_start.strftime('%d.%m.%Y') if parsed_start else 'За всё время'
        period_end = parsed_end.strftime('%d.%m.%Y') if parsed_end else 'По настоящее время'
 
        story.append(Paragraph(
            f'Период отчёта: {period_start} — {period_end}',
            normal_style
        ))
 
    story.append(Spacer(1, 15))
 
    total_repairs = repairs.count()
 
    total_revenue = repairs.aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    completed_revenue = repairs.filter(
        status__in=['completed', 'issued']
    ).aggregate(
        total=Sum('service_price') + Sum('labor_cost')
    )['total'] or Decimal('0.00')
 
    story.append(Paragraph(
        'Общая статистика',
        heading_style
    ))
 
    summary_data = [
        ['Показатель', 'Значение'],
        ['Всего заявок', str(total_repairs)],
        ['Общая выручка', f'{total_revenue:.2f} руб.'],
        [
            'Выручка по завершённым и выданным заявкам',
            f'{completed_revenue:.2f} руб.'
        ],
    ]
 
    summary_table = Table(
        summary_data,
        colWidths=[350, 250]
    )
 
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263A5B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'RepairFont'),
        ('FONTNAME', (0, 0), (-1, 0), 'RepairFont-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F2F5F9')),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
 
    story.append(summary_table)
 
    story.append(Paragraph(
        'Распределение заявок по статусам',
        heading_style
    ))
 
    status_data = [
        ['Статус', 'Количество заявок']
    ]
 
    for status_code, status_name in RepairRequest.STATUS_CHOICES:
        count = repairs.filter(status=status_code).count()
        status_data.append([status_name, str(count)])
 
    status_table = Table(
        status_data,
        colWidths=[300, 300]
    )
 
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'RepairFont'),
        ('FONTNAME', (0, 0), (-1, 0), 'RepairFont-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
 
    story.append(status_table)
 
    story.append(Paragraph(
        'Динамика заявок по месяцам',
        heading_style
    ))
 
    if parsed_start or parsed_end:
        monthly_repairs = repairs
    else:
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_repairs = repairs.filter(
            created_at__gte=six_months_ago
        )
 
    monthly_statistics = (
        monthly_repairs
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            revenue=Sum('service_price') + Sum('labor_cost')
        )
        .order_by('month')
    )
 
    monthly_data = [
        ['Месяц', 'Количество заявок', 'Выручка']
    ]
 
    for item in monthly_statistics:
        monthly_data.append([
            item['month'].strftime('%m.%Y'),
            str(item['total']),
            f'{(item["revenue"] or Decimal("0.00")):.2f} руб.'
        ])
 
    if len(monthly_data) == 1:
        monthly_data.append([
            'Нет данных',
            '0',
            '0.00 руб.'
        ])
 
    monthly_table = Table(
        monthly_data,
        colWidths=[200, 200, 200]
    )
 
    monthly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'RepairFont'),
        ('FONTNAME', (0, 0), (-1, 0), 'RepairFont-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
 
    story.append(monthly_table)
 
    story.append(Paragraph(
        'Популярность услуг и выручка',
        heading_style
    ))
 
    popular_services = (
        Service.objects
        .annotate(
            request_count=Count(
                'repair_requests',
                filter=Q(repair_requests__in=repairs)
            ),
            revenue=Sum(
                'repair_requests__service_price',
                filter=Q(repair_requests__in=repairs)
            )
        )
        .order_by('-request_count', 'name')
    )
 
    services_data = [[
        'Услуга',
        'Категория',
        'Цена',
        'Количество заявок',
        'Выручка'
    ]]
 
    for service in popular_services:
        services_data.append([
            Paragraph(str(service.name), normal_style),
            Paragraph(str(service.get_category_display()), normal_style),
            f'{service.price:.2f} руб.',
            str(service.request_count),
            f'{(service.revenue or Decimal("0.00")):.2f} руб.'
        ])
 
    if len(services_data) == 1:
        services_data.append([
            'Нет данных',
            '-',
            '-',
            '0',
            '0.00 руб.'
        ])
 
    services_table = Table(
        services_data,
        colWidths=[190, 140, 100, 130, 130],
        repeatRows=1
    )
 
    services_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263A5B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'RepairFont'),
        ('FONTNAME', (0, 0), (-1, 0), 'RepairFont-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F2F5F9')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
 
    story.append(services_table)
 
    document.build(story)
 
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(
        pdf,
        content_type='application/pdf'
    )
 
    response['Content-Disposition'] = (
        'attachment; filename="repair_workshop_report.pdf"'
    )
 
    return response
 

# Управление сотрудниками доступно только суперпользователю.
@staff_member_required(login_url='master_login')
def employee_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Управлять сотрудниками может только администратор.')
    User = get_user_model()
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        employee = get_object_or_404(User, pk=employee_id, is_staff=True)
        if employee.pk != request.user.pk and not employee.is_superuser:
            employee.is_active = not employee.is_active
            employee.save(update_fields=['is_active'])
        return redirect('employee_list')
    employees = User.objects.filter(is_staff=True).order_by('username')
    return render(request, 'main/employee_list.html', {'employees': employees})


@staff_member_required(login_url='master_login')
def employee_add(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Создавать сотрудников может только администратор.')
    form = EmployeeCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('employee_list')
    return render(request, 'main/employee_form.html', {'form': form})
