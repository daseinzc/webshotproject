from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import UserProfile
from .serializers import RegisterSerializer, UserProfileSerializer
from rest_framework.authtoken.models import Token # 如果使用Token认证
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
import random
from rest_framework.views import APIView
from django.db import transaction # 用于事务
from django.db.models import Sum  # <--- 必须加，否则无法计算总和
from django.db import transaction # <--- 必须加，否则无法做原子操作
from .models import UserProfile, Transaction  # <--- 必须加 Transaction
from .serializers import (
    RegisterSerializer, 
    UserProfileSerializer, 
    TransactionSerializer  # <--- 必须加 TransactionSerializer
)

# 或者简单的 Session 登录，但小程序建议用 JWT 或 Token。这里先演示标准流程。

# === 1. 注册接口 (对应 register.js) ===
class RegisterView(APIView):
    def post(self, request):

        print("收到注册请求数据:", request.data)  # 在终端打印收到的数据

        username = request.data.get('username')
        password = request.data.get('password')
        phone = request.data.get('phone')
        nickname = request.data.get('nickname')

        # 1. 校验用户是否已存在
        if User.objects.filter(username=username).exists():
            return Response({'msg': '该用户名已被注册'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. 创建 Django User
        user = User.objects.create_user(username=username, password=password)
        
        # 3. 创建关联的 UserProfile
        UserProfile.objects.create(user=user, phone=phone, nickname=nickname)

        return Response({'msg': '注册成功', 'code': 200})

# === 2. 登录接口 (对应 login.js) ===
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            # 获取或创建真实的 Token
            token, created = Token.objects.get_or_create(user=user)
            
            profile = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(profile, context={'request': request})
            
            return Response({
                'msg': '登录成功',
                'token': token.key,  # <--- 返回真实的 Token Key
                'userInfo': serializer.data
            })
        else:
            return Response({'msg': '账号或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

# === 3. 个人信息接口 (对应 profile.js & my.js) ===
class ProfileView(APIView):
    # 1. 添加认证和权限控制
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 2. 获取当前登录用户 (Token 校验通过后，request.user 就是当前用户)
        user = request.user 
        
        # 获取关联的 profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return Response({'msg': '用户资料不存在'}, status=404)

        serializer = UserProfileSerializer(profile, context={'request': request})

        # 我们也可以手动把 User 模型里的 username/email 拼进去
        data = serializer.data
        data['username'] = user.username
        data['email'] = user.email
        data['uid_tag'] = profile.uid_tag
        data['full_nickname'] = f"{profile.nickname}#{profile.uid_tag}"
        
        return Response(data)


    def post(self, request):
        # 修改个人信息
        user = request.user # 获取当前用户
        profile = user.profile
        
        # 1. 获取前端传来的新数据
        new_nickname = request.data.get('nickname')
        new_gender = request.data.get('gender')
        new_birthday = request.data.get('birthday')

        # 2. 处理昵称修改逻辑
        if new_nickname and new_nickname != profile.nickname:
            # 检查 "新昵称 + 当前Tag" 是否已被占用
            is_taken = UserProfile.objects.filter(
                nickname=new_nickname, 
                uid_tag=profile.uid_tag
            ).exclude(user=user).exists() # 排除自己（虽然逻辑上自己还没改名，但这步是个保险）

            if is_taken:
                # 冲突了！(例如我也想改名叫"张三"，但我原本的尾号是8888，而已经有一个"张三#8888"了)
                # 策略：强制生成一个新的 Tag 给当前用户
                profile.nickname = new_nickname
                profile.uid_tag = profile.generate_unique_tag() # 调用 Model 里写好的生成方法
                print(f"昵称冲突，已自动为用户分配新尾号: {profile.uid_tag}")
            else:
                # 没冲突，直接改名，尾号不变
                profile.nickname = new_nickname
        # 3. 处理其他字段
        if new_gender:
            profile.gender = new_gender
        if new_birthday:
            profile.birthday = new_birthday

        # 4. 保存
        profile.save()
        
        # 5. 返回最新的数据（包括可能变化了的 Tag）
        return Response({
            'msg': '修改成功', 
            'code': 200,
            'data': {
                'nickname': profile.nickname,
                'uid_tag': profile.uid_tag,
                'full_nickname': f"{profile.nickname}#{profile.uid_tag}"
            }
        })

# === 4. 修改密码接口 (对应 password.js) ===
class ChangePasswordView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # 1. 后端二次校验空值 (防止绕过前端校验)
        if not old_password or not new_password:
            return Response({'msg': '参数不完整'}, status=400)

        # 2. 校验旧密码
        if not user.check_password(old_password):
            return Response({'msg': '原密码错误，请重试'}, status=400)

        # 3. 设置新密码
        # 建议：这里也可以加上后端的新密码正则校验，为了安全起见
        user.set_password(new_password)
        user.save()

        return Response({'msg': '密码修改成功', 'code': 200})
    
# === 5. 钱包首页接口：获取余额、统计和流水 ===
class WalletInfoView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # === 修复逻辑：获取或创建 ===
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            # 老用户没有档案，自动初始化
            profile = UserProfile.objects.create(user=user, balance=10000)
        # ==========================

        # 下面的代码保持不变...
        income = Transaction.objects.filter(user=user, trans_type='income').aggregate(s=Sum('amount'))['s'] or 0
        expense = Transaction.objects.filter(user=user, trans_type='expense').aggregate(s=Sum('amount'))['s'] or 0

        trans_qs = Transaction.objects.filter(user=user).order_by('-created_at')[:20]
        serializer = TransactionSerializer(trans_qs, many=True)

        return Response({
            'code': 200,
            'data': {
                'total_balance': profile.balance,
                'total_income': income,
                'total_expense': expense,
                'list': serializer.data 
            }
        })

# === 6. 充值接口：执行加钱逻辑 ===
class RechargeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        price = request.data.get('price')

        # 1. 基础校验
        if not price:
            return Response({'msg': '参数错误'}, status=400)
        try:
            price_val = float(price)
            if price_val <= 0: raise ValueError
        except:
            return Response({'msg': '金额无效'}, status=400)

        points = int(price_val * 100)

        try:
            with transaction.atomic():
                # 尝试获取 Profile，如果是老用户没有Profile，则自动创建
                # select_for_update 在 get_or_create 中使用需要注意，这里为了稳健我们拆开写
                
                try:
                    # 尝试带锁查询（针对有账号的人）
                    profile = UserProfile.objects.select_for_update().get(user=user)
                except UserProfile.DoesNotExist:
                    # 如果报错说找不到，说明是老账号，立刻创建一个补救
                    # 默认余额在 models.py 里已经是 10000 了，这里不用特意指定，或者指定也行
                    profile = UserProfile.objects.create(
                        user=user, 
                        balance=10000, 
                        nickname=user.username  # 默认用账号名做昵称
                    )
                    print(f"检测到老用户 {user.username} 无档案，已自动补全")
                

                # 2. 执行充值 (在现有余额基础上增加)
                profile.balance += points
                profile.save()

                # 3. 写入流水
                Transaction.objects.create(
                    user=user,
                    title='账户充值',
                    amount=points,
                    trans_type='income'
                )

        except Exception as e:
            print(f"充值报错: {e}")
            return Response({'msg': '系统繁忙，请重试'}, status=500)

        return Response({'code': 200, 'msg': '充值成功', 'new_balance': profile.balance})
