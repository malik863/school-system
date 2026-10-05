from django.db import migrations, models
import django.db.models.deletion


def backfill_enrollments(apps, schema_editor):
    StudentProfile = apps.get_model("students", "StudentProfile")
    StudentEnrollment = apps.get_model("students", "StudentEnrollment")
    Grade = apps.get_model("assessments", "Grade")
    Attendance = apps.get_model("attendance", "Attendance")

    # Historical evidence first. Later evidence in the same year wins; the
    # student's current classroom is applied last and therefore is authoritative
    # for the current enrollment.
    for student in StudentProfile.objects.all().iterator():
        choices = {}
        for row in Grade.objects.filter(student_id=student.id).select_related(
            "assessment__classroom__academic_year"
        ).order_by("assessment__date", "id"):
            classroom = row.assessment.classroom
            choices[classroom.academic_year_id] = classroom.id
        for row in Attendance.objects.filter(student_id=student.id).select_related(
            "classroom__academic_year"
        ).order_by("date", "id"):
            classroom = row.classroom
            choices[classroom.academic_year_id] = classroom.id
        if student.classroom_id:
            Classroom = apps.get_model("academics", "Classroom")
            classroom = Classroom.objects.get(pk=student.classroom_id)
            choices[classroom.academic_year_id] = classroom.id
        for year_id, classroom_id in choices.items():
            StudentEnrollment.objects.update_or_create(
                school_id=student.school_id,
                student_id=student.id,
                academic_year_id=year_id,
                defaults={"classroom_id": classroom_id},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0004_studentprofile_nationality"),
        ("schools", "0001_initial"),
        ("academics", "0001_initial"),
        ("assessments", "0001_initial"),
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_enrollments", to="schools.academicyear", verbose_name="العام الدراسي")),
                ("classroom", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_enrollments", to="academics.classroom", verbose_name="الفصل")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="studentenrollment_records", to="schools.school")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="students.studentprofile", verbose_name="الطالب")),
            ],
            options={"verbose_name": "قيد طالب", "verbose_name_plural": "قيود الطلاب", "ordering": ["-academic_year__start_date", "student_id"]},
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(fields=("student", "academic_year"), name="unique_student_enrollment_per_year"),
        ),
        migrations.RunPython(backfill_enrollments, migrations.RunPython.noop),
    ]
