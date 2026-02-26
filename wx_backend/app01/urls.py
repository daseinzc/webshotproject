from django.urls import path
from . import views

urlpatterns = [
    # === 用户与认证 ===
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change_password'), # 注意路径名加了 change

    # === 钱包 ===
    path('wallet/info/', views.WalletInfoView.as_view(), name='wallet_info'),
    path('wallet/recharge/', views.RechargeView.as_view(), name='wallet_recharge'),

    # === 任务委托 ===
    path('tasks/list/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/detail/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    
    # 发布任务 (对应 views.py 中的 PublishTaskView)
    path('tasks/publish/', views.PublishTaskView.as_view(), name='task_publish'),
    
    # ⚠️【关键修改点】: 这里改用 ClaimTaskView.as_view()
    path('tasks/claim/', views.ClaimTaskView.as_view(), name='task_claim'),
    
    path('tasks/my/', views.MyTasksView.as_view(), name='my_tasks'),
    
    path('tasks/publish/', views.PublishTaskView.as_view(), name='task_publish'),
]
