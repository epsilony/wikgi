'''
Created on 2014年6月16日

@author: epsilon
'''

from markdown.util import etree
from markdown.inlinepatterns import Pattern
from markdown import Extension

from django.core.urlresolvers import reverse
from django.conf import settings

from pathlib import Path
import mimetypes

def get_base_url():
    return reverse('wikgi:index')

class WikgiUrlPattern(Pattern):
    def __init__ (self, start_end=None, groups=None):
        pattern = r'\[\[\s*((?:\w+)(?:/\w+)*((?:\.\w+)*))\s*\|?\s*(.*?)\s*\]\]'
        Pattern.__init__(self, pattern)

    def handleMatch(self, m):
        if len(m.group(3)) > 0:
            return self._mime_link(m);
        else:
            return self._article_link(m)
    
    def _article_link(self,m):
        return self._a_link(m)
    
    def _a_link(self,m):
        e=etree.Element('a')
        e.text=self._get_label(m)
        e.set('href',self._get_url(m))
        e.set('class','wikgi_link')
        return e
    
    def _mime_link(self,m):
        mimetype=self._get_mime_type(m)
        
        if not mimetype:
            return self._a_link(m)
        
        if mimetype.startswith('image/'):
            e=etree.Element('img')
            e.set('src',self._get_url(m))
            e.set('alt',self._get_label(m))
            return e
        else:
            e=self._a_link(m)
            e.set('type',mimetype)
            return e
    
    def _get_url(self,m):
        return get_base_url()+self._get_rel_path(m)
    
    def _get_rel_path(self, m):
        rel_path = m.group(2)
        return rel_path


    def _get_path(self, m):      
        return Path(settings.WIKGI_MEDIA) / self._get_rel_path(m)
    
    def _get_mime_type(self,m):
        path = self._get_path(m)
        if path.exists() and path.is_file():
            return mimetypes.guess_type(str(path))[0]
        else:
            return None
    
    def _get_label(self, m):
        return m.group(2) if len(m.group(4)) == 0 else m.group(4)

class WikgiUrlExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('wigi_url', WikgiUrlPattern(), '<not_strong')
        
def makeExtension(configs=None):
    return WikgiUrlExtension(configs)
