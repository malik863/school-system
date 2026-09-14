from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from schools.models import School, AcademicYear, Term
from academics.models import Classroom, Subject, TeachingAssignment
from students.models import StudentProfile


User = get_user_model()


class Command(BaseCommand):
    help = "Creates test data for the school system"

    def handle(self, *args, **options):

        self.stdout.write("Starting seed data...")

        # =====================================================
        # SCHOOL
        # =====================================================

        school, created = School.objects.get_or_create(
            slug="test-school",
            defaults={
                "name": "مدرسة الاختبار",
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"School: {school.name}"
            )
        )

        # =====================================================
        # SCHOOL MANAGER
        # =====================================================

        manager, created = User.objects.get_or_create(
            username="manager",
            defaults={
                "first_name": "مدير",
                "last_name": "المدرسة",
                "email": "manager@test.com",
                "role": User.Role.SCHOOL_MANAGER,
                "school": school,
                "email_verified": True,
                "is_staff": False,
            },
        )

        manager.school = school
        manager.role = User.Role.SCHOOL_MANAGER
        manager.email_verified = True
        manager.is_active = True
        manager.set_password("Manager123!")
        manager.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Manager: manager / Manager123!"
            )
        )

        # =====================================================
        # TEACHERS
        # =====================================================

        teachers_data = [
            {
                "username": "teacher1",
                "first_name": "أحمد",
                "last_name": "محمد",
                "email": "teacher1@test.com",
            },
            {
                "username": "teacher2",
                "first_name": "محمد",
                "last_name": "علي",
                "email": "teacher2@test.com",
            },
            {
                "username": "teacher3",
                "first_name": "خالد",
                "last_name": "حسن",
                "email": "teacher3@test.com",
            },
        ]

        teachers = []

        for data in teachers_data:

            teacher, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                    "role": User.Role.TEACHER,
                    "school": school,
                    "email_verified": True,
                    "is_active": True,
                },
            )

            teacher.first_name = data["first_name"]
            teacher.last_name = data["last_name"]
            teacher.email = data["email"]
            teacher.role = User.Role.TEACHER
            teacher.school = school
            teacher.email_verified = True
            teacher.is_active = True
            teacher.set_password("Teacher123!")
            teacher.save()

            teachers.append(teacher)

        self.stdout.write(
            self.style.SUCCESS(
                "Teachers: teacher1, teacher2, teacher3 / Teacher123!"
            )
        )

        # =====================================================
        # ACADEMIC YEAR
        # =====================================================

        academic_year, created = AcademicYear.objects.get_or_create(
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
        academic_year.school = school
        academic_year.save()

        # =====================================================
        # TERMS
        # =====================================================

        term1, created = Term.objects.get_or_create(
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
        term1.school = school
        term1.academic_year = academic_year
        term1.save()

        term2, created = Term.objects.get_or_create(
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
        term2.school = school
        term2.academic_year = academic_year
        term2.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Academic year and terms created."
            )
        )

        # =====================================================
        # CLASSROOMS
        # =====================================================

        classroom1, created = Classroom.objects.get_or_create(
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
        classroom1.school = school
        classroom1.academic_year = academic_year
        classroom1.save()

        classroom2, created = Classroom.objects.get_or_create(
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
        classroom2.school = school
        classroom2.academic_year = academic_year
        classroom2.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Classrooms created."
            )
        )

        # =====================================================
        # SUBJECTS
        # =====================================================

        math, created = Subject.objects.get_or_create(
            school=school,
            name="الرياضيات",
            defaults={
                "code": "MATH",
            },
        )

        arabic, created = Subject.objects.get_or_create(
            school=school,
            name="اللغة العربية",
            defaults={
                "code": "ARABIC",
            },
        )

        science, created = Subject.objects.get_or_create(
            school=school,
            name="العلوم",
            defaults={
                "code": "SCI",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Subjects created."
            )
        )

        # =====================================================
        # TEACHING ASSIGNMENTS
        # =====================================================

        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[0],
            classroom=classroom1,
            subject=math,
        )

        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[1],
            classroom=classroom1,
            subject=arabic,
        )

        TeachingAssignment.objects.get_or_create(
            school=school,
            teacher=teachers[2],
            classroom=classroom2,
            subject=science,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teaching assignments created."
            )
        )

        # =====================================================
        # STUDENTS
        # =====================================================

        students_data = [
            {
                "username": "student1",
                "first_name": "عمر",
                "last_name": "أحمد",
                "email": "student1@test.com",
                "student_number": "ST001",
                "classroom": classroom1,
            },
            {
                "username": "student2",
                "first_name": "علي",
                "last_name": "محمد",
                "email": "student2@test.com",
                "student_number": "ST002",
                "classroom": classroom1,
            },
            {
                "username": "student3",
                "first_name": "يوسف",
                "last_name": "خالد",
                "email": "student3@test.com",
                "student_number": "ST003",
                "classroom": classroom2,
            },
        ]

        for data in students_data:

            student_user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                    "school": school,
                    "email_verified": True,
                    "is_active": True,
                },
            )

            student_user.first_name = data["first_name"]
            student_user.last_name = data["last_name"]
            student_user.email = data["email"]
            student_user.school = school
            student_user.email_verified = True
            student_user.is_active = True
            student_user.set_password("Student123!")
            student_user.save()

            StudentProfile.objects.update_or_create(
                user=student_user,
                defaults={
                    "school": school,
                    "classroom": data["classroom"],
                    "student_number": data["student_number"],
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Students: student1, student2, student3 / Student123!"
            )
        )

        # =====================================================
        # DONE
        # =====================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "====================================="
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Seed data completed successfully."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "====================================="
            )
        )