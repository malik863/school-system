from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("students", "0005_studentenrollment")]
    operations = [
        migrations.RemoveConstraint(model_name="studentprofile", name="unique_student_number_per_school"),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.UniqueConstraint(fields=("school", "student_number"), condition=~models.Q(student_number=""), name="unique_student_number_per_school"),
        ),
    ]
