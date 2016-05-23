#!/usr/bin/env python
from setuptools import setup
from setuptools.command.install_lib import install_lib as _install_lib
from distutils.command.build import build as _build
from distutils.cmd import Command


class compile_translations(Command):
    description = 'compile message catalogs to MO files via django compilemessages'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import os
        from django.core.management import execute_from_command_line, CommandError

        curdir = os.getcwd()
        forum_dir = os.path.realpath('djangobb_forum')
        os.chdir(forum_dir)
        try:
            execute_from_command_line(['django-admin', 'compilemessages'])
        except CommandError:
            pass
        finally:
            os.chdir(curdir)


class build(_build):
    sub_commands = [('compile_translations', None)] + _build.sub_commands


class install_lib(_install_lib):
    def run(self):
        self.run_command('compile_translations')
        _install_lib.run(self)


setup(name='slimbb',
    version='0.2.0',
    description='slimbb is a minimal bulletin board (forum) implemented in Django. Forks DjangoBB.',
    license='BSD',
    url='https://github.com/hsoft/slimbb',
    author='Virgil Dupras, Alexey Afinogenov, Maranchuk Sergey',
    author_email='Virgil Dupras <hsoft@hardcoded.net>',
    packages=['slimbb'],
    include_package_data=True,
    setup_requires=['django>=1.8,<2.0'],
    install_requires=open('requirements.txt').readlines(),
    test_suite='runtests.runtests',
    cmdclass={'build': build, 'install_lib': install_lib,
        'compile_translations': compile_translations}
)
