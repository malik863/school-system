from django import forms
from django.contrib.auth import get_user_model

from academics.models import (
    AcademicScheme,
    Classroom,
    Subject,
    GradeScheme,
)
from students.models import StudentProfile

from .models import AcademicYear, Term


User = get_user_model()


class BaseSchoolForm(forms.ModelForm):
    """Base form that receives the current manager's school."""

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if not self.school:
            return

        for field in self.fields.values():
            if not hasattr(field, "queryset"):
                continue

            model = field.queryset.model
            try:
                model._meta.get_field("school")
            except Exception:
                continue

            field.queryset = field.queryset.filter(school=self.school)


# =========================================================
# TEACHERS
# =========================================================

class TeacherCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "username": "اسم المستخدم",
            "first_name": "الاسم الأول",
            "last_name": "اسم العائلة",
            "email": "البريد الإلكتروني",
            "phone_number": "رقم الهاتف",
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.TEACHER
        user.school = self.school
        user.email_verified = False

        if commit:
            user.save()
        return user


class TeacherUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "username": "اسم المستخدم",
            "first_name": "الاسم الأول",
            "last_name": "اسم العائلة",
            "email": "البريد الإلكتروني",
            "phone_number": "رقم الهاتف",
            "is_active": "الحساب نشط",
        }


