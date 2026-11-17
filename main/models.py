from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class RepairRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Принята'),
        ('diagnostics', 'В диагностике'),
        ('in_progress', 'В ремонте'),
        ('ready', 'Готова к выдаче'),
        ('completed', 'Завершена'),
        ('issued', 'Выдана'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Аккаунт клиента',
        related_name='repair_requests'
    )
    assigned_master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Назначенный мастер',
        related_name='assigned_repairs',
        limit_choices_to={'is_staff': True}
    )
    service = models.ForeignKey(
        'Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Выбранная услуга',
        related_name='repair_requests'
    )
    service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Стоимость услуги на момент заявки'
    )
    labor_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)],
        verbose_name='Стоимость работ мастера'
    )
    customer_name = models.CharField(max_length=100, verbose_name='Имя клиента')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    device = models.CharField(max_length=100, verbose_name='Устройство')
    problem = models.TextField(verbose_name='Описание неисправности')
    photo = models.ImageField(
        upload_to='repair_photos/',
        null=True,
        blank=True,
        verbose_name='Фотография неисправности'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f'{self.device} — {self.customer_name}'

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'


class Service(models.Model):
    CATEGORY_CHOICES = [
        ('computer', 'Компьютеры'),
        ('laptop', 'Ноутбуки'),
        ('smartphone', 'Смартфоны'),
        ('other', 'Другая техника'),
    ]
    name = models.CharField(max_length=100, verbose_name='Название услуги')
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='other',
        verbose_name='Категория'
    )
    description = models.TextField(verbose_name='Описание услуги')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Стоимость')
    duration = models.CharField(max_length=100, verbose_name='Срок выполнения')
    is_active = models.BooleanField(default=True, verbose_name='Услуга доступна')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'


class StockPart(models.Model):
    name = models.CharField(max_length=150, verbose_name='Название запчасти')
    category = models.CharField(max_length=100, verbose_name='Категория')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество на складе')
    min_quantity = models.PositiveIntegerField(default=2, verbose_name='Минимальный остаток')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Цена за единицу')
    supplier = models.CharField(max_length=150, blank=True, verbose_name='Поставщик')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    class Meta:
        verbose_name = 'Запчасть'
        verbose_name_plural = 'Склад запчастей'


class RepairStatusHistory(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE,
        related_name='status_history', verbose_name='Заявка'
    )
    old_status = models.CharField(max_length=20, blank=True, verbose_name='Предыдущий статус')
    new_status = models.CharField(max_length=20, choices=RepairRequest.STATUS_CHOICES, verbose_name='Новый статус')
    comment = models.CharField(max_length=500, blank=True, verbose_name='Комментарий')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='repair_status_changes',
        verbose_name='Кто изменил'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')

    class Meta:
        verbose_name = 'История статусов'
        verbose_name_plural = 'История статусов'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка №{self.repair_id}: {self.get_new_status_display()}'


class RepairComment(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Заявка'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='repair_comments',
        verbose_name='Автор'
    )
    text = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата комментария')

    class Meta:
        verbose_name = 'Комментарий к заявке'
        verbose_name_plural = 'Комментарии к заявкам'
        ordering = ['created_at']

    def __str__(self):
        return f'Комментарий к заявке №{self.repair_id}'


class RepairPartUsage(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE,
        related_name='part_usages', verbose_name='Заявка'
    )
    part = models.ForeignKey(
        StockPart, on_delete=models.PROTECT,
        related_name='usages', verbose_name='Запчасть'
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
        verbose_name='Цена за единицу на момент списания'
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='used_repair_parts',
        verbose_name='Списал'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата списания')

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    class Meta:
        verbose_name = 'Использованная запчасть'
        verbose_name_plural = 'Использованные запчасти'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.part.name} × {self.quantity} для заявки №{self.repair_id}'
