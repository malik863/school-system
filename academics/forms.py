
from django import forms
from django.contrib.auth import get_user_model


from .models import (
    AcademicScheme,
    AcademicSchemeRule,
    Classroom,
    ClassroomSubject,
    GradeScheme,
    Subject,
    TeachingAssignment,
)

from decimal import Decimal

User = get_user_model()


class AcademicSchoolForm(forms.ModelForm):
    """
    Base form that keeps all school-owned querysets
    restricted to the current school.
    """

    def __init__(self, *args, school=None, **kwargs):
        self.school = school

        super().__init__(*args, **kwargs)

        if self.school:
            self.instance.school = self.school

            for field in self.fields.values():
                queryset = getattr(field, "queryset", None)

                if queryset is None:
                    continue

                model = queryset.model

                if hasattr(model, "school"):
                    field.queryset = queryset.filter(
                        school=self.school
                    )


class ClassroomSubjectForm(AcademicSchoolForm):
    class Meta:
        model = ClassroomSubject
        fields = [
            "classroom",
            "subject",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, school=school, **kwargs)

        self.fields["classroom"].queryset = (
            Classroom.objects
            .filter(school=self.school)
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        self.fields["subject"].queryset = (
            Subject.objects
            .filter(school=self.school)
            .order_by("name")
        )

    def clean(self):
        cleaned_data = super().clean()

        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            exists = ClassroomSubject.objects.filter(
                school=self.school,
                classroom=classroom,
                subject=subject,
            )

            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError(
                    "هذه المادة مضافة بالفعل إلى هذا الفصل."
                )

        return cleaned_data


class TeachingAssignmentForm(AcademicSchoolForm):
    class Meta:
        model = TeachingAssignment
        fields = [
            "classroom",
            "subject",
            "teacher",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, school=school, **kwargs)

        self.fields["classroom"].queryset = (
            Classroom.objects
            .filter(school=self.school)
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        self.fields["subject"].queryset = (
            Subject.objects
            .filter(school=self.school)
            .order_by("name")
        )

        self.fields["teacher"].queryset = (
            User.objects
            .filter(
                school=self.school,
                role=User.Role.TEACHER,
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    def clean(self):
        cleaned_data = super().clean()

        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")
        teacher = cleaned_data.get("teacher")

        if classroom and subject:

            # Subject must be enabled for this classroom.
            if not ClassroomSubject.objects.filter(
                school=self.school,
                classroom=classroom,
                subject=subject,
            ).exists():
                raise forms.ValidationError(
                    "هذه المادة غير مضافة إلى هذا الفصل. "
                    "أضف المادة إلى الفصل أولًا."
                )

            duplicate = TeachingAssignment.objects.filter(
                school=self.school,
                classroom=classroom,
                subject=subject,
            )

            if self.instance.pk:
                duplicate = duplicate.exclude(
                    pk=self.instance.pk
                )

            if duplicate.exists():
                existing = duplicate.select_related(
                    "teacher"
                ).first()

                raise forms.ValidationError(
                    f"هذه المادة في هذا الفصل مسندة بالفعل "
                    f"إلى المعلم {existing.teacher}."
                )

        if teacher and teacher.school_id != self.school.id:
            raise forms.ValidationError(
                "المعلم يجب أن يكون تابعًا لنفس المدرسة."
            )

        return cleaned_data


class GradeSchemeForm(AcademicSchoolForm):
    classrooms = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="الفصول",
    )

    class Meta:
        model = GradeScheme
        fields = [
            "subject",
            "assessment_type",
            "max_count",
            "weight",
            "classrooms",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, school=school, **kwargs)

        self.fields["subject"].queryset = (
            Subject.objects
            .filter(school=self.school)
            .order_by("name")
        )

        self.fields["classrooms"].queryset = (
            Classroom.objects
            .filter(school=self.school)
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        # On edit, initially show the classes already selected.
        if self.instance.pk:
            self.initial["classrooms"] = (
                self.instance.classrooms.all()
            )

    def clean(self):
        cleaned_data = super().clean()

        subject = cleaned_data.get("subject")
        classrooms = cleaned_data.get("classrooms")

        if subject and classrooms:
            invalid_classrooms = []

            for classroom in classrooms:
                studies_subject = ClassroomSubject.objects.filter(
                    school=self.school,
                    classroom=classroom,
                    subject=subject,
                ).exists()

                if not studies_subject:
                    invalid_classrooms.append(
                        classroom.name
                    )

            if invalid_classrooms:
                raise forms.ValidationError(
                    "المادة غير مضافة إلى الفصول التالية: "
                    + ", ".join(invalid_classrooms)
                    + ". أضف المادة إلى هذه الفصول أولًا."
                )

        return cleaned_data


class AcademicSchemeForm(AcademicSchoolForm):
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
                    "placeholder": "مثال: الصفوف الأساسية",
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
            "name": "اسم النظام",
            "description": "الوصف",
            "classrooms": "الفصول",
            "subjects": "المواد",
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(
            *args,
            school=school,
            **kwargs,
        )

        self.fields["classrooms"].queryset = (
            Classroom.objects
            .filter(school=self.school)
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        self.fields["subjects"].queryset = (
            Subject.objects
            .filter(school=self.school)
            .order_by("name")
        )

        if self.instance.pk:
            self.initial["classrooms"] = (
                self.instance.classrooms.all()
            )

            self.initial["subjects"] = (
                self.instance.subjects.all()
            )

    def clean_classrooms(self):
        classrooms = self.cleaned_data["classrooms"]

        for classroom in classrooms:
            if classroom.school_id != self.school.id:
                raise forms.ValidationError(
                    "الفصل المحدد لا ينتمي إلى مدرسة المدير الحالية."
                )

        # A classroom can belong to only one academic scheme.
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
                        flat=True
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



class AcademicSchemeRuleForm(AcademicSchoolForm):
    class Meta:
        model = AcademicSchemeRule
        fields = [
            "assessment_type",
            "max_count",
            "weight",
        ]
        widgets = {
            "assessment_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "max_count": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "weight": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 100,
                    "step": "0.01",
                }
            ),
        }
        labels = {
            "assessment_type": "نوع التقييم",
            "max_count": "عدد التقييمات",
            "weight": "الوزن (%)",
        }

    def __init__(
        self,
        *args,
        school=None,
        scheme=None,
        **kwargs
    ):
        self.scheme = scheme

        super().__init__(
            *args,
            school=school,
            **kwargs
        )

    def clean_weight(self):
        weight = self.cleaned_data["weight"]

        if weight <= 0:
            raise forms.ValidationError(
                "الوزن يجب أن يكون أكبر من صفر."
            )

        if weight > 100:
            raise forms.ValidationError(
                "الوزن لا يمكن أن يتجاوز 100%."
            )

        return weight

    def clean_max_count(self):
        max_count = self.cleaned_data["max_count"]

        if max_count < 1:
            raise forms.ValidationError(
                "عدد التقييمات يجب أن يكون واحدًا على الأقل."
            )

        return max_count

    def clean(self):
        cleaned_data = super().clean()

        weight = cleaned_data.get("weight")

        if not weight or not self.scheme:
            return cleaned_data

        existing_rules = AcademicSchemeRule.objects.filter(
            school=self.school,
            scheme=self.scheme,
        )

        if self.instance.pk:
            existing_rules = existing_rules.exclude(
                pk=self.instance.pk
            )

        existing_total = sum(
            (
                rule.weight
                for rule in existing_rules
            ),
            Decimal("0"),
        )

        new_total = existing_total + weight

        if new_total > Decimal("100"):
            raise forms.ValidationError(
                f"مجموع أوزان قواعد الدرجات سيكون "
                f"{new_total}%، ولا يمكن أن يتجاوز 100%."
            )

        return cleaned_data