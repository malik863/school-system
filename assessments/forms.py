
from django import forms
from django.core.exceptions import ValidationError

from academics.models import (
    AcademicScheme,
    AcademicSchemeRule,
    Classroom,
    ClassroomSubject,
    TeachingAssignment,
)
from schools.models import Term

from .models import Assessment
from academics.models import Subject

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            "classroom",
            "subject",
            "term",
            "title",
            "assessment_type",
            "max_score",
            "date",
        ]

        widgets = {
            "classroom": forms.Select(
                attrs={"class": "form-select"}
            ),
            "subject": forms.Select(
                attrs={"class": "form-select"}
            ),
            "term": forms.Select(
                attrs={"class": "form-select"}
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: اختبار الرياضيات الأول",
                }
            ),
            "assessment_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "max_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

        labels = {
            "classroom": "الفصل",
            "subject": "المادة",
            "term": "الترم",
            "title": "اسم التقييم",
            "assessment_type": "نوع التقييم",
            "max_score": "الدرجة النهائية",
            "date": "التاريخ",
        }

    def __init__(
        self,
        *args,
        teacher=None,
        school=None,
        **kwargs,
    ):
        self.teacher = teacher
        self.school = school

        super().__init__(*args, **kwargs)

        if school and not self.instance.school_id:
            self.instance.school = school

        # -------------------------------------------------
        # Only classrooms assigned to this teacher.
        # -------------------------------------------------

        assignments = TeachingAssignment.objects.filter(
            school=school,
            teacher=teacher,
        )

        classroom_ids = assignments.values_list(
            "classroom_id",
            flat=True,
        ).distinct()

        self.fields["classroom"].queryset = (
            Classroom.objects
            .filter(
                school=school,
                id__in=classroom_ids,
            )
            .select_related("academic_year")
            .order_by(
                "academic_year__name",
                "grade_level",
                "name",
            )
        )

        # -------------------------------------------------
        # Subjects assigned to this teacher.
        # -------------------------------------------------

        self.fields["subject"].queryset = Subject.objects.filter(
            school=school,
            id__in=assignments.values_list("subject_id", flat=True),
        ).order_by("name")



        # -------------------------------------------------
        # Terms belonging to the school's academic years.
        # -------------------------------------------------

        self.fields["term"].queryset = (
            Term.objects
            .filter(
                school=school,
            )
            .select_related("academic_year")
            .order_by(
                "-academic_year__start_date",
                "start_date",
            )
        )

        # -------------------------------------------------
        # When editing an existing assessment,
        # preserve the existing values.
        # -------------------------------------------------

        if self.instance.pk:
            self.fields["classroom"].initial = (
                self.instance.classroom_id
            )

            self.fields["subject"].initial = (
                self.instance.subject_id
            )

            self.fields["term"].initial = (
                self.instance.term_id
            )

    def clean(self):
        cleaned_data = super().clean()

        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")
        term = cleaned_data.get("term")
        assessment_type = cleaned_data.get(
            "assessment_type"
        )

        if not classroom or not subject or not term:
            return cleaned_data

        # -------------------------------------------------
        # 1. Verify classroom belongs to teacher assignment.
        # -------------------------------------------------

        assignment_exists = TeachingAssignment.objects.filter(
            school=self.school,
            teacher=self.teacher,
            classroom=classroom,
            subject=subject,
        ).exists()

        if not assignment_exists:
            raise ValidationError(
                "لا يمكنك إنشاء تقييم لهذه المادة وهذا الفصل."
            )

        # -------------------------------------------------
        # 2. Verify the subject is actually taught
        #    in this classroom.
        # -------------------------------------------------

        classroom_subject_exists = (
            ClassroomSubject.objects.filter(
                school=self.school,
                classroom=classroom,
                subject=subject,
            ).exists()
        )

        if not classroom_subject_exists:
            raise ValidationError(
                "هذه المادة غير مضافة إلى هذا الفصل."
            )

        # -------------------------------------------------
        # 3. Verify term belongs to classroom's
        #    academic year.
        # -------------------------------------------------

        if (
            term.academic_year_id
            != classroom.academic_year_id
        ):
            raise ValidationError(
                "الترم يجب أن يكون تابعًا للعام الدراسي الخاص بالفصل."
            )

        # -------------------------------------------------
        # 4. Find the academic scheme assigned
        #    to this classroom.
        # -------------------------------------------------

        scheme = (
            AcademicScheme.objects
            .filter(
                school=self.school,
                classrooms=classroom,
            )
            .first()
        )

        if not scheme:
            raise ValidationError(
                "لا يوجد نظام أكاديمي مرتبط بهذا الفصل."
            )

        # -------------------------------------------------
        # 5. Make sure the subject belongs to the scheme.
        # -------------------------------------------------

        if not scheme.subjects.filter(
            pk=subject.pk
        ).exists():
            raise ValidationError(
                "هذه المادة غير موجودة ضمن النظام الأكاديمي لهذا الفصل."
            )

        # -------------------------------------------------
        # 6. Find the rule for this assessment type.
        # -------------------------------------------------

        rule = (
            AcademicSchemeRule.objects
            .filter(
                school=self.school,
                scheme=scheme,
                assessment_type=assessment_type,
            )
            .first()
        )

        if not rule:
            raise ValidationError(
                "نوع التقييم المحدد غير مسموح به في النظام الأكاديمي لهذا الفصل."
            )

        # -------------------------------------------------
        # 7. Count existing assessments of this type.
        # -------------------------------------------------

        existing_assessments = Assessment.objects.filter(
            school=self.school,
            classroom=classroom,
            subject=subject,
            term=term,
            assessment_type=assessment_type,
        )

        if self.instance.pk:
            existing_assessments = (
                existing_assessments
                .exclude(pk=self.instance.pk)
            )

        existing_count = existing_assessments.count()

        if existing_count >= rule.max_count:
            assessment_type_name = dict(
                Assessment.AssessmentType.choices
            ).get(
                assessment_type,
                assessment_type,
            )

            raise ValidationError(
                f"تم الوصول إلى الحد الأقصى لعدد "
                f"{assessment_type_name} المسموح به "
                f"لهذه المادة في هذا الترم "
                f"({rule.max_count})."
            )

        return cleaned_data