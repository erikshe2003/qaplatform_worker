# -*- coding: utf-8 -*-

"""
文本文件参数化插件
    功能简述:
        支持从txt/csv等文本文件中读取内容,并按行以及指定符号区隔的列生成参数化内容

    实现逻辑:
        初始化时,检查各项参数是否符合输入要求,通过后读取参数化文件,并将内容填充至自定义迭代器,最终添加入总参数化存储实例中以供调用

    需求入参:{"name":"","uuid":"","auto_encode":true,"encode":"","var_names":"","ignore_first_line":false,"split":",","share_all_threads":true}
        {
            "name":"...",
                参数化用到文件的文件名
            "uuid":"...",
                参数化用到文件的经uuid重命名后的名称
            "auto_encode":true/false,
                自动/手动指定文件编码格式
            "encode":"...",
                手动指定的文件编码格式
            "var_names":"...",
                参数化的变量名称,可填写多个,需以半角逗号区隔
            "ignore_first_line":true/false,
                是/否忽略首行
            "split":",",
                参数化文件中每一行内容的区隔符号,用以将每行内容区隔为不同的列,并将各列数据赋以参数化的变量名称
            "share_all_threads":true/false
                变量值是否在全部虚拟用户之间共享
        }
"""

import json
import re

from handler.scheduler import kill_test_task_job

from lib.storage.iterator import TextIterator

from ..parameter import ParameterPlugin


class CsvDataSetConfig(ParameterPlugin):
    csvIterator = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化公共迭代器
        if not CsvDataSetConfig.csvIterator:
            CsvDataSetConfig.csvIterator = TextIterator(_total=self.base_user_num)
        # 添加插件自有属性
        self.config_name = ''
        self.config_uuid = ''
        self.config_auto_encode = True
        self.config_encode = 'utf8'
        self.config_var_names = ''
        self.config_ignore_first_line = False
        self.config_split = ','
        self.config_share_all_threads = True
        # 根据传入的数据，进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_var_names(names):
        # 如果名称未填写则忽略
        if names != '':
            # 变量名称需符合填写规范
            for ns in names.split(','):
                if not re.match(r"(\b[_a-zA-Z][_a-zA-Z0-9.]*)", ns):
                    return False
        return True

    def check_before_run(self):
        """
        初始化说明点
        1 name:str
        2 uuid:str
        3 auto_encode:bool
        4 encode:str
        5 var_names:str
        6 ignore_first_line:bool
        7 split:str
        8 share_all_threads:bool
        :return: (False, log)/(True, None)
        """
        log = ''
        check_flag = True

        try:
            plugin_init_value = json.loads(self.plugin_init_value_str)
        except Exception as e:
            log += '数据整体检查失败,原因:%s;' % repr(e)
            check_flag = False
        else:
            # name
            if 'name' not in plugin_init_value or type(plugin_init_value['name']) is not str:
                log += '文件名检查失败,原因:文件名整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['name'] == "":
                log += '文件名检查失败,原因:文件名缺失,文件未上传;'
                check_flag = False
            # uuid
            if 'uuid' not in plugin_init_value or type(plugin_init_value['uuid']) is not str:
                log += '文件别名检查失败,原因:文件别名整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['uuid'] == "":
                log += '文件别名检查失败,原因:文件别名缺失,文件未上传;'
                check_flag = False
            # auto_encode
            if 'auto_encode' not in plugin_init_value or type(plugin_init_value['auto_encode']) is not bool:
                log += '文件编码方式选项检查失败,原因:文件编码方式选项整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # encode
            if 'encode' not in plugin_init_value or type(plugin_init_value['encode']) is not str:
                log += '手动指定编码格式检查失败,原因:手动指定编码格式整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif not plugin_init_value['auto_encode'] and plugin_init_value['encode'] == "":
                log += '手动指定编码格式检查失败,原因:文件编码选择手动指定编码时编码格式不能为空;'
                check_flag = False
            # var_names
            if 'var_names' not in plugin_init_value or type(plugin_init_value['var_names']) is not str:
                log += '变量名检查失败,原因:变量名整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif not self.check_var_names(plugin_init_value['var_names']):
                log += '变量名检查失败,原因:变量名填写非法,请按照格式要求填写;'
                check_flag = False
            # ignore_first_line
            if 'ignore_first_line' not in plugin_init_value or type(plugin_init_value['ignore_first_line']) is not bool:
                log += '忽略首行检查失败,原因:忽略首行整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # split
            if 'split' not in plugin_init_value or type(plugin_init_value['split']) is not str:
                log += '分隔符检查失败,原因:分隔符整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # share_all_threads
            if 'share_all_threads' not in plugin_init_value or type(plugin_init_value['share_all_threads']) is not bool:
                log += '线程间数据共享检查失败,原因:线程间数据共享整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
        if not check_flag:
            return False, log
        else:
            return True, None

    def init_before_run(self):
        # 参数化处理
        plugin_value_str = self.parameters_replace(self.plugin_init_value_str)

        # 预处理
        try:
            self.plugin_value = json.loads(plugin_value_str)
        except Exception as e:
            return False, '运行前插件原始数据预处理失败:%s;' % repr(e)
        else:
            # name
            self.config_name = self.plugin_value['name']
            # uuid
            self.config_uuid = self.plugin_value['uuid']
            # auto_encode
            self.config_auto_encode = self.plugin_value['auto_encode']
            # encode
            self.config_encode = self.plugin_value['encode']
            # var_names
            self.config_var_names = self.plugin_value['var_names']
            # ignore_first_line
            self.config_ignore_first_line = self.plugin_value['ignore_first_line']
            # split
            self.config_split = self.plugin_value['split']
            # share_all_threads
            self.config_share_all_threads = self.plugin_value['share_all_threads']
            if self.config_var_names != '':
                # 进行数据填充
                try:
                    parameter_file = open(
                        '%s/files/%s' % (self.base_data['file_path'], self.config_uuid),
                        mode='r',
                        encoding=None if self.config_auto_encode else self.config_encode
                    )
                except Exception as e:
                    return False, '参数化文件打开失败,原因:%s;' % repr(e)
                else:
                    CsvDataSetConfig.csvIterator.init(
                        _share=self.config_share_all_threads,
                        _data=parameter_file.readlines()[1 if self.config_ignore_first_line else 0:],  # 忽略首行
                        _split=self.config_split,
                        _keys=self.config_var_names
                    )
                    for cvn in self.config_var_names.split(','):
                        self.run_parameter_controller.update({cvn: CsvDataSetConfig.csvIterator})
                    return True, None

    def run_test(self):
        # 对于本参数化插件来说，第一次被调用run_test即调用init_before_run去初始化迭代器
        if not CsvDataSetConfig.csvIterator.inited:
            run_init_result, run_init_log = self.init_before_run()
            # 如果失败强行终止测试任务运行
            if not run_init_result:
                self.trans_init_log(run_init_log)
                kill_test_task_job(self.base_data)
        CsvDataSetConfig.csvIterator.next(vuser_num=self.vuser_index)
