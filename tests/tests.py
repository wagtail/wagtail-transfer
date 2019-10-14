from django.test import TestCase


class TestFoo(TestCase):
    fixtures = ['test.json']

    def test_foo(self):
        self.assertTrue(True)
