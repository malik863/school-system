from django import forms

from assessments.models import Assessment, Grade


class GradeEntryForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = [
            "student",
            "assessment",
            "score",
        ]

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school is not None:
            self.fields["student"].queryset = (
                self.fields["student"]
                .queryset
                .filter(school=school)
            )

            self.fields["assessment"].queryset = (
                self.fields["assessment"]
                .queryset
                .filter(school=school)
            )

    def clean(self):
        cleaned_data = super().clean()

        student = cleaned_data.get("student")
        assessment = cleaned_data.get("assessment")
        score = cleaned_data.get("score")

        if student and assessment:
            if student.classroom_id != assessment.classroom_id:
                raise forms.ValidationError(
                    "الطالب ليس في فصل هذا التقييم."
                )

        if assessment and score is not None:
            if score > assessment.max_score:
                self.add_error(
                    "score",
                    "الدرجة لا يمكن أن تتجاوز الدرجة النهائية."
                )

        return cleaned_data