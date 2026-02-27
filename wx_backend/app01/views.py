from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token 
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum, Q 
import random
from django.db import transaction 

from .models import UserProfile, Transaction, Task
from .serializers import (
    RegisterSerializer, 
    UserProfileSerializer, 
    TransactionSerializer,
    TaskSerializer,
    TaskPublishSerializer 
)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        phone = request.data.get('phone')
        nickname = request.data.get('nickname')

        if User.objects.filter(username=username).exists():
            return Response({'msg': '该用户名已被注册'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, phone=phone, nickname=nickname)

        return Response({'msg': '注册成功', 'code': 200})

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            profile = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(profile, context={'request': request})
            
            return Response({
                'msg': '登录成功',
                'token': token.key,
                'userInfo': serializer.data
            })
        else:
            return Response({'msg': '账号或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({'msg': '用户资料不存在'}, status=404)

        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        profile = request.user.profile
        new_nickname = request.data.get('nickname')
        new_gender = request.data.get('gender')
        new_birthday = request.data.get('birthday')

        if new_nickname and new_nickname != profile.nickname:
            is_taken = UserProfile.objects.filter(nickname=new_nickname, uid_tag=profile.uid_tag).exclude(user=request.user).exists()
            if is_taken:
                profile.nickname = new_nickname
                profile.uid_tag = profile.generate_unique_tag()
            else:
                profile.nickname = new_nickname
        
        if new_gender: profile.gender = new_gender
        if new_birthday: profile.birthday = new_birthday
        profile.save()
        
        return Response({'msg': '修改成功', 'code': 200, 'data': {'nickname': profile.nickname}})

class ChangePasswordView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'msg': '原密码错误'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'msg': '密码修改成功', 'code': 200})

class WalletInfoView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user, balance=10000)

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

class RechargeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            price = float(request.data.get('price'))
            if price <= 0: raise ValueError
        except:
            return Response({'msg': '金额无效'}, status=400)

        points = int(price * 100)

        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            profile.balance += points
            profile.save()

            Transaction.objects.create(user=user, title='账户充值', amount=points, trans_type='income')

        return Response({'code': 200, 'msg': '充值成功', 'new_balance': profile.balance})

class TaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Task.objects.filter(status='pending').order_by('-created_at')
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(desc__icontains=keyword))
        sort = self.request.query_params.get('sort', '0')
        if sort == '1': 
            qs = qs.order_by('-price')
        return qs
    
    def get_serializer_context(self):
        return {'request': self.request}

class TaskDetailView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_context(self):
        return {'request': self.request}

# 终极合并版 PublishTaskView
class PublishTaskView(generics.CreateAPIView):
    serializer_class = TaskPublishSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 400, 
                'msg': '数据校验失败', 
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        price = data.get('price')
        user = request.user

        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=user)
                
                if profile.balance < price:
                    return Response({'code': 400, 'msg': '账户余额不足，请先充值'}, status=200)

                profile.balance -= price
                profile.save()

                task = serializer.save(publisher=user, status='pending')

                Transaction.objects.create(
                    user=user,
                    title=f"发布任务-{data.get('title')}",
                    amount=price,
                    trans_type='expense' 
                )
            
            return Response({
                'code': 200, 
                'msg': '发布成功', 
                'data': {'id': task.id}
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"发布失败: {e}")
            return Response({'code': 500, 'msg': '服务器内部错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClaimTaskView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        task_id = request.data.get('task_id')
        user = request.user

        if not task_id:
            return Response({'msg': '缺少任务ID'}, status=400)

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update().get(id=task_id)
            except Task.DoesNotExist:
                return Response({'code': 404, 'msg': '任务不存在'})

            if task.status != 'pending':
                return Response({'code': 400, 'msg': '任务已被抢或已过期'})
            
            if task.publisher == user:
                return Response({'code': 400, 'msg': '不能领取自己的任务'})

            task.worker = user
            task.status = 'ongoing'
            task.save()
            
            return Response({'code': 200, 'msg': '领取成功'})

class MyTasksView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get('role', 'publisher')
        user = request.user
        
        if role == 'publisher':
            tasks = Task.objects.filter(publisher=user).order_by('-created_at')
        else:
            tasks = Task.objects.filter(worker=user).order_by('-created_at')
            
        serializer = TaskSerializer(tasks, many=True, context={'request': request})
        return Response({'code': 200, 'data': serializer.data})
    


class UploadVideoView(APIView):
    """拍客上传视频接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        video_file = request.FILES.get('video')  # 获取前端传来的视频文件
        
        if not video_file:
            return Response({'code': 400, 'msg': '请上传视频文件'})

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update().get(id=pk)
            except Task.DoesNotExist:
                return Response({'code': 404, 'msg': '任务不存在'})

            if task.worker != user:
                return Response({'code': 403, 'msg': '无权操作此任务'})
            if task.status != 'ongoing':
                return Response({'code': 400, 'msg': '任务不在进行中，无法上传'})

            # 保存视频，状态保持 ongoing，等待发布者验收
            task.result_video = video_file
            task.save()

        return Response({'code': 200, 'msg': '上传成功，等待发布者验收', 'video_url': task.result_video.url})


class AcceptTaskView(APIView):
    """发布者确认验收并结算接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update().get(id=pk)
            except Task.DoesNotExist:
                return Response({'code': 404, 'msg': '任务不存在'})

            if task.publisher != user:
                return Response({'code': 403, 'msg': '无权操作此任务'})
            if task.status != 'ongoing':
                return Response({'code': 400, 'msg': '任务不在进行中或已验收'})
            if not task.result_video:
                return Response({'code': 400, 'msg': '拍客尚未上传视频，无法验收'})

            # 1. 改变任务状态为已完成
            task.status = 'completed'
            task.save()

            # 2. 给接单者(拍客)结算积分
            worker_profile = UserProfile.objects.select_for_update().get(user=task.worker)
            worker_profile.balance += task.price
            worker_profile.save()

            # 3. 记录接单者的收入流水
            Transaction.objects.create(
                user=task.worker,
                title=f"完成任务验收收益-{task.title}",
                amount=task.price,
                trans_type='income'
            )

        return Response({'code': 200, 'msg': '验收成功，积分已结算'})
