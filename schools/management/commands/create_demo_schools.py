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
    help = "Create five complete demo schools with realistic sample data."

    PASSWORD = "Demo@12345"

    SCHOOLS = [
        {
            "name": "مدرسة النخبة الحديثة",
            "slug": "demo-elite-modern",
            "prefix": "elite",
            "grade": 4,
        },
        {
            "name": "مدرسة رواد المستقبل",
            "slug": "demo-future-leaders",
            "prefix": "future",
            "grade": 5,
        },
        {
            "name": "أكاديمية الأفق التعليمية",
            "slug": "demo-horizon-academy",
            "prefix": "horizon",
            "grade": 6,
        },
        {
            "name": "مدرسة جيل الغد",
            "slug": "demo-tomorrow-generation",
            "prefix": "tomorrow",
            "grade": 7,
        },
        {
            "name": "مدرسة المعرفة المتميزة",
            "slug": "demo-excellence-knowledge",
            "prefix": "knowledge",
            "grade": 8,
        },
    ]

    SUBJECTS = [
        ("اللغة العربية", "AR"),
        ("اللغة الإنجليزية", "EN"),
        ("الرياضيات", "MATH"),
        ("العلوم", "SCI"),
        ("الدراسات الاجتماعية", "SS"),
    ]

    TEACHERS = [
        {
            "key": "ar",
            "first_name": "أحمد",
            "last_name": "محمد",
            "email_prefix": "arabic",
        },
        {
            "key": "en",
            "first_name": "سارة",
            "last_name": "علي",
            "email_prefix": "english",
        },
        {
            "key": "math",
            "first_name": "عمر",
            "last_name": "حسن",
            "email_prefix": "math",
        },
        {
            "key": "science",
            "first_name": "مريم",
            "last_name": "أحمد",
            "email_prefix": "science",
        },
        {
            "key": "social",
            "first_name": "خالد",
            "last_name": "محمود",
            "email_prefix": "social",
        },
    ]

    FIRST_NAMES = [
        "يوسف", "محمد", "عمر", "آدم", "سيف",
        "كريم", "زياد", "ياسين", "عبدالله", "إياد",
        "سارة", "مريم", "نور", "ملك", "جنى",
    ]

    LAST_NAMES = [
        "أحمد", "علي", "حسن", "محمد", "خالد",
        "محمود", "إبراهيم", "مصطفى", "عبدالرحمن", "سمير",
        "فؤاد", "طارق", "وليد", "رامي", "نبيل",
    ]

    CLASS_NAMES = ["A", "B", "C"]

    @transaction.atomic
    def handle(self, *args, **options):
        self._validate_no_duplicates()

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Creating 5 demo schools..."
            )
        )
        self.stdout.write("")

        created_schools = []

        for school_index, school_data in enumerate(self.SCHOOLS, start=1):
            school_result = self.create_school(
                school_data=school_data,
                school_index=school_index,
            )
            created_schools.append(school_result)

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Demo school {school_index}/5 created: "
                    f"{school_result['school'].name}"
                )
            )

        self.print_summary(created_schools)

    def _validate_no_duplicates(self):
        for school_data in self.SCHOOLS:
            if School.objects.filter(
                slug=school_data["slug"]
            ).exists():
                raise CommandError(
                    f"School with slug '{school_data['slug']}' already exists."
                )

        for school_data in self.SCHOOLS:
            username = f"{school_data['prefix']}_manager"
            if User.objects.filter(username=username).exists():
                raise CommandError(
                    f"Username '{username}' already exists."
                )

    def create_school(self, school_data, school_index):
        school_name = school_data["name"]
        slug = school_data["slug"]
        prefix = school_data["prefix"]
        grade_level = school_data["grade"]

        # ---------------------------------------------------------
        # 1. SCHOOL
        # ---------------------------------------------------------

        school = School.objects.create(
            name=school_name,
            slug=slug,
            is_active=True,
        )

        # ---------------------------------------------------------
        # 2. MANAGER ACCOUNT
        # ---------------------------------------------------------

        manager_username = f"{prefix}_manager"

        manager = User.objects.create_user(
            username=manager_username,
            password=self.PASSWORD,
            first_name="مدير",
            last_name="المدرسة",
            email=f"{manager_username}@demo.local",
            phone_number=f"010{school_index:02d}0000000",
            role=User.Role.SCHOOL_MANAGER,
            school=school,
            email_verified=True,
        )

        # ---------------------------------------------------------
        # 3. ACADEMIC YEAR + TERMS
        # ---------------------------------------------------------

        academic_year = AcademicYear.objects.create(
            school=school,
            name="2026 / 2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )

        term1 = Term.objects.create(
            school=school,
            academic_year=academic_year,
            name="الترم الأول",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 15),
            is_current=True,
            is_closed=False,
        )

        Term.objects.create(
            school=school,
            academic_year=academic_year,
            name="الترم الثاني",
            start_date=date(2027, 1, 16),
            end_date=date(2027, 6, 30),
            is_current=False,
            is_closed=False,
        )

        # ---------------------------------------------------------
        # 4. TEACHERS
        # One teacher per subject, assigned to that subject in all
        # three classrooms.
        # ---------------------------------------------------------

        teachers = {}

        for teacher_data in self.TEACHERS:
            username = (
                f"{prefix}_teacher_{teacher_data['key']}"
            )

            teacher = User.objects.create_user(
                username=username,
                password=self.PASSWORD,
                first_name=teacher_data["first_name"],
                last_name=teacher_data["last_name"],
                email=(
                    f"{teacher_data['email_prefix']}"
                    f".{prefix}@demo.local"
                ),
                phone_number=(
                    f"011{school_index:02d}"
                    f"{len(teachers) + 1:02d}00000"
                ),
                role=User.Role.TEACHER,
                school=school,
                email_verified=True,
            )

            teachers[teacher_data["key"]] = teacher

        # ---------------------------------------------------------
        # 5. SUBJECTS
        # ---------------------------------------------------------

        subjects = {}

        for name, code in self.SUBJECTS:
            subject = Subject.objects.create(
                school=school,
                name=name,
                code=code,
            )
            subjects[code] = subject

        # ---------------------------------------------------------
        # 6. THREE CLASSROOMS
        # ---------------------------------------------------------

        classrooms = []

        lead_teacher_keys = ["ar", "math", "science"]

        for index, class_letter in enumerate(self.CLASS_NAMES):
            classroom = Classroom.objects.create(
                school=school,
                academic_year=academic_year,
                name=f"{grade_level}{class_letter}",
                grade_level=grade_level,
                lead_teacher=teachers[lead_teacher_keys[index]],
            )
            classrooms.append(classroom)

        # ---------------------------------------------------------
        # 7. ACADEMIC SCHEME
        # ---------------------------------------------------------

        scheme = AcademicScheme.objects.create(
            school=school,
            name=f"الخطة الأكاديمية للصف {grade_level}",
            description=(
                "خطة تجريبية كاملة توضح المواد المطلوبة "
                "وقواعد التقييم والدرجات."
            ),
        )

        scheme.classrooms.set(classrooms)
        scheme.subjects.set(subjects.values())

        AcademicSchemeRule.objects.create(
            school=school,
            scheme=scheme,
            assessment_type=AcademicSchemeRule.AssessmentType.EXAM,
            max_count=2,
            weight=Decimal("60"),
        )

        AcademicSchemeRule.objects.create(
            school=school,
            scheme=scheme,
            assessment_type=AcademicSchemeRule.AssessmentType.PROJECT,
            max_count=1,
            weight=Decimal("40"),
        )

        # ---------------------------------------------------------
        # 8. CLASSROOM SUBJECTS
        # Every classroom has all five subjects.
        # ---------------------------------------------------------

        for classroom in classrooms:
            for subject in subjects.values():
                ClassroomSubject.objects.create(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                )

        # ---------------------------------------------------------
        # 9. GRADE SCHEMES
        # ---------------------------------------------------------

        for subject in subjects.values():
            exam_scheme = GradeScheme.objects.create(
                school=school,
                subject=subject,
                assessment_type=GradeScheme.AssessmentType.EXAM,
                max_count=2,
                weight=Decimal("60"),
            )
            exam_scheme.classrooms.set(classrooms)

            project_scheme = GradeScheme.objects.create(
                school=school,
                subject=subject,
                assessment_type=GradeScheme.AssessmentType.PROJECT,
                max_count=1,
                weight=Decimal("40"),
            )
            project_scheme.classrooms.set(classrooms)

        # ---------------------------------------------------------
        # 10. TEACHING ASSIGNMENTS
        # Every subject has a teacher in every classroom.
        # This creates 5 x 3 = 15 assignments per school.
        # ---------------------------------------------------------

        subject_teacher_map = {
            "AR": teachers["ar"],
            "EN": teachers["en"],
            "MATH": teachers["math"],
            "SCI": teachers["science"],
            "SS": teachers["social"],
        }

        for classroom in classrooms:
            for code, subject in subjects.items():
                TeachingAssignment.objects.create(
                    school=school,
                    teacher=subject_teacher_map[code],
                    classroom=classroom,
                    subject=subject,
                )

        # ---------------------------------------------------------
        # 11. STUDENTS
        # 15 students in each classroom = 45 per school.
        # ---------------------------------------------------------

        students_by_classroom = {}

        global_student_number = 1

        for classroom in classrooms:
            classroom_students = []

            for student_index in range(15):
                first_name = self.FIRST_NAMES[student_index]
                last_name = self.LAST_NAMES[
                    (student_index + school_index + classroom.id)
                    % len(self.LAST_NAMES)
                ]

                username = (
                    f"{prefix}_student_"
                    f"{classroom.name.lower()}_"
                    f"{student_index + 1:02d}"
                )

                user = User.objects.create_user(
                    username=username,
                    password=self.PASSWORD,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{username}@demo.local",
                    phone_number=(
                        f"012{school_index:02d}"
                        f"{classroom.id % 100:02d}"
                        f"{student_index + 1:03d}00"
                    ),
                    role=User.Role.STUDENT,
                    school=school,
                    email_verified=True,
                )

                student = StudentProfile.objects.create(
                    school=school,
                    user=user,
                    classroom=classroom,
                    first_name=first_name,
                    last_name=last_name,
                    student_number=(
                        f"{prefix.upper()}-"
                        f"{global_student_number:04d}"
                    ),
                    national_id=(
                        f"2900{school_index:02d}"
                        f"{classroom.id % 100:02d}"
                        f"{student_index + 1:04d}"
                    ),
                    parent_phone=(
                        f"010{school_index:02d}"
                        f"{classroom.id % 100:02d}"
                        f"{student_index + 1:04d}0"
                    ),
                    date_of_birth=date(
                        2015 + (student_index % 2),
                        (student_index % 12) + 1,
                        (student_index % 25) + 1,
                    ),
                    is_active=True,
                )

                classroom_students.append(student)
                global_student_number += 1

            students_by_classroom[classroom.id] = classroom_students

        # ---------------------------------------------------------
        # 12. ASSESSMENTS
        #
        # Class A = COMPLETE:
        #   2 exams + 1 project for every subject,
        #   with grades for every student.
        #
        # Class B = PARTIAL:
        #   1 exam + 1 project for every subject,
        #   with grades for every student.
        #
        # Class C = EMPTY:
        #   no assessments at all.
        #
        # This demonstrates the certificate completion logic.
        # ---------------------------------------------------------

        assessment_counts = {
            "complete": 0,
            "partial": 0,
            "empty": 0,
        }

        grade_count = 0

        for class_index, classroom in enumerate(classrooms):
            if class_index == 0:
                assessment_plan = [
                    ("exam", "اختبار منتصف الفصل", date(2026, 10, 15)),
                    ("project", "مشروع المادة", date(2026, 11, 15)),
                    ("exam", "اختبار نهاية الفصل", date(2026, 12, 15)),
                ]
                status = "complete"

            elif class_index == 1:
                assessment_plan = [
                    ("exam", "اختبار أول", date(2026, 10, 15)),
                    ("project", "مشروع المادة", date(2026, 11, 15)),
                ]
                status = "partial"

            else:
                assessment_plan = []
                status = "empty"

            classroom_students = students_by_classroom[
                classroom.id
            ]

            for subject_index, (code, subject) in enumerate(
                subjects.items()
            ):
                teacher = subject_teacher_map[code]

                for assessment_index, (
                    assessment_type,
                    title_prefix,
                    assessment_date,
                ) in enumerate(assessment_plan):

                    if assessment_type == "exam":
                        db_type = Assessment.AssessmentType.EXAM
                    else:
                        db_type = Assessment.AssessmentType.PROJECT

                    assessment = Assessment.objects.create(
                        school=school,
                        classroom=classroom,
                        subject=subject,
                        term=term1,
                        title=(
                            f"{title_prefix} - "
                            f"{subject.name}"
                        ),
                        assessment_type=db_type,
                        max_score=100,
                        date=assessment_date,
                        created_by=teacher,
                    )

                    assessment_counts[status] += 1

                    for student_index, student in enumerate(
                        classroom_students
                    ):
                        score = Decimal(
                            68
                            + (
                                school_index * 3
                                + class_index * 4
                                + subject_index * 2
                                + assessment_index * 5
                                + student_index * 3
                            ) % 31
                        )

                        Grade.objects.create(
                            school=school,
                            assessment=assessment,
                            student=student,
                            score=score,
                            recorded_by=teacher,
                        )

                        grade_count += 1

        # ---------------------------------------------------------
        # 13. ATTENDANCE
        # 10 working days with a mixture of present, late,
        # and absent records.
        # ---------------------------------------------------------

        attendance_statuses = [
            Attendance.Status.PRESENT,
            Attendance.Status.PRESENT,
            Attendance.Status.PRESENT,
            Attendance.Status.LATE,
            Attendance.Status.ABSENT,
        ]

        attendance_start = date(2026, 9, 7)
        attendance_count = 0

        for day_offset in range(10):
            attendance_date = (
                attendance_start
                + timedelta(days=day_offset)
            )

            # Egypt weekend: Friday and Saturday.
            if attendance_date.weekday() in [4, 5]:
                continue

            for classroom in classrooms:
                classroom_students = students_by_classroom[
                    classroom.id
                ]

                teacher = classroom.lead_teacher

                for student_index, student in enumerate(
                    classroom_students
                ):
                    status = attendance_statuses[
                        (
                            student_index
                            + day_offset
                            + school_index
                        )
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

                    attendance_count += 1

        return {
            "school": school,
            "manager": manager,
            "classrooms": classrooms,
            "teachers": teachers,
            "students_by_classroom": students_by_classroom,
            "assessment_counts": assessment_counts,
            "grade_count": grade_count,
            "attendance_count": attendance_count,
        }

    def print_summary(self, created_schools):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "        5 DEMO SCHOOLS CREATED SUCCESSFULLY"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )
        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "ALL DEMO PASSWORDS:"
            )
        )
        self.stdout.write(
            self.PASSWORD
        )
        self.stdout.write("")

        for result in created_schools:
            school = result["school"]
            manager = result["manager"]
            prefix = school.slug.replace("demo-", "")

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    school.name
                )
            )

            self.stdout.write(
                f"  Slug: {school.slug}"
            )

            self.stdout.write(
                f"  Manager: {manager.username}"
            )

            self.stdout.write(
                f"  Teacher example: {prefix}_teacher_ar"
            )

            self.stdout.write(
                f"  Student example: "
                f"{prefix}_student_"
                f"{result['classrooms'][0].name.lower()}_01"
            )

            self.stdout.write(
                "  Classes: "
                "A = complete, B = partial, C = no assessments"
            )

            self.stdout.write(
                "  Assessments: "
                f"{result['assessment_counts']['complete']} complete / "
                f"{result['assessment_counts']['partial']} partial / "
                f"{result['assessment_counts']['empty']} empty"
            )

            self.stdout.write(
                f"  Grades: {result['grade_count']}"
            )

            self.stdout.write(
                f"  Attendance records: {result['attendance_count']}"
            )

            self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data is ready for showcasing the system."
            )
        )
        self.stdout.write("")
