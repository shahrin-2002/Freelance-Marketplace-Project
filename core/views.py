from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from .forms import ProjectForm
from .models import Project
from django.contrib.auth.decorators import login_required
from .models import Proposal, SkillTag, Review
from .forms import ProposalForm
from django.http import Http404
from .models import Message
from .forms import MessageForm
from django.contrib.auth.decorators import login_required
from .forms import ProjectForm, ProposalForm, MessageForm, ReviewForm
from django.http import HttpResponse
from django.db.models import Q, Max
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from .models import Message, CustomUser
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .forms import MessageForm
from django.db.models import Q
from .forms import ProfileForm
from .models import ProjectSkill
from django.db import transaction
from .models import Proposal, Project


def home(request):
    return HttpResponse("Welcome to the Freelance Marketplace!")

def home(request):
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        role = request.POST['role']

        # Check if username already exists
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

        except IntegrityError:
            messages.error(request, "Registration failed. Please try again.")
            return render(request, 'core/register.html')

    return render(request, 'core/register.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user

    if user.is_client:
        # Get all projects posted by the client
        projects = Project.objects.filter(client=user).order_by('-created_at')

        # Get all proposals sent to those projects
        proposals = Proposal.objects.filter(project__client=user).select_related('project', 'freelancer').order_by('-submitted_at')

        return render(request, 'core/client_dashboard.html', {
            'user': user,
            'projects': projects,
            'proposals': proposals
        })

    elif user.is_freelancer:
        proposals = Proposal.objects.filter(freelancer=user).select_related('project').order_by('-submitted_at')
        reviews = Review.objects.filter(proposal__freelancer=user).select_related('proposal__project', 'proposal__project__client')
        return render(request, 'core/freelancer_dashboard.html', {
            'user': user,
            'proposals': proposals,
            'reviews': reviews
        })

    return redirect('home')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def post_project(request):
    if not request.user.is_client:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.client = request.user
            project.save()

            # Create through-table rows for selected skills
            selected_skills = form.cleaned_data.get('skills', [])
            ProjectSkill.objects.filter(project=project).delete()
            ProjectSkill.objects.bulk_create(
                [ProjectSkill(project=project, skill=s) for s in selected_skills]
            )

            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'core/post_project.html', {'form': form})

def project_list(request):
    skill_filter = request.GET.get('skill')
    if skill_filter:
        projects = Project.objects.filter(
            projectskill__skill__name__iexact=skill_filter
        ).distinct()
    else:
        projects = Project.objects.all().order_by('-created_at')

    skills = SkillTag.objects.all()
    return render(request, 'core/project_list.html', {'projects': projects, 'skills': skills})


    skills = SkillTag.objects.order_by('name')
    return render(request, 'core/project_list.html', {'projects': projects, 'skills': skills})


def project_detail(request, project_id):
    project = Project.objects.get(id=project_id)
    return render(request, 'core/project_detail.html', {'project': project})

@login_required
def submit_proposal(request, project_id):
    if not request.user.is_freelancer:
        return redirect('dashboard')

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise Http404("Project not found")

    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.freelancer = request.user
            proposal.project = project
            proposal.save()
            return redirect('project_list')
    else:
        form = ProposalForm()

    return render(request, 'core/submit_proposal.html', {'form': form, 'project': project})

@login_required
def view_proposals(request, project_id):
    project = Project.objects.get(id=project_id)

    # Only allow the client who owns the project to view its proposals
    if request.user != project.client:
        return redirect('dashboard')

    proposals = Proposal.objects.filter(project=project).order_by('-submitted_at')
    return render(request, 'core/view_proposals.html', {'project': project, 'proposals': proposals})

@login_required
def inbox(request):
    user = request.user

    if user.is_client:
        # Get freelancers who submitted proposals to this client's projects
        client_projects = Project.objects.filter(client=user)
        proposals = Proposal.objects.filter(project__in=client_projects).select_related('freelancer')
        chat_users = set(p.freelancer for p in proposals)

    elif user.is_freelancer:
        # Get clients whose projects the freelancer submitted proposals to
        proposals = Proposal.objects.filter(freelancer=user).select_related('project__client')
        chat_users = set(p.project.client for p in proposals)

    else:
        chat_users = set()

    return render(request, 'core/inbox.html', {'chat_users': chat_users})


@login_required
def chat_detail(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    user = request.user

    messages = Message.objects.filter(
        Q(sender=user, receiver=other_user) |
        Q(sender=other_user, receiver=user)
    ).order_by('timestamp')

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = user
            message.receiver = other_user  # 👈 set automatically, no dropdown
            message.save()
            return redirect('chat_detail', username=other_user.username)
    else:
        form = MessageForm()

    return render(request, 'core/chat_detail.html', {
        'messages': messages,
        'form': form,
        'other_user': other_user,
    })



@login_required
@require_POST
@transaction.atomic
def update_proposal_status(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)

    if proposal.project.client != request.user:
        return HttpResponseForbidden("You do not have permission to modify this proposal.")

    action = request.POST.get('action')

    if action == 'accept':
        # 1) mark proposal accepted
        Proposal.objects.filter(pk=proposal.id).update(status='accepted')

        # 2) mark project ongoing (DB-level update)
        Project.objects.filter(pk=proposal.project_id).update(status='ongoing')

        # 3) optionally reject others
        Proposal.objects.filter(project_id=proposal.project_id)\
                        .exclude(pk=proposal.id).update(status='rejected')

        messages.success(request, "Proposal accepted. Project is now ongoing.")

    elif action == 'reject':
        Proposal.objects.filter(pk=proposal.id).update(status='rejected')
        messages.info(request, "Proposal rejected.")

    return redirect('dashboard')

@login_required
@transaction.atomic
def submit_review(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)

    if proposal.project.client != request.user:
        return HttpResponseForbidden("You can’t review this proposal.")

    if hasattr(proposal, 'review'):
        messages.warning(request, "You've already reviewed this proposal.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.proposal = proposal
            review.save()

            # ➜ After review, mark project COMPLETED
            project = proposal.project
            project.status = 'completed'
            project.save(update_fields=['status'])

            messages.success(request, "Review submitted. Project marked as completed.")
            return redirect('dashboard')
    else:
        form = ReviewForm()

    return render(request, 'core/submit_review.html', {
        'form': form,
        'proposal': proposal
    })

@login_required
def view_profile(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    return render(request, 'core/view_profile.html', {
        'profile_user': profile_user
    })

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
    freelancers = CustomUser.objects.filter(is_freelancer=True)

    if query:
        freelancers = freelancers.filter(
            Q(username__icontains=query) |
            Q(location__icontains=query) |
            Q(skills__name__icontains=query)
        ).distinct()

    return render(request, 'core/browse_freelancers.html', {
        'freelancers': freelancers,
        'query': query
    })