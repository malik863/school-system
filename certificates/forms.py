from django import forms
from .models import CertificateTemplate


class CertificateTemplateForm(forms.ModelForm):
    class Meta:
        model = CertificateTemplate
        fields = [
            "name",
            "background",
            "period",
            "classroom",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Certificate name",
                }
            ),
            "period": forms.Select(attrs={"class": "form-select"}),
            "classroom": forms.Select(attrs={"class": "form-select"}),
            "background": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
        }