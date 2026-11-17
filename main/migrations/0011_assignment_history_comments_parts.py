from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_initial_status_history(apps, schema_editor):
    RepairRequest = apps.get_model('main', 'RepairRequest')
    RepairStatusHistory = apps.get_model('main', 'RepairStatusHistory')
    rows = [
        RepairStatusHistory(
            repair_id=repair.pk,
            old_status='',
            new_status=repair.status,
            comment='Текущий статус на момент обновления проекта',
            changed_by_id=None,
        )
        for repair in RepairRequest.objects.all().iterator()
    ]
    RepairStatusHistory.objects.bulk_create(rows)


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0010_repairrequest_photo_alter_repairrequest_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='repairrequest',
            name='assigned_master',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'is_staff': True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_repairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Назначенный мастер',
            ),
        ),
        migrations.CreateModel(
            name='RepairStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_status', models.CharField(blank=True, max_length=20, verbose_name='Предыдущий статус')),
                ('new_status', models.CharField(choices=[('new', 'Принята'), ('diagnostics', 'В диагностике'), ('in_progress', 'В ремонте'), ('ready', 'Готова к выдаче'), ('completed', 'Завершена'), ('issued', 'Выдана')], max_length=20, verbose_name='Новый статус')),
                ('comment', models.CharField(blank=True, max_length=500, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='repair_status_changes', to=settings.AUTH_USER_MODEL, verbose_name='Кто изменил')),
                ('repair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='main.repairrequest', verbose_name='Заявка')),
            ],
            options={
                'verbose_name': 'История статусов',
                'verbose_name_plural': 'История статусов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RepairComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата комментария')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='repair_comments', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
                ('repair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='main.repairrequest', verbose_name='Заявка')),
            ],
            options={
                'verbose_name': 'Комментарий к заявке',
                'verbose_name_plural': 'Комментарии к заявкам',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='RepairPartUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='Количество')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена за единицу на момент списания')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата списания')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='usages', to='main.stockpart', verbose_name='Запчасть')),
                ('repair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='part_usages', to='main.repairrequest', verbose_name='Заявка')),
                ('used_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='used_repair_parts', to=settings.AUTH_USER_MODEL, verbose_name='Списал')),
            ],
            options={
                'verbose_name': 'Использованная запчасть',
                'verbose_name_plural': 'Использованные запчасти',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(create_initial_status_history, migrations.RunPython.noop),
    ]
