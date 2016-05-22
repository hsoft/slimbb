# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, RequestFactory

from djangobb_forum.models import Post
from djangobb_forum.util import urlize, add_rel_nofollow, convert_text_to_html, get_page


class TestParsers(TestCase):
    def setUp(self):
        self.data_url = "Lorem ipsum dolor sit amet, consectetur http://djangobb.org/ adipiscing elit."
        self.data_nofollow = "&lt;a&gt;Lorem ipsum&lt;/a&gt; <a href=\"http://djangobb.org/\">http://djangobb.org/</a>"

    def test_urlize(self):
        urlized_data = urlize(self.data_url)
        self.assertEqual(urlized_data, "Lorem ipsum dolor sit amet, consectetur <a href=\"http://djangobb.org/\" rel=\"nofollow\">http://djangobb.org/</a> adipiscing elit.")

    def test_nofollow(self):
        nofollow_data = add_rel_nofollow(self.data_nofollow)
        self.assertEqual(nofollow_data, "&lt;a&gt;Lorem ipsum&lt;/a&gt; <a href=\"http://djangobb.org/\" rel=\"nofollow\">http://djangobb.org/</a>")

    def test_convert_text_to_html(self):
        markdown = "**Lorem** `ipsum :)` [label](http://www.example.com) =)"
        html = convert_text_to_html(markdown)
        self.assertEqual(html, "<p><strong>Lorem</strong> <code>ipsum :)</code> <a href=\"http://www.example.com\" rel=\"nofollow\">label</a> =)</p>")


class TestPaginators(TestCase):
    fixtures = ['test_forum.json']

    def setUp(self):
        self.posts = Post.objects.all()[:5]
        self.factory = RequestFactory()

    def test_get_page(self):
        request = self.factory.get('/?page=2')
        page = get_page(self.posts, request, 3)
        self.assertEqual(page.number, 2)
        self.assertEqual(page.paginator.num_pages, 2)

        request = self.factory.get('/?page=1')
        page = get_page(self.posts, request, 3)
        self.assertEqual(page.number, 1)
        self.assertEqual(page.paginator.num_pages, 2)


class TestVersion(TestCase):
    def test_get_version(self):
        import djangobb_forum

        djangobb_forum.version_info = (0, 2, 1, 'f', 0)
        self.assertEqual(djangobb_forum.get_version(), '0.2.1')
        djangobb_forum.version_info = (2, 3, 1, 'a', 5)
        self.assertIn(djangobb_forum.get_version(), '2.3.1a5.dev0')
