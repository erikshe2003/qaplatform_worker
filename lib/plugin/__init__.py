# -*- coding: utf-8 -*-

from .controller import ControllerPlugin
from .controller.testTask import TestTask
from .controller.testCaseCollention import TestCaseCollention
from .controller.testCase import TestCase

from .parameter import ParameterPlugin
from .parameter.csvDataSetConfig import CsvDataSetConfig
from .parameter.excelDataSetConfig import ExcelDataSetConfig
from .parameter.userDefinedVariables import UserDefinedVariables

from .configuration import ConfigurationPlugin
from .configuration.mysqlConnectionConfiguration import MysqlConnectionConfiguration
from .configuration.redisConnectionConfiguration import RedisConnectionConfiguration

from .timer import TimerPlugin
from .timer.constantTimer import ConstantTimer

from .request import RequestPlugin
from .request.mysqlRequest import MysqlRequest
from .request.redisRequest import RedisRequest
from .request.httpRequest import HttpRequest

from .postprocessor import PostprocessorPlugin
from .postprocessor.jsonPathExtractor import JsonPathExtractor

from .assertion import AssertionPlugin
from .assertion.httpRequestAssert import HttpRequestAssert

from .preprocessor import PreprocessorPlugin


all_plugins = {
    0: TestTask,
    1: TestCaseCollention,
    2: TestCase,
    3: CsvDataSetConfig,
    4: ExcelDataSetConfig,
    5: UserDefinedVariables,
    6: MysqlConnectionConfiguration,
    7: RedisConnectionConfiguration,
    8: ConstantTimer,
    9: MysqlRequest,
    10: RedisRequest,
    11: HttpRequest,
    12: JsonPathExtractor,
    13: HttpRequestAssert
}
