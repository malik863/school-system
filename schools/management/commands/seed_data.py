from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from academics.models import Classroom, Subject, TeachingAssignment
from students.models import StudentProfile
from schools.models import AcademicYear, School, Term


User = get_user_model()


class Command(BaseCommand):
    help = "Creates or updates development test data for the school system."

    @transaction.atomic
    def handle(self, *args, **options):
        school, _ = School.objects.get_or_create(
            slug="test-school",
            defaults={
                "name": "مدرسة الاختبار",
                "is_active": True,
            },
        )
        school.name = "مدرسة الاختبار"
        school.is_active = True
        school.save(update_fields=["name", "is_active"])

        manager, _ = User.objects.get_or_create(username="manager")
        manager.first_name = "مدير"
        manager.last_name = "المدرسة"
        manager.email = "manager@test.com"
        manager.role = User.Role.SCHOOL_MANAGER
        manager.school = school
        manager.email_verified = True
        manager.is_active = True
        manager.is_staff = False
        manager.is_superuser = False
        manager.set_password("Manager123!")
        manager.save()

        teachers_data = [
            ("teacher1", "أحمد", "محمد", "teacher1@test.com"),
            ("teacher2", "محمد", "علي", "teacher2@test.com"),
            ("teacher3", "خالد", "حسن", "teacher3@test.com"),
        ]

        teachers = []
        for username, first_name, last_name, email in teachers_data:
            teacher, _ = User.objects.get_or_create(username=username)
            teacher.first_name = first_name
            teacher.last_name = last_name
            teacher.email = email
            teacher.role = User.Role.TEACHER
            teacher.school = school
            teacher.email_verified = True
            teacher.is_active = True
            teacher.is_staff = False
            teacher.is_superuser = False
            teacher.set_password("Teacher123!")
            teacher.save()
            teachers.append(teacher)

        academic_year, _ = AcademicYear.objects.get_or_create(
            school=school,
            name="2026/2027",
            defaults={
                "start_date": "2026-09-01",
                "end_date": "2027-06-30",
                "is_current": True,
            },
        )
        academic_year.start_date = "2026-09-01"
        academic_year.end_date = "2027-06-30"
        academic_year.is_current = True
        academic_year.save()

        term1, _ = Term.objects.get_or_create(
            school=school,
            academic_year=academic_year,
            name="الترم الأول",
            defaults={
                "start_date": "2026-09-01",
                "end_date": "2027-01-15",
                "is_current": True,
                "is_closed": False,
            },
        )
        term1.start_date = "2026-09-01"
        term1.end_date = "2027-01-15"
        term1.is_current = True
        term1.is_closed = False
        term1.save()

        term2, _ = Term.objects.get_or_create(
            school=school,
            academic_year=academic_year,
            name="الترم الثاني",
            defaults={
                "start_date": "2027-01-16",
                "end_date": "2027-06-30",
                "is_current": False,
                "is_closed": False,
            },
        )
        term2.start_date = "2027-01-16"
        term2.end_date = "2027-06-30"
        term2.is_current = False
        term2.is_closed = False
        term2.save()

        classroom1, _ = Classroom.objects.get_or_create(
            school=school,
            academic_year=academic_year,
            name="3A",
            defaults={
                "grade_level": 3,
                "lead_teacher": teachers[0],
            },
        )
        classroom1.grade_level = 3
        classroom1.lead_teacher = teachers[0]
        classroom1.save()

        classroom2, _ = Classroom.objects.get_or_create(
            school=school,
            academic_year=academic_year,
            name="3B",
            defaults={
                "grade_level": 3,
                "lead_teacher": teachers[1],
            },
        )
        classroom2.grade_level = 3
        classroom2.lead_teacher = teachers[1]
        classroom2.save()

        subjects = []
        for name, code in [
            ("الرياضيات", "MATH"),
            ("اللغة العربية", "ARABIC"),
            ("العلوم", "SCI"),
        ]:
            subject, _ = Subject.objects.get_or_create(
                school=school,
                name=name,
                defaults={"code": code},
            )
            subject.code = code
            subject.save(update_fields=["code"])
            subjects.append(subject)

        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[0],
            classroom=classroom1,
            subject=subjects[0],
        )
        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[1],
            classroom=classroom1,
            subject=subjects[1],
        )
        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[2],
            classroom=classroom2,
            subject=subjects[2],
        )

        students_data = [
            ("student1", "علي", "حسن", "1001", "01000000001", classroom1),
            ("student2", "عمر", "خالد", "1002", "01000000002", classroom1),
            ("student3", "يوسف", "أحمد", "1003", "01000000003", classroom2),
        ]

        for username, first_name, last_name, student_number, parent_phone, classroom in students_data:
            student_user, _ = User.objects.get_or_create(username=username)
            student_user.first_name = first_name
            student_user.last_name = last_name
            student_user.email = f"{username}@test.com"
            student_user.role = User.Role.STUDENT
            student_user.school = school
            student_user.email_verified = True
            student_user.is_active = True
            student_user.is_staff = False
            student_user.is_superuser = False
            student_user.set_password("Student123!")
            student_user.save()

            profile, _ = StudentProfile.objects.get_or_create(
                user=student_user,
                defaults={
                    "school": school,
                    "classroom": classroom,
                    "student_number": student_number,
                    "parent_phone": parent_phone,
                },
            )
            profile.school = school
            profile.classroom = classroom
            profile.student_number = student_number
            profile.parent_phone = parent_phone
            profile.is_active = True
            profile.save()

        self.stdout.write(self.style.SUCCESS("Seed data completed successfully."))
        self.stdout.write("School: مدرسة الاختبار")
        self.stdout.write("Manager: manager / Manager123!")
        self.stdout.write("Teachers: teacher1, teacher2, teacher3 / Teacher123!")
        self.stdout.write("Students: student1, student2, student3 / Student123!")
