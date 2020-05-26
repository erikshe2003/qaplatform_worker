# -*- coding: utf-8 -*-


class ConfigError(Exception):
    """ Config error. """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
