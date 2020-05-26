# -*- coding: utf-8 -*-

"""
Xls/Xlsx参数化插件
    功能简述:
        支持从xls/xlsx文件中读取内容,支持多sheet读取及从每个sheet参数化各自的内容

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
            "share_all_threads":true/false
                变量值是否在全部虚拟用户之间共享
        }
"""

import json
import xlrd
import xlwt
import pandas
import numpy
import re
import math

from io import BytesIO

from handler.scheduler import kill_test_task_job

from lib.storage.iterator import ListIterator

from ..parameter import ParameterPlugin


class ExcelDataSetConfig(ParameterPlugin):
    excelIterator = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化公共迭代器
        if not ExcelDataSetConfig.excelIterator:
            ExcelDataSetConfig.excelIterator = ListIterator(_total=self.base_user_num)
        # 添加插件自有属性
        self.config_name = ''
        self.config_uuid = ''
        self.config_auto_encode = True
        self.config_encode = 'utf8'
        self.config_var_names = []
        self.config_ignore_first_line = False
        self.config_share_all_threads = True
        # 根据传入的数据，进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_var_names(names):
        # 变量名称需符合填写规范
        for nkey, nvalues in names:
            # nkey即sheet名称需符合excel官方要求
            if type(nkey) is not str:
                return False
            # 当sheet名称填写时需检查sheet名称以及对应的参数化变量名
            # 当sheet名未填写时忽略
            if nkey != '':
                # 1.不能长于31个字符
                # 3.不能为空
                if len(nkey) > 31 or len(nkey) == 0:
                    return False
                # 2.不能包含[ ] / ? / \ * :
                elif re.search(r"[\[\]\?\/\\\*\:]+", nkey):
                    return False
                # nvalues即变量名称须符合参数化要求
                if type(nvalues) is not str:
                    return False
                if nvalues != '':
                    for ns in nvalues.split(','):
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
            if 'var_names' not in plugin_init_value or type(plugin_init_value['var_names']) is not list:
                log += '变量设置检查失败,原因:变量设置整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif not self.check_var_names(plugin_init_value['var_names']):
                log += '变量设置检查失败,原因:Sheet名或变量名填写非法,请按照格式要求填写;'
                check_flag = False
            # ignore_first_line
            if 'ignore_first_line' not in plugin_init_value or type(plugin_init_value['ignore_first_line']) is not bool:
                log += '忽略首行检查失败,原因:忽略首行整体数据缺失或数据异常,请联系管理员;'
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
            # share_all_threads
            self.config_share_all_threads = self.plugin_value['share_all_threads']
            # 进行数据填充
            try:
                parameter_wb = xlrd.open_workbook(
                    '%s/files/%s' % (self.base_data['file_path'], self.config_uuid),
                    encoding_override=None if self.config_auto_encode else self.config_encode
                )
            except Exception as e:
                return False, '参数化文件打开失败,原因:%s;' % repr(e)
            else:
                for sheet_name, parameter_keys in self.config_var_names:
                    # 如果存在该sheet则没事,如果不存在直接报错且程序终止
                    if sheet_name != '' and parameter_keys != '' and sheet_name in parameter_wb.sheet_names():
                        parameter_ws = parameter_wb.sheet_by_name(sheet_name)
                        # 开始流处理
                        sheet_data = []
                        # 有效行数
                        nrows = parameter_ws.nrows
                        # 有效列数
                        ncols = parameter_ws.ncols
                        # 缓冲次数
                        cache_time = 0
                        # 缓冲区行数x行
                        cache_nrow = 1000
                        cache_index = 0
                        cache_max_time = math.ceil(nrows / cache_nrow)
                        while cache_time < cache_max_time:
                            rrow = 0
                            # 缓冲区
                            cache_io = BytesIO()
                            cache_workbook = xlwt.Workbook(encoding='utf-8')
                            cache_sheet = cache_workbook.add_sheet('Sheet')
                            if (cache_time + 1) * cache_nrow > nrows:
                                cache_nrow = nrows - cache_time * cache_nrow
                            for row in range(cache_index, cache_index + cache_nrow):
                                row_content = parameter_ws.row_values(row)
                                for col in range(0, ncols):
                                    cache_sheet.write(rrow, col, row_content[col])
                                rrow += 1
                            cache_workbook.save(cache_io)
                            df = pandas.read_excel(cache_io, header=None, dtype=numpy.str)
                            sheet_data += df.values.tolist()
                            cache_index += cache_nrow
                            cache_time += 1
                            cache_io.close()
                        ExcelDataSetConfig.excelIterator.init(
                            _share=self.config_share_all_threads,
                            _data=sheet_data[1 if self.config_ignore_first_line else 0:],  # 忽略首行
                            _keys=parameter_keys
                        )
                        for cvn in parameter_keys.split(','):
                            self.run_parameter_controller.update({cvn: ExcelDataSetConfig.excelIterator})
                    else:
                        return False, '表单Sheet名不存在;'

                return True, None

    def run_test(self):
        # 对于本参数化插件来说，第一次被调用run_test即调用init_before_run去初始化迭代器
        if not ExcelDataSetConfig.excelIterator.inited:
            run_init_result, run_init_log = self.init_before_run()
            # 如果失败强行终止测试任务运行
            if not run_init_result:
                self.trans_init_log(run_init_log)
                kill_test_task_job(self.base_data)
        ExcelDataSetConfig.excelIterator.next(vuser_num=self.vuser_index)
