from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academics", "0005_academicscheme_academicschemerule")]

    operations = [
        migrations.AlterField(
            model_name="academicschemerule",
            name="assessment_type",
            field=models.CharField(
                choices=[("exam", "اختبار"), ("project", "مشروع"), ("attendance", "حضور")],
                max_length=20,
                verbose_name="نوع التقييم",
            ),
        ),
        migrations.AlterField(
            model_name="academicschemerule",
            name="max_count",
            field=models.PositiveIntegerField(
                blank=True, null=True, help_text="غير مطلوب للحضور.", verbose_name="عدد التقييمات"
            ),
        ),
    ]
