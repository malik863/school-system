
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model

from schools.models import School, AcademicYear, Term
from academics.models import (
    Classroom,
    Subject,
    TeachingAssignment,
    ClassroomSubject,
    AcademicScheme,
    AcademicSchemeRule,
    GradeScheme,
)
from students.models import StudentProfile
from assessments.models import Assessment, Grade
from attendance.models import Attendance


User = get_user_model()


class Command(BaseCommand):
    help = "Create a complete demo/trial school with realistic sample data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-name",
            default="مدرسة المستقبل الدولية - تجربة",
            help="Name of the demo school",
        )

        parser.add_argument(
            "--slug",
            default="demo-school",
            help="Unique slug for the demo school",
        )

        parser.add_argument(
            "--manager-username",
            default="demo_manager",
            help="Username for the school manager",
        )

        parser.add_argument(
            "--password",
            default="Demo@12345",
            help="Password for demo accounts",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        school_name = options["school_name"]
        slug = options["slug"]
        manager_username = options["manager_username"]
        password = options["password"]

        # ---------------------------------------------------------
        # 1. Prevent accidental duplicate demo school
        # ---------------------------------------------------------

        if School.objects.filter(slug=slug).exists():
            raise CommandError(
                f"School with slug '{slug}' already exists."
            )

        if User.objects.filter(username=manager_username).exists():
            raise CommandError(
                f"Username '{manager_username}' already exists."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Creating demo school..."
            )
        )

        # ---------------------------------------------------------
        # 2. SCHOOL
        # ---------------------------------------------------------

        school = School.objects.create(
            name=school_name,
            slug=slug,
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ School created: {school.name}"
            )
        )

        # ---------------------------------------------------------
        # 3. MANAGER
        # ---------------------------------------------------------

        manager = User.objects.create_user(
            username=manager_username,
            password=password,
            first_name="أحمد",
            last_name="مدير المدرسة",
            email="demo.manager@example.com",
            phone_number="01000000000",
            role=User.Role.SCHOOL_MANAGER,
            school=school,
            email_verified=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Manager created: {manager.username}"
            )
        )

        # ---------------------------------------------------------
        # 4. ACADEMIC YEAR
        # ---------------------------------------------------------

        academic_year = AcademicYear.objects.create(
            school=school,
            name="2026 / 2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )

        # ---------------------------------------------------------
        # 5. TERMS
        # ---------------------------------------------------------

        term1 = Term.objects.create(
            school=school,
            academic_year=academic_year,
            name="الترم الأول",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 15),
            is_current=True,
            is_closed=False,
        )

        term2 = Term.objects.create(
            school=school,
            academic_year=academic_year,
            name="الترم الثاني",
            start_date=date(2027, 1, 16),
            end_date=date(2027, 6, 30),
            is_current=False,
            is_closed=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Academic year and terms created"
            )
        )

        # ---------------------------------------------------------
        # 6. TEACHERS
        # ---------------------------------------------------------

        teachers_data = [
            {
                "username": "demo_teacher_ahmed",
                "first_name": "أحمد",
                "last_name": "محمد",
                "email": "ahmed.teacher@example.com",
                "phone": "01111111111",
            },
            {
                "username": "demo_teacher_sara",
                "first_name": "سارة",
                "last_name": "علي",
                "email": "sara.teacher@example.com",
                "phone": "01111111112",
            },
            {
                "username": "demo_teacher_omar",
                "first_name": "عمر",
                "last_name": "حسن",
                "email": "omar.teacher@example.com",
                "phone": "01111111113",
            },
            {
                "username": "demo_teacher_mariam",
                "first_name": "مريم",
                "last_name": "أحمد",
                "email": "mariam.teacher@example.com",
                "phone": "01111111114",
            },
        ]

        teachers = {}

        for data in teachers_data:

            teacher = User.objects.create_user(
                username=data["username"],
                password=password,
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone_number=data["phone"],
                role=User.Role.TEACHER,
                school=school,
                email_verified=True,
            )

            teachers[data["username"]] = teacher

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(teachers)} teachers created"
            )
        )

        # ---------------------------------------------------------
        # 7. SUBJECTS
        # ---------------------------------------------------------

        subjects_data = [
            ("اللغة العربية", "AR"),
            ("اللغة الإنجليزية", "EN"),
            ("الرياضيات", "MATH"),
            ("العلوم", "SCI"),
            ("الدراسات الاجتماعية", "SS"),
        ]

        subjects = {}

        for name, code in subjects_data:

            subject = Subject.objects.create(
                school=school,
                name=name,
                code=code,
            )

            subjects[code] = subject

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(subjects)} subjects created"
            )
        )

        # ---------------------------------------------------------
        # 8. CLASSROOMS
        # ---------------------------------------------------------

        class_4a = Classroom.objects.create(
            school=school,
            academic_year=academic_year,
            name="4A",
            grade_level=4,
            lead_teacher=teachers["demo_teacher_ahmed"],
        )

        class_4b = Classroom.objects.create(
            school=school,
            academic_year=academic_year,
            name="4B",
            grade_level=4,
            lead_teacher=teachers["demo_teacher_sara"],
        )

        classrooms = [class_4a, class_4b]

        self.stdout.write(
            self.style.SUCCESS(
                "✓ 2 classrooms created"
            )
        )

        # ---------------------------------------------------------
        # 9. ACADEMIC SCHEME
        # ---------------------------------------------------------

        academic_scheme = AcademicScheme.objects.create(
            school=school,
            name="النظام الأكاديمي للصف الرابع",
            description=(
                "نظام أكاديمي تجريبي يوضح طريقة توزيع المواد "
                "والتقييمات والدرجات."
            ),
        )

        academic_scheme.classrooms.set(classrooms)

        all_subjects = list(subjects.values())

        academic_scheme.subjects.set(all_subjects)

        # ---------------------------------------------------------
        # 10. ACADEMIC SCHEME RULES
        # ---------------------------------------------------------

        AcademicSchemeRule.objects.create(
            school=school,
            scheme=academic_scheme,
            assessment_type=AcademicSchemeRule.AssessmentType.EXAM,
            max_count=2,
            weight=Decimal("60"),
        )

        AcademicSchemeRule.objects.create(
            school=school,
            scheme=academic_scheme,
            assessment_type=AcademicSchemeRule.AssessmentType.PROJECT,
            max_count=1,
            weight=Decimal("40"),
        )

        # ---------------------------------------------------------
        # 11. CLASSROOM SUBJECTS
        # ---------------------------------------------------------

        for classroom in classrooms:

            for subject in all_subjects:

                ClassroomSubject.objects.create(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Classroom subjects created"
            )
        )

        # ---------------------------------------------------------
        # 12. GRADE SCHEMES
        # ---------------------------------------------------------

        for subject in all_subjects:

            grade_exam = GradeScheme.objects.create(
                school=school,
                subject=subject,
                assessment_type=GradeScheme.AssessmentType.EXAM,
                max_count=2,
                weight=Decimal("60"),
            )

            grade_exam.classrooms.set(classrooms)

            grade_project = GradeScheme.objects.create(
                school=school,
                subject=subject,
                assessment_type=GradeScheme.AssessmentType.PROJECT,
                max_count=1,
                weight=Decimal("40"),
            )

            grade_project.classrooms.set(classrooms)

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Grade schemes created"
            )
        )

        # ---------------------------------------------------------
        # 13. TEACHING ASSIGNMENTS
        # ---------------------------------------------------------

        teacher_list = [
            teachers["demo_teacher_ahmed"],
            teachers["demo_teacher_sara"],
            teachers["demo_teacher_omar"],
            teachers["demo_teacher_mariam"],
        ]

        for index, subject in enumerate(all_subjects):

            teacher = teacher_list[index % len(teacher_list)]

            for classroom in classrooms:

                TeachingAssignment.objects.create(
                    school=school,
                    teacher=teacher,
                    classroom=classroom,
                    subject=subject,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Teaching assignments created"
            )
        )

        # ---------------------------------------------------------
        # 14. STUDENTS
        # ---------------------------------------------------------

        student_names = [
            ("يوسف", "أحمد"),
            ("محمد", "علي"),
            ("عمر", "خالد"),
            ("آدم", "حسن"),
            ("سيف", "محمد"),
            ("كريم", "أحمد"),
            ("زياد", "علي"),
            ("ياسين", "محمود"),
            ("عبدالله", "حسن"),
            ("إياد", "محمد"),

            ("سارة", "أحمد"),
            ("مريم", "علي"),
            ("نور", "حسن"),
            ("ملك", "محمد"),
            ("جنى", "أحمد"),
            ("ليان", "خالد"),
            ("تاليا", "علي"),
            ("ريم", "محمود"),
            ("لارا", "حسن"),
            ("فريدة", "محمد"),
        ]

        students = []

        for index, (first_name, last_name) in enumerate(
            student_names,
            start=1
        ):

            classroom = (
                class_4a
                if index <= 10
                else class_4b
            )

            username = f"demo_student_{index}"

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@example.com",
                phone_number=f"01234567{index:03d}",
                role=User.Role.STUDENT,
                school=school,
                email_verified=True,
            )

            student = StudentProfile.objects.create(
                school=school,
                user=user,
                classroom=classroom,
                student_number=f"ST{index:04d}",
                national_id=f"2900101{index:04d}",
                parent_phone=f"01012345{index:03d}",
                date_of_birth=date(
                    2016 if index % 2 else 2015,
                    (index % 12) + 1,
                    (index % 25) + 1,
                ),
                is_active=True,
            )

            students.append(student)

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(students)} students created"
            )
        )

        # ---------------------------------------------------------
        # 15. ASSESSMENTS + GRADES
        # ---------------------------------------------------------

        assessment_counter = 0

        for classroom in classrooms:

            for subject_index, subject in enumerate(
                all_subjects
            ):

                teacher = teacher_list[
                    subject_index % len(teacher_list)
                ]

                # First exam
                assessment_counter += 1

                exam1 = Assessment.objects.create(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                    term=term1,
                    title=f"اختبار {subject.name} الأول",
                    assessment_type=Assessment.AssessmentType.EXAM,
                    max_score=100,
                    date=date(2026, 10, 15),
                    created_by=teacher,
                )

                # Project
                assessment_counter += 1

                project = Assessment.objects.create(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                    term=term1,
                    title=f"مشروع {subject.name}",
                    assessment_type=Assessment.AssessmentType.PROJECT,
                    max_score=100,
                    date=date(2026, 11, 15),
                    created_by=teacher,
                )

                # Second exam
                assessment_counter += 1

                exam2 = Assessment.objects.create(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                    term=term1,
                    title=f"اختبار {subject.name} الثاني",
                    assessment_type=Assessment.AssessmentType.EXAM,
                    max_score=100,
                    date=date(2026, 12, 15),
                    created_by=teacher,
                )

                assessments = [
                    exam1,
                    project,
                    exam2,
                ]

                classroom_students = [
                    student
                    for student in students
                    if student.classroom_id == classroom.id
                ]

                for student_index, student in enumerate(
                    classroom_students
                ):

                    for assessment_index, assessment in enumerate(
                        assessments
                    ):

                        score = Decimal(
                            70
                            + (
                                (student_index * 3)
                                + (assessment_index * 5)
                            )
                            % 26
                        )

                        Grade.objects.create(
                            school=school,
                            assessment=assessment,
                            student=student,
                            score=score,
                            recorded_by=teacher,
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {assessment_counter} assessments and grades created"
            )
        )

        # ---------------------------------------------------------
        # 16. ATTENDANCE
        # ---------------------------------------------------------

        attendance_statuses = [
            Attendance.Status.PRESENT,
            Attendance.Status.PRESENT,
            Attendance.Status.PRESENT,
            Attendance.Status.LATE,
            Attendance.Status.ABSENT,
        ]

        attendance_start = date(2026, 9, 7)

        for day_offset in range(5):

            attendance_date = (
                attendance_start
                + timedelta(days=day_offset)
            )

            # Skip Friday/Saturday
            if attendance_date.weekday() in [4, 5]:
                continue

            for student_index, student in enumerate(students):

                classroom = (
                    class_4a
                    if student.classroom_id == class_4a.id
                    else class_4b
                )

                teacher = (
                    classroom.lead_teacher
                )

                status = attendance_statuses[
                    (student_index + day_offset)
                    % len(attendance_statuses)
                ]

                Attendance.objects.create(
                    school=school,
                    student=student,
                    classroom=classroom,
                    term=term1,
                    date=attendance_date,
                    status=status,
                    recorded_by=teacher,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Attendance records created"
            )
        )

        # ---------------------------------------------------------
        # FINISHED
        # ---------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=========================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "       DEMO SCHOOL CREATED SUCCESSFULLY"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=========================================="
            )
        )

        self.stdout.write("")

        self.stdout.write(
            f"School: {school.name}"
        )

        self.stdout.write(
            f"Slug: {school.slug}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "MANAGER LOGIN"
            )
        )

        self.stdout.write(
            f"Username: {manager_username}"
        )

        self.stdout.write(
            f"Password: {password}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "TEACHER LOGIN EXAMPLE"
            )
        )

        self.stdout.write(
            "Username: demo_teacher_ahmed"
        )

        self.stdout.write(
            f"Password: {password}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "STUDENT LOGIN EXAMPLE"
            )
        )

        self.stdout.write(
            "Username: demo_student_1"
        )

        self.stdout.write(
            f"Password: {password}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data is ready."
            )
        )

        self.stdout.write("")