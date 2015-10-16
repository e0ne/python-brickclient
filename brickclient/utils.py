# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import os
import pkg_resources
import sys

from oslo_utils import encodeutils
import prettytable
import six


def arg(*args, **kwargs):
    """Decorator for CLI args."""
    def _decorator(func):
        add_arg(func, *args, **kwargs)
        return func
    return _decorator


def add_arg(f, *args, **kwargs):
    """Bind CLI arguments to a shell.py `do_foo` function."""

    if not hasattr(f, 'arguments'):
        f.arguments = []

    # NOTE(sirp): avoid dups that can occur when the module is shared across
    # tests.
    if (args, kwargs) not in f.arguments:
        # Because of the semantics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        f.arguments.insert(0, (args, kwargs))


def env(*vars, **kwargs):
    """
    returns the first environment variable set
    if none are non-empty, defaults to '' or keyword arg default
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def unauthenticated(f):
    """
    Adds 'unauthenticated' attribute to decorated function.
    Usage:
        @unauthenticated
        def mymethod(f):
            ...
    """
    f.unauthenticated = True
    return f


def isunauthenticated(f):
    """
    Checks to see if the function is marked as not requiring authentication
    with the @unauthenticated decorator. Returns True if decorator is
    set to True, False otherwise.
    """
    return getattr(f, 'unauthenticated', False)


def service_type(stype):
    """
    Adds 'service_type' attribute to decorated function.
    Usage:
        @service_type('volume')
        def mymethod(f):
            ...
    """
    def inner(f):
        f.service_type = stype
        return f
    return inner


def get_service_type(f):
    """
    Retrieves service type from function
    """
    return getattr(f, 'service_type', None)


def print_dict(d, property="Property"):
    pt = prettytable.PrettyTable([property, 'Value'], caching=False)
    pt.aligns = ['l', 'l']
    [pt.add_row(list(r)) for r in six.iteritems(d)]
    _print(pt, property)


def _print(pt, order):
    if sys.version_info >= (3, 0):
        print(pt.get_string(sortby=order))
    else:
        print(encodeutils.safe_encode(pt.get_string(sortby=order)))


class HookableMixin(object):
    """Mixin so classes can register and run hooks."""
    _hooks_map = {}

    @classmethod
    def add_hook(cls, hook_type, hook_func):
        if hook_type not in cls._hooks_map:
            cls._hooks_map[hook_type] = []

        cls._hooks_map[hook_type].append(hook_func)

    @classmethod
    def run_hooks(cls, hook_type, *args, **kwargs):
        hook_funcs = cls._hooks_map.get(hook_type) or []
        for hook_func in hook_funcs:
            hook_func(*args, **kwargs)


def safe_issubclass(*args):
    """Like issubclass, but will just return False if not a class."""

    try:
        if issubclass(*args):
            return True
    except TypeError:
        pass

    return False


def _load_entry_point(ep_name, name=None):
    """Try to load the entry point ep_name that matches name."""
    for ep in pkg_resources.iter_entry_points(ep_name, name=name):
        try:
            return ep.load()
        except (ImportError, pkg_resources.UnknownExtra, AttributeError):
            continue
