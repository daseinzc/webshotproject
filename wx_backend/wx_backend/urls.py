"""
URL configuration for wx_backend project.
"""
from django.contrib import admin
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 管理后台路由
    path('admin/', admin.site.urls),
    
    # 你的应用路由（核心）
    # path('浏览器访问的前缀/', include('你的App名字.urls'))
    # 既然你的文件夹叫 app01，这里就必须写 app01.urls
    path('api/', include('app01.urls')), 
]

# ==========================================
# 关键一步：添加媒体文件的路由服务
# ==========================================
# 这段代码的意思是：如果是开发模式(DEBUG=True)，这就开启一个通道，
# 让 http://127.0.0.1:8000/media/... 能直接访问到你的本地文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
