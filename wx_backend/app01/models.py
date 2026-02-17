from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
import json
import random

# ==========================================
# 1. 用户与账户模块 (User & Profile)
# ==========================================
class UserProfile(models.Model):
    """
    用户扩展信息表
    对应前端：profile.js, register.js, my.js
    """
    GENDER_CHOICES = (
        ('男', '男'),
        ('女', '女'),
        ('未知', '未知'),
    )

    # 关联 Django 内置 User (用于存储 username, password, email)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

 
    
    # 基础信息
    nickname = models.CharField(max_length=50, verbose_name='昵称', default='微信用户')
    uid_tag = models.CharField(max_length=4, default='0000', verbose_name='UID尾号')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', verbose_name='头像')
    phone = models.CharField(max_length=20, unique=True, verbose_name='手机号')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='未知', verbose_name='性别')
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    
    # 资产信息 (对应 points.js)
    balance = models.IntegerField(default=0, verbose_name='积分余额') # 1元=100积分? 需根据业务定义
    credit_score = models.IntegerField(default=100, verbose_name='信用分')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')


    class Meta:
        # 核心约束：【昵称 + 尾号】必须联合唯一
        # 这样允许不同昵称拥有相同的尾号，但同名同姓的人尾号必须不同
        unique_together = ('nickname', 'uid_tag')



    def __str__(self):
        return f"{self.nickname} ({self.user.username})"
    

    def save(self, *args, **kwargs):
        # 如果是第一次保存（没有 ID）且没有 uid_tag，或者 uid_tag 是默认值
        if not self.uid_tag or self.uid_tag == '0000':
            self.uid_tag = self.generate_unique_tag()
        
        super().save(*args, **kwargs)


    def generate_unique_tag(self):
        # 生成一个当前昵称下不冲突的随机Tag
        while True:
            # 生成 '0001' 到 '9999'
            new_tag = f"{random.randint(1, 9999):04d}"
            # 检查数据库里是否已经有 (当前昵称 + 这个tag)
            if not UserProfile.objects.filter(nickname=self.nickname, uid_tag=new_tag).exists():
                return new_tag

    def __str__(self):
        return f"{self.nickname}#{self.uid_tag}"





# ==========================================
# 2. 任务委托模块 (Task)
# ==========================================
class Task(models.Model):
    """
    任务委托表
    对应前端：index.js (发布), assignments.js (列表), bounty_details.js (详情)
    """
    STATUS_CHOICES = (
        ('pending', '待确认'),  # 发布后，等待接单或发布者确认
        ('ongoing', '进行中'),  # 已接单，拍摄中
        ('completed', '已完成'), # 拍摄完成并验收
        ('expired', '已过期'),   # 超过截止时间未接单
    )

    # 发布者与接单者
    publisher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='published_tasks', verbose_name='发布者')
    worker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_tasks', verbose_name='接单者')

    # 核心字段
    title = models.CharField(max_length=100, verbose_name='地点名称/标题') # e.g. "上海中心大厦"
    desc = models.TextField(verbose_name='需求描述') # 对应前端 reqText
    
    # 地理位置 (用于计算距离)
    location_name = models.CharField(max_length=255, verbose_name='地点名') # e.g. "上海中心大厦"
    location_address = models.CharField(max_length=255, verbose_name='地址详情') # e.g. "浦东新区..."
    detail_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='具体位置') # e.g. "52层窗口"
    latitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='纬度')
    longitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='经度')

    # 规格参数
    price = models.IntegerField(verbose_name='积分')
    deadline = models.DateTimeField(verbose_name='截止时间')
    task_type = models.CharField(max_length=50, default='日常', verbose_name='类型') # e.g. 生日祝福
    language = models.CharField(max_length=50, default='普通话', verbose_name='语言')
    video_specs = models.CharField(max_length=50, default='1080P', verbose_name='规格') # e.g. 4K 60fps

    # 拍摄指南 (前端是数组，后端存JSON字符串)
    guide_text = models.TextField(default='[]', verbose_name='拍摄指南JSON') 

    # 状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    
    # 成果物
    result_video = models.FileField(upload_to='videos/', null=True, blank=True, verbose_name='交付视频')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    # 辅助方法：获取指南列表
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
    对应前端：points.js
    """
    TRANS_TYPE = (
        ('income', '收入'),
        ('expense', '支出'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    title = models.CharField(max_length=100, verbose_name='流水标题') # e.g. "充值", "任务收益"
    amount = models.IntegerField(verbose_name='变动金额') # 存绝对值
    trans_type = models.CharField(max_length=10, choices=TRANS_TYPE, verbose_name='类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')

    def __str__(self):
        sign = '+' if self.trans_type == 'income' else '-'
        return f"{self.title} {sign}{self.amount}"

