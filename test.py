#!/usr/bin/env python3
"""
Lightweight tests for the reverse proxy.
Run with: python test.py
"""

import unittest
import sys
sys.path.insert(0, '/home/claude')

from utils.rewrite import rewrite_content


class TestURLRewriting(unittest.TestCase):
    
    def test_relative_urls_get_prefixed(self):
        html = '<a href="/about">About</a>'
        result = rewrite_content(html, 'myapp', 'example.com')
        self.assertIn('href="/myapp/about"', result)
    
    def test_absolute_urls_untouched(self):
        html = '<script src="https://cdn.example.com/script.js"></script>'
        result = rewrite_content(html, 'myapp', 'example.com')
        self.assertIn('https://cdn.example.com/script.js', result)
    
    def test_mathjax_gets_prefixed(self):
        html = '<script src="/mathjax/tex-chtml.js"></script>'
        result = rewrite_content(html, 'calculum', 'calculum.aediroum.ca')
        self.assertIn('src="/calculum/mathjax/tex-chtml.js"', result)
    
    def test_no_double_prefix(self):
        html = '<a href="/myapp/about">About</a>'
        result = rewrite_content(html, 'myapp', 'example.com')
        self.assertEqual(html, result)
        
    def test_pathname_reads_get_stripped(self):
        """JavaScript reads window.location.pathname without /service/ prefix"""
        js = 'if (window.location.pathname === "/about") { }'
        result = rewrite_content(js, 'app', 'example.com')
        self.assertIn('pathname.replace(/^\\/app\\//, "/")', result)

    def test_fetch_calls_get_prefixed(self):
        """fetch() with relative URLs get service prefix"""
        js = 'fetch("/api/data")'
        result = rewrite_content(js, 'app', 'example.com')
        self.assertIn('fetch("/app/api/data")', result)

    def test_base_tag_rewritten(self):
        """<base href="/"> gets service prefix"""
        html = '<base href="/">'
        result = rewrite_content(html, 'app', 'example.com')
        self.assertIn('<base href="/app/">', result)

    def test_data_urls_untouched(self):
        """data: URLs should not be modified"""
        html = '<img src="data:image/png;base64,iVBORw0KGg==">'
        result = rewrite_content(html, 'app', 'example.com')
        self.assertEqual(html, result)

    def test_protocol_relative_urls(self):
        """//cdn.com URLs should not be modified"""
        html = '<script src="//cdn.jsdelivr.net/lib.js"></script>'
        result = rewrite_content(html, 'app', 'example.com')
        self.assertEqual(html, result)

    def test_root_path_slash(self):
        """href="/" should become href="/service/" """
        html = '<a href="/">Home</a>'
        result = rewrite_content(html, 'club', 'example.com')
        self.assertIn('href="/club/"', result)
    
    def test_navigation_links(self):
        """Real-world navigation from calculum site"""
        html = '''<nav>
    <a href="/">Info</a>
    <a href="/meets">Rencontres</a>
    <a href="/events">Événements</a>
</nav>'''
        result = rewrite_content(html, 'club', 'calculum.aediroum.ca')
        self.assertIn('href="/club/"', result)
        self.assertIn('href="/club/meets"', result)
        self.assertIn('href="/club/events"', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)