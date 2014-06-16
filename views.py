from django.shortcuts import render
from django.http import Http404,HttpResponse,HttpResponseNotModified
from django.template import RequestContext,loader
from django.conf import settings
from django.core.urlresolvers import reverse

from markdown import Markdown
from .markdown.mdx_mathjax import MathJaxExtension
from .markdown.mdx_wikgi_url import WikgiUrlExtension

from pathlib import Path

from django import forms

import mimetypes
# Create your views here.

_mark_down_parser=None
_md_suffix=".md"

def index_view(request):
    articles = get_all_articles()
    return render(request,'wikgi/index.html',{'articles':articles})

def article(request,article_name):
    if request.method == 'POST':
        form=ArticleEditorForm(request.POST)
        if form.is_valid():
            import subprocess
            subprocess.Popen(["gedit",str(get_article_path(article_name))])
            return HttpResponseNotModified()
    
    global _mark_down_parser
    if _mark_down_parser is None:
        _mark_down_parser=Markdown(extensions=[MathJaxExtension(),WikgiUrlExtension(),'extra','codehilite'],safe_mode='escape')
    path=get_article_path(article_name)
    if not path.exists() or not path.is_file():
        raise Http404
    
    markdown_html=get_article_html(article_name)
    
    return render(request,'wikgi/article.html',
                  {'markdown_html':markdown_html,
                   'article_name':article_name,
                   'up_article_names':get_up_article_names(article_name),
                   'form':ArticleEditorForm()})

class ArticleEditorForm(forms.Form):
    pass   

def media(request,media_file_url):
    pth=get_media_path(media_file_url)
    if not pth.exists() or not pth.is_file():
        raise Http404
    mime_type=mimetypes.guess_type(str(pth))[0]
    try:
        with pth.open('rb') as f:
            return HttpResponse(f.read(),content_type=mime_type)
    except IOError:
        raise Http404

def get_all_articles():
    articles = [str(path.relative_to(settings.WIKGI_GIT))[:-len(_md_suffix)] for path in get_all_articles_paths()]
    return articles

def get_up_article_names(article_name):
    up_name=get_up_article_name(article_name)
    res=[]
    while up_name:
        res.append(up_name)
        up_name=get_up_article_name(up_name)
    return res.reverse()

def get_up_article_name(article_name):
    r=article_name.rfind('/')
    if r<0:
        return ''
    else:
        return article_name[:r]
    
def get_all_articles_paths():
    all_articles_paths=get_article_root_path().glob('**/*'+_md_suffix)
    return [path for path in all_articles_paths]

def get_article_root_path():
    return Path(settings.WIKGI_GIT)

def get_article_path(article):
    pth = get_article_root_path() / (article + _md_suffix)
    return pth

def get_article_markdown(article):
    pth = get_article_path(article)
    with pth.open() as f:
        markdown_text = f.read()
    _mark_down_parser.reset()
    return markdown_text

def get_article_html(article):
    markdown_text = get_article_markdown(article)
    return _mark_down_parser.convert(markdown_text)

def get_media_path(media_file_name):
    root_pth=get_media_root_path()
    return root_pth/media_file_name

def get_media_root_path():
    return Path(settings.WIKGI_MEDIA)

