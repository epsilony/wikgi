'''
Created on 2014年6月15日

@author: epsilon
'''
from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns('',
    url(r'^$',views.index_view,name='index'),
    url(r'^((?:\w+)(?:/\w+)*(?:\.\w+))$',views.media,name="media"),
    url(r'^((?:\w+)(?:/\w+)*)$',views.article,name='article'),
)