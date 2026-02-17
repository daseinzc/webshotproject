from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Task, Transaction

# 1. 用户信息序列化
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['username', 'nickname', 'avatar', 'phone', 'gender', 'birthday', 'balance', 'credit_score']

# 2. 注册使用的序列化器
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("两次密码输入不一致")
        return data

# 3. 任务列表/详情序列化器
class TaskSerializer(serializers.ModelSerializer):
    publisher_avatar = serializers.SerializerMethodField()
    status_text = serializers.CharField(source='get_status_display', read_only=True)
    guide = serializers.ListField(source='get_guide_list', read_only=True) # 将JSON文本转为数组返给前端
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['publisher', 'worker', 'status', 'created_at']

    def get_publisher_avatar(self, obj):
        # 返回发布者的头像 URL，供列表页显示
        request = self.context.get('request')
        if obj.publisher.profile.avatar:
            return request.build_absolute_uri(obj.publisher.profile.avatar.url)
        return ""

# 4. 积分流水序列化器
class TransactionSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source='created_at', format="%Y-%m-%d %H:%M") # 格式化时间

    class Meta:
        model = Transaction
        fields = ['id', 'title', 'date', 'amount', 'trans_type']
