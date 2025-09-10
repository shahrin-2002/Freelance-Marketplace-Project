from django.db import models
from django.utils import timezone
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.conf import settings


# -----------------------------
# Custom user manager
# -----------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        # Just reuse create_user – no is_staff/is_superuser
        return self.create_user(username, password=password, **extra_fields)


# -----------------------------
# Custom user (slim schema)
# -----------------------------
class CustomUser(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)              # PK as user_id
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    password = models.CharField(max_length=128)              # inherited from AbstractBaseUser

    is_client = models.BooleanField(default=False)
    is_freelancer = models.BooleanField(default=False)

    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "name"]

    objects = CustomUserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


# -----------------------------
# Skills
# -----------------------------
class SkillTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "skill_tags"

    def __str__(self):
        return self.name


# -----------------------------
# Projects
# -----------------------------
class Project(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="new")

    class Meta:
        db_table = "projects"

    def __str__(self):
        return self.title


# -----------------------------
# Messages between users
# -----------------------------
class Message(models.Model):
    project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name="messages",
    null=True,
    blank=True
    )
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "messages"



# -----------------------------
# Proposals and reviews
# -----------------------------
class Proposal(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="proposals"
    )
    freelancer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    class Meta:
        db_table = "proposals"

    def __str__(self):
        return f"{self.freelancer} → {self.project.title}"


class Review(models.Model):
    proposal = models.OneToOneField(
        Proposal, on_delete=models.CASCADE, related_name="review"
    )
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"

    def __str__(self):
        return f"Review for {self.proposal.freelancer.username} on {self.proposal.project.title}"

    @property
    def client(self):
        return self.proposal.project.client



# -----------------------------
# Project-skill & user-skill bridges
# -----------------------------
class ProjectSkill(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id")
    skill = models.ForeignKey(SkillTag, on_delete=models.CASCADE, db_column="skill_id")

    class Meta:
        db_table = "project_skills"
        unique_together = (("project", "skill"),)


class UserSkill(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column="user_id")
    skill = models.ForeignKey(SkillTag, on_delete=models.CASCADE, db_column="skill_id")

    class Meta:
        db_table = "user_skills"
        unique_together = (("user", "skill"),)


# Add M2M to user
CustomUser.add_to_class(
    "skills",
    models.ManyToManyField(SkillTag, through="UserSkill", blank=True),
)


# -----------------------------
# Project views
# -----------------------------
class ProjectView(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column="user_id")
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "project_views"
