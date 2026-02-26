# === Python代码文件: serializers.py ===

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Task, Transaction

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_avatar = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        # 【修复点1】：这里加入了 'uid_tag'，让前端能拿到真实的4位数尾号
        fields = [
            'username', 'nickname', 'uid_tag', 'avatar', 'full_avatar', 
            'phone', 'gender', 'birthday', 'balance', 'credit_score'
        ]

    def get_full_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return "https://img.yzcdn.cn/vant/cat.jpeg"

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

class TaskSerializer(serializers.ModelSerializer):
    publisher = serializers.SerializerMethodField()
    status_text = serializers.CharField(source='get_status_display', read_only=True)
    guide = serializers.ListField(source='get_guide_list', read_only=True)
    deadline_display = serializers.SerializerMethodField()
    specs = serializers.SerializerMethodField()

    class Meta:
        model = Task
        # 【修复点2】：这里在末尾加入了 'guide'，彻底解决 500 崩溃报错
        fields = [
            'id', 'title', 'desc', 'price', 'deadline', 
            'location_name', 'location_address', 'detail_address',
            'latitude', 'longitude', 
            'task_type', 'language', 'video_specs', 'orientation', 
            'publisher', 'status_text', 'deadline_display', 'specs', 'status', 
            'guide' 
        ]
        read_only_fields = ['worker', 'status', 'created_at']

    def get_publisher(self, obj):
        profile = obj.publisher.profile
        avatar_url = "https://img.yzcdn.cn/vant/cat.jpeg"
        if profile.avatar:
            request = self.context.get('request')
            if request:
                avatar_url = request.build_absolute_uri(profile.avatar.url)
            else:
                try:
                    avatar_url = profile.avatar.url
                except:
                    pass
        return {
            "name": profile.nickname,
            "avatar": avatar_url
        }

    def get_deadline_display(self, obj):
        return obj.deadline.strftime("%m月%d日 %H:%M")

    def get_specs(self, obj):
        # 你的语言字段加回来啦！！
        return [
            { 'label': '委托类型', 'value': obj.task_type },
            { 'label': '语言要求', 'value': obj.language }, 
            { 'label': '画幅要求', 'value': obj.get_orientation_display() }, 
            { 'label': '画质规格', 'value': obj.video_specs },
            { 'label': '截止时间', 'value': obj.deadline.strftime("%m-%d %H:%M") }
        ]

class TransactionSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source='created_at', format="%Y-%m-%d %H:%M")

    class Meta:
        model = Transaction
        fields = ['id', 'title', 'date', 'amount', 'trans_type']

class TaskPublishSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=100, required=True)
    desc = serializers.CharField(required=True)
    price = serializers.IntegerField(required=True)
    deadline = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=True)
    orientation = serializers.CharField(required=True) 

    class Meta:
        model = Task
        fields = [
            'title', 'desc', 'price', 'deadline', 
            'location_name', 'location_address', 'detail_address',
            'latitude', 'longitude', 
            'task_type', 'language', 'video_specs', 'orientation' 
        ]
        extra_kwargs = {
            'detail_address': {'required': False, 'allow_blank': True},
            'video_specs': {'required': False, 'default': '1080P'},
            'language': {'required': False, 'default': '普通话'} 
        }

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("任务积分必须大于0")
        return value

    def validate_deadline(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("截止时间不能早于当前时间")
        return value
