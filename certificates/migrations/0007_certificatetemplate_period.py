from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("certificates", "0006_certificatetemplate_classroom")]

    operations = [
        migrations.AddField(
            model_name="certificatetemplate",
            name="period",
            field=models.CharField(
                choices=[
                    ("term_1", "الفصل الأول"),
                    ("term_2", "الفصل الثاني"),
                    ("academic_year", "العام الدراسي"),
                ],
                default="term_1",
                help_text="تحدد الفترة التي يجب اكتمال درجاتها قبل إصدار الشهادة.",
                max_length=20,
                verbose_name="فترة الشهادة",
            ),
        ),
    ]
