#!/usr/bin/env python3
"""
Lightweight tests for the reverse proxy.
Run with: python test.py
"""

import unittest
import re


def rewrite_content(content, service, target_domain):
    """Rewrite URLs - extracted from views.py for standalone testing."""
    
    # Rewrite pathname reads
    content = re.sub(
        r'(?<!document\.)window\.location\.pathname\b',
        f'(window.location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    content = re.sub(
        r'(?<!window\.)(?<!document\.)location\.pathname\b',
        f'(location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    
    # Rewrite <base> tag
    content = re.sub(
        r'<base\s+href="/"',
        f'<base href="/{service}/"',
        content,
        flags=re.IGNORECASE
    )
    
    def is_absolute(url):
        return bool(re.match(r'^https?://', url)) or '//' in url or url.startswith('data:')
    
    def rewrite_url(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        
        if url.startswith(f'/{service}/'):
            return match.group(0)
        
        if is_absolute(url):
            return match.group(0)
        
        return f'{attr}{quote}/{service}{url}{quote}'
    
    # Rewrite attributes
    content = re.sub(
        r'((?:href|src|action)=)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    # Rewrite fetch() calls
    content = re.sub(
        r'(fetch\s*\(\s*)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    # Rewrite location.href
    content = re.sub(
        r'(location\.href\s*=\s*)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    return content


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


if __name__ == '__main__':
    unittest.main(verbosity=2)