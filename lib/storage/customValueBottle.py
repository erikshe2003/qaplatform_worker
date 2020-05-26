# -*- coding: utf-8 -*-


class VuserDataBottle:
    def __init__(self):
        self.__data = {}

    def update(self, item_dict):
        if type(item_dict) is dict:
            self.__data.update(item_dict)

    def get(self, item):
        if item in self.__data:
            return self.__data[item]
        else:
            return None
