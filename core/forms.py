from django import forms
from .models import Project, Proposal, SkillTag, Message

class ProjectForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=SkillTag.objects.none(),  # temporarily empty
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = SkillTag.objects.all()  # loaded dynamically

    class Meta:
        model = Project
        fields = ['title', 'description', 'budget', 'skills']

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['message', 'proposed_price']

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['receiver', 'text', 'attachment']