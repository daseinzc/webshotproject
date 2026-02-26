from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import random

# ==========================================
# 1. 用户与账户模块 (User & Profile)
# ==========================================
class UserProfile(models.Model):
    """
    用户扩展信息表
    """
    GENDER_CHOICES = (
        ('男', '男'),
        ('女', '女'),
        ('未知', '未知'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    nickname = models.CharField(max_length=50, verbose_name='昵称', default='微信用户')
    uid_tag = models.CharField(max_length=4, default='0000', verbose_name='UID尾号')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', verbose_name='头像')
    phone = models.CharField(max_length=20, unique=True, verbose_name='手机号')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='未知', verbose_name='性别')
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    
    balance = models.IntegerField(default=10000, verbose_name='积分余额') 
    credit_score = models.IntegerField(default=100, verbose_name='信用分')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')

    class Meta:
        unique_together = ('nickname', 'uid_tag')
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.nickname}#{self.uid_tag}"

    def save(self, *args, **kwargs):
        if not self.uid_tag or self.uid_tag == '0000':
            self.uid_tag = self.generate_unique_tag()
        super().save(*args, **kwargs)

    def generate_unique_tag(self):
        while True:
            new_tag = f"{random.randint(1, 9999):04d}"
            if not UserProfile.objects.filter(nickname=self.nickname, uid_tag=new_tag).exists():
                return new_tag

# ==========================================
# 2. 任务委托模块 (Task)
# ==========================================
class Task(models.Model):
    """
    任务委托表
    """
    STATUS_CHOICES = (
        ('pending', '待确认'),  
        ('ongoing', '进行中'),  
        ('completed', '已完成'), 
        ('expired', '已过期'),   
    )

    ORIENTATION_CHOICES = (
        ('portrait', '竖屏 (9:16)'),   
        ('landscape', '横屏 (16:9)'),  
    )

    publisher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='published_tasks', verbose_name='发布者')
    worker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_tasks', verbose_name='接单者')

    title = models.CharField(max_length=100, verbose_name='地点名称/标题') 
    desc = models.TextField(verbose_name='需求描述') 
    
    location_name = models.CharField(max_length=255, verbose_name='地点名')
    location_address = models.CharField(max_length=255, verbose_name='地址详情')
    detail_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='具体位置')
    latitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='纬度')
    longitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='经度')

    price = models.IntegerField(verbose_name='积分')
    deadline = models.DateTimeField(verbose_name='截止时间')
    task_type = models.CharField(max_length=50, default='日常', verbose_name='类型')
    language = models.CharField(max_length=50, default='普通话', verbose_name='语言')
    
    video_specs = models.CharField(max_length=50, default='1080P', verbose_name='画质规格')
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default='portrait', verbose_name='画幅')

    guide_text = models.TextField(default='[]', verbose_name='拍摄指南JSON') 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    result_video = models.FileField(upload_to='videos/', null=True, blank=True, verbose_name='交付视频')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def get_guide_list(self):
        try:
            return json.loads(self.guide_text)
        except:
            return []

# ==========================================
# 3. 积分流水模块 (Transaction)
# ==========================================
class Transaction(models.Model):
    """
    积分流水表
    """
    TRANS_TYPE = (
        ('income', '收入'),
        ('expense', '支出'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    title = models.CharField(max_length=100, verbose_name='流水标题') 
    amount = models.IntegerField(verbose_name='变动金额') 
    trans_type = models.CharField(max_length=10, choices=TRANS_TYPE, verbose_name='类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')

    def __str__(self):
        sign = '+' if self.trans_type == 'income' else '-'
        return f"{self.title} {sign}{self.amount}"
