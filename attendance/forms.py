
from django import forms
from academics.models import Classroom


class AttendanceForm(forms.Form):

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.none(),
        label="الفصل",
        empty_label="اختر الفصل",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    date = forms.DateField(
        label="التاريخ",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    def __init__(
        self,
        *args,
        teacher=None,
        students=None,
        initial_attendance=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.teacher = teacher

        # Only classes where this teacher is the lead teacher
        if teacher is not None:
            self.fields["classroom"].queryset = (
                Classroom.objects
                .filter(
                    school=teacher.school,
                    lead_teacher=teacher,
                )
                .select_related("academic_year")
                .order_by(
                    "grade_level",
                    "name",
                )
            )

        self.student_fields = []

        if students is not None:

            initial_attendance = initial_attendance or {}

            for student in students:

                field_name = f"student_{student.pk}"

                self.fields[field_name] = forms.ChoiceField(
                    label=str(student),
                    choices=[
                        ("present", "حاضر"),
                        ("absent", "غائب"),
                        ("late", "متأخر"),
                        ("excused", "بعذر"),
                    ],
                    initial=initial_attendance.get(
                        student.pk,
                        "present",
                    ),
                    widget=forms.Select(
                        attrs={
                            "class": "form-select",
                        }
                    ),
                )

                self.student_fields.append(
                    (
                        student,
                        self[field_name],
                    )
                )