from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0003_studentprofile_first_name_studentprofile_last_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="الجنسية"),
        ),
    ]
