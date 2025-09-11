from django import forms
from .models import Project, Proposal, SkillTag, Message
from .models import Review
from django import forms
from .models import CustomUser

class ProjectForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=SkillTag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skills"].queryset = SkillTag.objects.all()
        self.fields["title"].widget = forms.TextInput(attrs={
            "class": "mt-2 w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
        })
        self.fields["description"].widget = forms.Textarea(attrs={
            "rows": 7,
            "class": "mt-2 w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
        })
        self.fields["budget"].widget = forms.NumberInput(attrs={
            "min": "0",
            "step": "1",
            "class": "mt-2 w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
        })

    class Meta:
        model = Project
        fields = ["title", "description", "budget", "skills"]


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ["message", "proposed_price"]


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["text", "attachment"]
        widgets = {"text": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for unwanted in ("receiver", "project", "sender"):
            if unwanted in self.fields:
                self.fields.pop(unwanted)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"rating": forms.RadioSelect(choices=[(i, f"{i} Stars") for i in range(1, 6)])}


class ProfileForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=SkillTag.objects.order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = CustomUser
        fields = ["name", "email", "location", "bio", "skills"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance") or getattr(self, "instance", None)
        if instance and not getattr(instance, "is_freelancer", False):
            self.fields.pop("skills", None)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if "skills" in self.cleaned_data and hasattr(user, "skills"):
            user.skills.set(self.cleaned_data["skills"])
        return user