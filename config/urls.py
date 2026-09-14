"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from schools.views import landing_page

urlpatterns = [

    path("", landing_page, name="landing"),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    
    # 1. Include your custom accounts app URLs (login, profile, etc.)
    path('accounts/', include('accounts.urls')), 
    
    # Optional: Keep built-in auth views as fallback if needed
    # path('auth/', include('django.contrib.auth.urls')),
    
    # 2. Manager / School management URLs
    path('manager/', include('schools.urls', namespace='manager')),

    path(
    "teacher/",
    include("schools.teacher_urls", namespace="teacher"),
),
]
