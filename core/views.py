from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Avg, Q
from django.db import models

from .models import (
    CustomUser,
    Project,
    Proposal,
    Review,
    SkillTag,
    Message,
    ProjectSkill,
)
from .forms import (
    ProjectForm,
    ProposalForm,
    MessageForm,
    ReviewForm,
    ProfileForm,
)


def start(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def home(request):
    return render(request, 'core/home.html')


@never_cache
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        role = request.POST['role']

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'core/register.html')

        try:
            user = CustomUser.objects.create_user(username=username, password=password)
            if role == 'client':
                user.is_client = True
            else:
                user.is_freelancer = True
            user.save()
            login(request, user)
            return redirect('dashboard')
        except Exception:
            messages.error(request, "Registration failed. Please try again.")
            return render(request, 'core/register.html')

    return render(request, 'core/register.html')


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


@never_cache
@login_required
def dashboard(request):
    user = request.user

    if user.is_client:
        projects = Project.objects.filter(client=user).order_by('-created_at')
        proposals = (
            Proposal.objects
            .filter(project__client=user)
            .select_related('project', 'freelancer')
            .order_by('-submitted_at')
        )
        return render(request, 'core/client_dashboard.html', {
            'user': user,
            'projects': projects,
            'proposals': proposals,
        })

    if user.is_freelancer:
        proposals = (
            Proposal.objects
            .filter(freelancer=user)
            .select_related('project')
            .order_by('-submitted_at')
        )
        reviews = Review.objects.filter(
            proposal__freelancer=user
        ).select_related('proposal__project', 'proposal__project__client')
        return render(request, 'core/freelancer_dashboard.html', {
            'user': user,
            'proposals': proposals,
            'reviews': reviews,
        })

    return redirect('home')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def post_project(request):
    if not getattr(request.user, "is_client", False):
        return redirect("dashboard")

    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                project = form.save(commit=False)
                project.client = request.user
                project.save()

                ProjectSkill.objects.filter(project=project).delete()
                skills_qs = form.cleaned_data.get("skills")
                if skills_qs:
                    ProjectSkill.objects.bulk_create(
                        [ProjectSkill(project=project, skill=s) for s in skills_qs]
                    )

            return redirect("project_list")
    else:
        form = ProjectForm()

    return render(request, "core/post_project.html", {"form": form})


def project_list(request):
    skill_filter = request.GET.get('skill')
    status_filter = request.GET.get('status')

    projects = Project.objects.all()

    if skill_filter:
        projects = projects.filter(
            projectskill__skill__name__iexact=skill_filter
        )

    if status_filter in ["new", "ongoing", "completed"]:
        projects = projects.filter(status=status_filter)

    projects = projects.order_by('-created_at')
    skills = SkillTag.objects.order_by('name')

    return render(request, 'core/project_list.html', {
        'projects': projects,
        'skills': skills
    })


def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'core/project_detail.html', {
        'project': project,
    })