# =========================================================
# CLASSROOMS
# =========================================================
class ClassroomForm(BaseSchoolForm):
    class Meta:
        model = Classroom
        fields = [
            "name",
            "grade_level",
            "academic_year",
            "lead_teacher",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "grade_level": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "academic_year": forms.Select(
                attrs={"class": "form-select"}
            ),
            "lead_teacher": forms.Select(
                attrs={"class": "form-select"}
            ),
        }
        labels = {
            "name": "اسم الفصل",
            "grade_level": "الصف الدراسي",
            "academic_year": "العام الدراسي",
            "lead_teacher": "معلم الفصل",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.school:
            self.instance.school = self.school

            self.fields["academic_year"].queryset = (
                AcademicYear.objects.filter(
                    school=self.school
                )
            )

            self.fields["lead_teacher"].queryset = (
                User.objects.filter(
                    school=self.school,
                    role=User.Role.TEACHER,
                )
                .order_by(
                    "first_name",
                    "last_name",
                    "username",
                )
            )
# =========================================================
# SUBJECTS
# =========================================================

class SubjectForm(BaseSchoolForm):
    class Meta:
        model = Subject
        fields = ["name", "code"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "اسم المادة",
            "code": "كود المادة",
        }


# =========================================================
# STUDENTS
# =========================================================
class StudentCreateForm(forms.ModelForm):
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        min_length=8,
    )

    first_name = forms.CharField(
        label="الاسم الأول",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    last_name = forms.CharField(
        label="اسم العائلة",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    phone_number = forms.CharField(
        label="رقم الهاتف",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = StudentProfile
        fields = [
            "classroom",
            "student_number",
            "national_id",
            "parent_phone",
            "date_of_birth",
            "is_active",
        ]

        widgets = {
            "classroom": forms.Select(
                attrs={"class": "form-select"}
            ),
            "student_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "national_id": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "parent_phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

        labels = {
            "classroom": "الفصل",
            "student_number": "رقم الطالب",
            "national_id": "الرقم القومي",
            "parent_phone": "رقم ولي الأمر",
            "date_of_birth": "تاريخ الميلاد",
            "is_active": "الطالب نشط",
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if self.school:
            # Set the school before Django runs model validation.
            self.instance.school = self.school

            # Only show classrooms belonging to this school.
            self.fields["classroom"].queryset = Classroom.objects.filter(
                school=self.school
            )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "اسم المستخدم مستخدم بالفعل."
            )

        return username

    def clean_classroom(self):
        classroom = self.cleaned_data.get("classroom")

        if classroom is None:
            raise forms.ValidationError(
                "يجب اختيار فصل."
            )

        if not self.school:
            raise forms.ValidationError(
                "لم يتم تحديد المدرسة."
            )

        if classroom.school_id != self.school.id:
            raise forms.ValidationError(
                "الفصل المحدد لا ينتمي إلى مدرسة المدير الحالية."
            )

        return classroom

    def save(self, commit=True):
        student = super().save(commit=False)

        user = User(
            username=self.cleaned_data["username"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            phone_number=self.cleaned_data["phone_number"],
            role=User.Role.STUDENT,
            school=self.school,
            email_verified=False,
        )

        user.set_password(
            self.cleaned_data["password"]
        )

        user.save()

        student.user = user
        student.school = self.school

        if commit:
            student.save()

        return student

    
class StudentUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        label="الاسم الأول",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="اسم العائلة",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        label="رقم الهاتف",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = StudentProfile
        fields = [
            "classroom",
            "student_number",
            "national_id",
            "parent_phone",
            "date_of_birth",
            "is_active",
        ]
        widgets = {
            "classroom": forms.Select(attrs={"class": "form-select"}),
            "student_number": forms.TextInput(attrs={"class": "form-control"}),
            "national_id": forms.TextInput(attrs={"class": "form-control"}),
            "parent_phone": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "classroom": "الفصل",
            "student_number": "رقم الطالب",
            "national_id": "الرقم القومي",
            "parent_phone": "رقم ولي الأمر",
            "date_of_birth": "تاريخ الميلاد",
            "is_active": "الطالب نشط",
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if self.school:
            self.fields["classroom"].queryset = Classroom.objects.filter(
                school=self.school
            )

        if self.instance and self.instance.user_id:
            user = self.instance.user
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
            self.fields["phone_number"].initial = user.phone_number

    def save(self, commit=True):
        student = super().save(commit=False)
        user = student.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]

        if commit:
            user.save(update_fields=["first_name", "last_name", "email", "phone_number"])
            student.save()
        return student


# Backwards-compatible name for any code still importing StudentForm.
StudentForm = StudentCreateForm


# =========================================================
# ACADEMIC YEAR
# =========================================================

class AcademicYearForm(BaseSchoolForm):
    class Meta:
        model = AcademicYear
        fields = ["name", "start_date", "end_date", "is_current"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "مثال: 2026/2027"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "اسم العام الدراسي",
            "start_date": "تاريخ البداية",
            "end_date": "تاريخ النهاية",
            "is_current": "العام الحالي",
        }


# =========================================================
# TERMS
# =========================================================
class TermForm(BaseSchoolForm):
    class Meta:
        model = Term
        fields = [
            "academic_year",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "is_closed",
        ]
        widgets = {
            "academic_year": forms.Select(
                attrs={"class": "form-select"}
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: الترم الأول",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "is_current": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "is_closed": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "academic_year": "العام الدراسي",
            "name": "اسم الترم",
            "start_date": "تاريخ البداية",
            "end_date": "تاريخ النهاية",
            "is_current": "الترم الحالي",
            "is_closed": "مغلق",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.school:
            # IMPORTANT:
            # Set the school before Django runs model validation.
            self.instance.school = self.school

            # Only show academic years belonging to this school.
            self.fields["academic_year"].queryset = (
                AcademicYear.objects.filter(
                    school=self.school
                )
            )




# =========================================================
# ACADEMIC SCHEME
# =========================================================

class AcademicSchemeForm(BaseSchoolForm):
    classrooms = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.none(),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label="الفصول",
    )

    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label="المواد",
    )

    class Meta:
        model = AcademicScheme

        fields = [
            "name",
            "description",
            "classrooms",
            "subjects",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: النظام الأساسي للمرحلة الابتدائية",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "وصف اختياري للنظام",
                }
            ),

        }

        labels = {
            "name": "اسم النظام الأكاديمي",
            "description": "الوصف",
            "classrooms": "الفصول",
            "subjects": "المواد",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.school:
            return

        self.fields["classrooms"].queryset = (
            Classroom.objects.filter(
                school=self.school
            )
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        self.fields["subjects"].queryset = (
            Subject.objects.filter(
                school=self.school
            )
            .order_by("name")
        )

        # Keep selected values when editing an existing scheme.
        if self.instance.pk:
            self.initial["classrooms"] = self.instance.classrooms.all()
            self.initial["subjects"] = self.instance.subjects.all()

    def clean_classrooms(self):
        classrooms = self.cleaned_data["classrooms"]

        for classroom in classrooms:
            if classroom.school_id != self.school.id:
                raise forms.ValidationError(
                    "الفصل المحدد لا ينتمي إلى مدرسة المدير الحالية."
                )

        # A classroom can belong to only ONE academic scheme.
        for classroom in classrooms:
            existing_schemes = (
                AcademicScheme.objects
                .filter(
                    school=self.school,
                    classrooms=classroom,
                )
                .exclude(pk=self.instance.pk)
            )

            if existing_schemes.exists():
                scheme_names = ", ".join(
                    existing_schemes.values_list(
                        "name",
                        flat=True,
                    )
                )

                raise forms.ValidationError(
                    f"الفصل «{classroom.name}» مرتبط بالفعل "
                    f"بالنظام الأكاديمي: {scheme_names}. "
                    "لا يمكن ربط الفصل بأكثر من نظام أكاديمي."
                )

        return classrooms

    def clean_subjects(self):
        subjects = self.cleaned_data["subjects"]

        for subject in subjects:
            if subject.school_id != self.school.id:
                raise forms.ValidationError(
                    "المادة المحددة لا تنتمي إلى مدرسة المدير الحالية."
                )

        return subjects