# 文件路径：wx_backend/app01/urls.py
from django.urls import path
from . import views

# 这里暂时留空，以后你的接口写在这里
urlpatterns = [
    # 认证相关
    path('register/', views.RegisterView.as_view(), name='register'), # 注册
    path('login/', views.LoginView.as_view(), name='login'),          # 登录
    path('profile/', views.ProfileView.as_view(), name='profile'),    # 个人信息
    path('password/', views.ChangePasswordView.as_view(), name='change_password'),                  # 修改密码    
]