@never_cache
@login_required
def submit_proposal(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.status != "new":
        messages.error(request, "You can only submit proposals on new projects.")
        return redirect("project_detail", project_id=project.id)

    if request.method == "POST":
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.project = project
            proposal.freelancer = request.user
            proposal.save()

            # Optional: seed a chat message to the client when a proposal is submitted
            Message.objects.create(
                sender=request.user,
                receiver=project.client,
                text=f"Hello {project.client.username}, I just submitted a proposal for “{project.title}”."
            )

            messages.success(request, "Proposal submitted successfully!")
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProposalForm()

    return render(request, "core/submit_proposal.html", {"form": form, "project": project})

@never_cache
@login_required
def view_proposals(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user != project.client:
        return redirect('dashboard')

    proposals = Proposal.objects.filter(project=project).order_by('-submitted_at')
    return render(request, 'core/view_proposals.html', {'project': project, 'proposals': proposals})


@never_cache
@login_required
def inbox(request):
    user = request.user

    partner_ids = set()

    if user.is_client:
        partner_ids.update(
            Proposal.objects.filter(project__client=user)
            .values_list("freelancer_id", flat=True)
        )
    if user.is_freelancer:
        partner_ids.update(
            Proposal.objects.filter(freelancer=user)
            .values_list("project__client_id", flat=True)
        )

    partner_ids.update(
        Message.objects.filter(sender=user).values_list("receiver_id", flat=True)
    )
    partner_ids.update(
        Message.objects.filter(receiver=user).values_list("sender_id", flat=True)
    )

    partners = CustomUser.objects.filter(pk__in=partner_ids)

    from django.db.models import Max, Q
    rows = []
    for p in partners:
        last = (
            Message.objects.filter(
                Q(sender=user, receiver=p) | Q(sender=p, receiver=user)
            ).aggregate(last=Max("timestamp"))["last"]
        )
        rows.append((p, last))

    rows.sort(key=lambda x: (x[1] is None, x[1]), reverse=True)
    chats = [{"user": u, "last": ts} for u, ts in rows]

    return render(request, "core/inbox.html", {"chats": chats})



@never_cache
@login_required
def chat_detail(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    user = request.user

    msgs = Message.objects.filter(
        Q(sender=user, receiver=other_user) |
        Q(sender=other_user, receiver=user)
    ).order_by('timestamp')

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            m = form.save(commit=False)
            m.sender = user
            m.receiver = other_user
            m.save()
            return redirect('chat_detail', username=other_user.username)
    else:
        form = MessageForm()

    return render(request, 'core/chat_detail.html', {
        'messages': msgs,
        'form': form,
        'other_user': other_user,
    })


@never_cache
@login_required
@require_POST
@transaction.atomic
def update_proposal_status(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)

    if proposal.project.client != request.user:
        return HttpResponseForbidden("You do not have permission to modify this proposal.")

    action = request.POST.get("action")

    if action == "accept":
        # 1) accept this proposal
        Proposal.objects.filter(pk=proposal.id).update(status="accepted")
        # 2) mark project ongoing
        Project.objects.filter(pk=proposal.project_id).update(status="ongoing")
        # 3) reject all other proposals for this project
        Proposal.objects.filter(project_id=proposal.project_id).exclude(pk=proposal.id).update(status="rejected")

        # 4) seed a chat (NO 'project' kwarg anymore)
        Message.objects.create(
            sender=request.user,
            receiver=proposal.freelancer,
            text=f"Hi {proposal.freelancer.username}, I’ve accepted your proposal for “{proposal.project.title}”."
        )

        messages.success(request, "Proposal accepted. Project is now ongoing.")

    elif action == "reject":
        Proposal.objects.filter(pk=proposal.id).update(status="rejected")
        messages.info(request, "Proposal rejected.")

    return redirect("dashboard")

@never_cache
@login_required
@transaction.atomic
def submit_review(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)

    # Only the project client can review
    if proposal.project.client != request.user:
        return HttpResponseForbidden("You can’t review this proposal.")

    # Prevent duplicate review
    if hasattr(proposal, 'review'):
        messages.warning(request, "You've already reviewed this proposal.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.proposal = proposal
            review.save()

            # Mark project completed
            project = proposal.project
            project.status = 'completed'
            project.save(update_fields=['status'])

            # 🔔 Notify freelancer (NO 'project=' kwarg here)
            Message.objects.create(
                sender=request.user,
                receiver=proposal.freelancer,
                text=f"{request.user.username} left a {review.rating}/5 review on '{project.title}': {review.comment}"
            )

            messages.success(request, "Review submitted. Project marked as completed.")
            return redirect('dashboard')
    else:
        form = ReviewForm()

    return render(request, 'core/submit_review.html', {
        'form': form,
        'proposal': proposal
    })


@never_cache
@login_required
def view_profile(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)

    reviews = []
    avg_rating = None
    if profile_user.is_freelancer:
        reviews = Review.objects.filter(
            proposal__freelancer=profile_user
        ).select_related("proposal__project", "proposal__freelancer")
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg("rating"))["rating__avg"]

    return render(request, "core/view_profile.html", {
        "profile_user": profile_user,
        "reviews": reviews,
        "avg_rating": avg_rating,
    })


@never_cache
@login_required
def edit_profile(request, username):
    user = get_object_or_404(CustomUser, username=username)

    if user != request.user:
        return HttpResponseForbidden("You can only edit your own profile.")

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('view_profile', username=user.username)
    else:
        form = ProfileForm(instance=user)

    return render(request, 'core/edit_profile.html', {'form': form})


def browse_freelancers(request):
    query = request.GET.get('q', '')

    freelancers = (
        CustomUser.objects
        .filter(is_freelancer=True)
        .annotate(avg_rating=Avg('proposal__review__rating'))  # rating from accepted/completed reviews
        .prefetch_related('skills')
    )

    if query:
        freelancers = freelancers.filter(
            Q(username__icontains=query) |
            Q(location__icontains=query) |
            Q(skills__name__icontains=query)
        ).distinct()

    freelancers = freelancers.order_by('-avg_rating', 'username')

    return render(request, 'core/browse_freelancers.html', {
        'freelancers': freelancers,
        'query': query,
    })