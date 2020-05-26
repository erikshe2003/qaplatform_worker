# -*- coding: utf-8 -*-


class Iterator:
    def __init__(self, _total=1):
        """
        :param _total: 虚拟用户数量
        """
        self.data = []
        self.keys_str = ''
        self.keys = []
        self.split = ''
        self.total = _total
        self.share = True
        self.inited = False
        # 编号从1开始
        self.current_indexs = {}
        self.current_lines = {}
        self.max_line = 0

    def init(self, _share: bool, _data: list, _keys: str, _split=','):
        """
        手动初始化
        :param _share: 是否全部线程共享
        :param _keys: 参数化的变量名称,字符串,半角逗号区隔
        :param _split: 值分隔符
        :param _data: 参数化数据
        :return: 无返回值
        """
        self.data = _data
        self.keys_str = _keys
        self.keys = self.keys_str.split(',')
        self.split = _split
        self.share = _share
        # 编号从1开始
        self.max_line = len(self.data)
        i = 0
        while i < self.total:
            self.current_indexs[i + 1] = -1
            self.current_indexs[i + 1], self.current_lines[i + 1] = self.handle_blank(self.current_indexs[i + 1])
            i += 1
        self.inited = True

    def handle_blank(self, _index):
        current_line = {}
        for i, val in enumerate(self.keys):
            current_line[val] = None
        return _index, current_line

    def handle(self, _index):
        return 0, ''

    def next(self, vuser_num):
        # 如果self.share为真则把current_indexs中值全体+1
        # 否则根据vuser_num来修改对应的current_index
        if self.share:
            i = 0
            while i < self.total:
                self.current_indexs[i + 1] += 1
                self.current_indexs[i + 1], self.current_lines[i + 1] = self.handle(self.current_indexs[i + 1])
                i += 1
        else:
            self.current_indexs[vuser_num] += 1
            self.current_indexs[vuser_num], self.current_lines[vuser_num] = self.handle(self.current_indexs[vuser_num])

    def get(self, _key, vuser_num):
        return self.current_lines[vuser_num][_key]

    def get_by_index(self, _key: str, _index: int):
        # 超出行数返回None
        if _index > self.max_line:
            return None
        elif _key in self.keys:
            # 根据传入的key行数返回对应行切分后的数据
            line_str_split = self.data[_index].rstrip('\n').rstrip('\r').split(self.split)
            return line_str_split[self.keys.index(_key)]
        else:
            # 没有符合条件的key则返回空
            return None


class TextIterator(Iterator):
    def handle(self, _index):
        current_line = {}
        # 判断此时self.current_indexs[i + 1]值大小,如果其大于等于max_line则重新赋值为0
        if _index >= self.max_line:
            _index = 0
        line_str_split = self.data[_index].rstrip('\n').rstrip('\r').split(self.split)
        line_str_split_range = range(len(line_str_split))
        for i, val in enumerate(self.keys):
            if i in line_str_split_range:
                current_line[self.keys[i]] = line_str_split[i]
            else:
                current_line[val] = None
        return _index, current_line


class ListIterator(Iterator):
    def handle(self, _index):
        current_line = {}
        # 判断此时self.current_indexs[i + 1]值大小,如果其大于等于max_line则重新赋值为0
        if _index >= self.max_line:
            _index = 0
        line_str_split = [di for di in self.data[_index]]
        line_str_split_range = range(len(line_str_split))
        for i, val in enumerate(self.keys):
            if i in line_str_split_range:
                current_line[self.keys[i]] = line_str_split[i]
            else:
                current_line[val] = None
        return _index, current_line
