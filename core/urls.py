from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('post-project/', views.post_project, name='post_project'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/propose/', views.submit_proposal, name='submit_proposal'),
    path('projects/<int:project_id>/proposals/', views.view_proposals, name='view_proposals'),
    path('inbox/', views.inbox, name='inbox'),
    path('chat/<str:username>/', views.chat_detail, name='chat_detail'),
    path('proposals/<int:proposal_id>/update/', views.update_proposal_status, name='update_proposal_status'),
    path('proposals/<int:proposal_id>/review/', views.submit_review, name='submit_review'),
    path('proposals/<int:proposal_id>/review/', views.submit_review, name='submit_review'),
    path('profile/<str:username>/', views.view_profile, name='view_profile'),
    path('profile/<str:username>/edit/', views.edit_profile, name='edit_profile'),
    path('freelancers/', views.browse_freelancers, name='browse_freelancers'),
]