from django import forms
from .models import Project, Proposal, SkillTag, Message
from .models import Review
from django import forms
from .models import CustomUser

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

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i} Stars") for i in range(1, 6)])
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'location', 'bio','skills']
        widgets = {
            'skills': forms.CheckboxSelectMultiple
        }
