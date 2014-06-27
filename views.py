from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseNotModified, JsonResponse
from django.template import RequestContext, loader
from django.conf import settings
from django.core.urlresolvers import reverse

from markdown import Markdown
from .markdown.mdx_mathjax import MathJaxExtension
from .markdown.mdx_wikgi_url import WikgiUrlExtension

from pathlib import Path

from django import forms

import re

import mimetypes

import sys

import json
# Create your views here.

_mark_down_parser = None
_md_suffix = ".md"

def index_view(request):
    articles = get_all_articles()
    return render(request, 'wikgi/index.html', {'articles':articles})

def article(request, article_name):
    if request.is_ajax():
        return _article_ajax(request, article_name)
    
    path = get_article_path(article_name)
    if not path.exists() or not path.is_file():
        raise Http404
    
    markdown_html = get_article_html(article_name)
    
    return render(request, 'wikgi/article.html',
                  {'markdown_html':markdown_html,
                   'article_name':article_name,
                   'up_article_names':get_up_article_names(article_name),
                   'form':ArticleEditorForm()})



def _article_ajax(request, article_name):
    if request.method == 'GET':
        view_type = request.GET.get('view_type')
    else:
        view_type = request.POST.get('view_type')
        
    if not view_type:
        return _article_ajax_fail();
    ajax_func = _article_ajax_funcs.get(view_type)
    if not ajax_func:
        return _article_ajax_fail();
    return ajax_func(request, article_name)

def _article_get_h_markdown(request, article_name):
    h_index = request.POST['h_index']
    h_index = int(h_index)
    markdown_piece = get_article_markdown_piece(h_index, article_name)[0]
    return JsonResponse({'success':True, 'markdown_piece':markdown_piece})

def _article_replace_h_markdown(request, article_name):
    h_index = request.POST['h_index']
    h_index = int(h_index)
    
    new_markdown_piece = request.POST['new_markdown_piece']
    
    (start, end) = get_article_markdown_piece(h_index, article_name)[1]
      
    markdown_text = get_article_markdown(article_name)
    markdown_text = markdown_text.splitlines()
    new_markdown_text = markdown_text[:start]
    new_markdown_text.extend(new_markdown_piece.splitlines())
    new_markdown_text.extend(markdown_text[end:])
    
    with get_article_path(article_name).open('w') as f:
        f.write('\n'.join(new_markdown_text))
    
    new_markdown_piece_html = parse_markdown(new_markdown_piece)
    
    
    return JsonResponse({'success':True, 'markdown_html':new_markdown_piece_html})

def _article_get_markdown_html(request, article_name):
    markdown_text = ''
    if request.method == "POST":
        markdown_text = request.POST['markdown_text']
    else:
        markdown_text = request.GET['markdown_text']
    markdown_html = parse_markdown(markdown_text)
    return JsonResponse({'success':True, 'markdown_html':markdown_html})

def _article_ajax_fail():
    return JsonResponse({"success":False})

class ArticleEditorForm(forms.Form):
    pass   

def media(request, media_file_url):
    pth = get_media_path(media_file_url)
    if not pth.exists() or not pth.is_file():
        raise Http404
    mime_type = mimetypes.guess_type(str(pth))[0]
    try:
        with pth.open('rb') as f:
            return HttpResponse(f.read(), content_type=mime_type)
    except IOError:
        raise Http404

def get_all_articles():
    articles = [str(path.relative_to(settings.WIKGI_GIT))[:-len(_md_suffix)] for path in get_all_articles_paths()]
    return articles

def get_up_article_names(article_name):
    up_name = get_up_article_name(article_name)
    res = []
    while up_name:
        res.append(up_name)
        up_name = get_up_article_name(up_name)
    return res.reverse()

def get_up_article_name(article_name):
    r = article_name.rfind('/')
    if r < 0:
        return ''
    else:
        return article_name[:r]
    
def get_all_articles_paths():
    all_articles_paths = get_article_root_path().glob('**/*' + _md_suffix)
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
    return markdown_text

def get_article_markdown_piece(h_index, article):  
    article_markdown = get_article_markdown(article)
    article_markdown_lines = article_markdown.splitlines()
    hs_line_indes = _get_hs_line_indes(article_markdown_lines)
    h_line = article_markdown_lines[hs_line_indes[h_index]]
    h_lv = get_h_line_level(h_line)
    next_h_index = None
    for i in range(h_index + 1, len(hs_line_indes)):
        t_h_line = article_markdown_lines[hs_line_indes[i]]
        if get_h_line_level(t_h_line) <= h_lv:
            next_h_index = i
            break
    start = hs_line_indes[h_index]
    if next_h_index:
        end = hs_line_indes[next_h_index]
    else:
        end = len(article_markdown_lines)
    return ('\n'.join(article_markdown_lines[start:end]), (start, end))

_h_lv_reg = re.compile(r'^#{1,6}')   
def get_h_line_level(h_line):
    return _h_lv_reg.match(h_line).end()

_h_reg = re.compile(r'^#{1,6}.*$')
_pre_start_reg = re.compile(r'^```\s*\w*\s*$')
_pre_end_reg = re.compile(r'^```\s*$')   
def _get_hs_line_indes(markdown_lines):
    i = 0
    res = []
    may_in_pre_block_hs = []
    may_in_block = False
    for line in markdown_lines:
        if not may_in_block and _pre_start_reg.fullmatch(line):
            may_in_block = True
            i += 1
            continue
        if _pre_end_reg.fullmatch(line):
            may_in_block = False
            may_in_pre_block_hs.clear()
            i += 1
            continue
        if _h_reg.fullmatch(line):
            if may_in_block:
                may_in_pre_block_hs.append(i)
            else:
                res.append(i)
        i += 1
    # this is something wrong with a ``` block, so the heads are included in
    if may_in_block:
        res.extend(may_in_pre_block_hs)
    return res
        

def get_article_html(article):
    markdown_text = get_article_markdown(article)
    return parse_markdown(markdown_text)
    
def parse_markdown(markdown_text):
    global _mark_down_parser
    if _mark_down_parser is None:
        _mark_down_parser = Markdown(extensions=[MathJaxExtension(), WikgiUrlExtension(), 'extra', 'codehilite'], safe_mode='escape')
    _mark_down_parser.reset()
    return _mark_down_parser.convert(markdown_text)

def get_media_path(media_file_name):
    root_pth = get_media_root_path()
    return root_pth / media_file_name

def get_media_root_path():
    return Path(settings.WIKGI_MEDIA)

_article_ajax_funcs = {'get_h_markdown':_article_get_h_markdown, 'get_markdown_html':_article_get_markdown_html, 'replace_h_markdown':_article_replace_h_markdown}
