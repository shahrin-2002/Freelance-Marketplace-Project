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

from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'attachment']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for unwanted in ('receiver', 'project', 'sender'):
            if unwanted in self.fields:
                self.fields.pop(unwanted)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i} Stars") for i in range(1, 6)])
        }

from django import forms
from .models import CustomUser, SkillTag

class ProfileForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=SkillTag.objects.order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'location', 'bio', 'skills']  # 'name' kept

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance') or getattr(self, 'instance', None)
        if instance and not getattr(instance, 'is_freelancer', False):
            # remove from the form entirely (won't render and won't validate)
            self.fields.pop('skills', None)
