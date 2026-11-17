from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('main', '0011_assignment_history_comments_parts')]
    operations = [
        migrations.AddField(
            model_name='repairrequest',
            name='labor_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Стоимость работ мастера'),
        ),
    ]
