from django.core.validators import MinValueValidator
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('main', '0012_repairrequest_labor_cost')]
    operations = [
        migrations.AlterField(
            model_name='repairrequest', name='service_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)], verbose_name='Стоимость услуги на момент заявки'),
        ),
        migrations.AlterField(
            model_name='repairrequest', name='labor_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)], verbose_name='Стоимость работ мастера'),
        ),
        migrations.AlterField(
            model_name='service', name='price',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(0)], verbose_name='Стоимость'),
        ),
        migrations.AlterField(
            model_name='stockpart', name='price',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(0)], verbose_name='Цена за единицу'),
        ),
        migrations.AlterField(
            model_name='repairpartusage', name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(0)], verbose_name='Цена за единицу на момент списания'),
        ),
    ]
