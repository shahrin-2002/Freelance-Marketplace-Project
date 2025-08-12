from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Create your models here.

class CustomUser(AbstractUser):
    is_client = models.BooleanField(default=False)
    is_freelancer = models.BooleanField(default=False)

    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    skills = models.ManyToManyField('SkillTag', blank=True)

    def __str__(self):
        return self.username

class SkillTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name   
      
class Project(models.Model):
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    skills = models.ManyToManyField(SkillTag, blank=True)  

    def __str__(self):
        return self.title
    
# class Proposal(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='proposals')
#     freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     message = models.TextField()
#     proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
#     submitted_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.freelancer.username} → {self.project.title}"
    
class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.sender} to {self.receiver}: {self.text[:30]}"
    
class Proposal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='proposals')
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    #review = models.OneToOneField('Review', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.freelancer.username} → {self.project.title}"
    
class Review(models.Model):
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])  # 1 to 5 stars
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.proposal.freelancer.username} on {self.proposal.project.title}"