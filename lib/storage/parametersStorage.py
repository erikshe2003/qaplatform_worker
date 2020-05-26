# -*- coding: utf-8 -*-

"""
用于存储参数化的数据
当前线程共享则每个线程(协程)拥有一个本类的实例
所有线程共享则所有线程(协程)拥有且公用同一个本类的实例
"""


class ParametersStorage:
    def __init__(self):
        # 初始化全局变量
        self.__global_dict = {}

    def get(self, name: str):
        """
        按照名称获取参数化的内容
        :param name: 参数化的变量名称
        :return: 参数化的值
        """
        if name in self.__global_dict:
            return self.__global_dict[name]
        else:
            return None

    def update(self, items_dict: dict):
        """
        将参数化的键值对添加入全局字典中
        :param items_dict: 参数化的键值对
        :return: 无返回
        """
        self.__global_dict.update(items_dict)

    def get_all(self):
        return self.__global_dict
