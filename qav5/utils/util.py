# -*- coding: utf-8 -*-

import hashlib
import random
import string
import threading
from decimal import Decimal


class Bunch(dict):
    """
    >>> d1 = dict(username='admin', password=123456, datastore={'code': 7788})
    >>> bunch = Bunch(d1)
    >>> bunch.username == d1['username']
    True
    >>> bunch.datastore.code == 7788
    True
    >>> bunch.name = 'hello'
    """

    def __getattr__(self, item):
        try:
            object.__getattribute__(self, item)
        except AttributeError:
            try:
                value = super(Bunch, self).__getitem__(item)
            except KeyError as e:
                raise AttributeError('attribute named {} was not found'.format(item)) from e
            else:
                if isinstance(value, dict):
                    return Bunch(value)
                return value

    def __setattr__(self, key, value):
        super(Bunch, self).__setitem__(key, value)


def md5_str(content, encoding='utf-8'):
    """计算字符串的MD5值

    :param content:输入字符串
    :param encoding: 编码方式
    :return:
    """
    m = hashlib.md5(content.encode(encoding))
    return m.hexdigest()


def md5_file(fp, block=1024):
    """计算文件的MD5值

    :param fp:文件路径
    :param block:读取的块大小
    :return:
    """
    m = hashlib.md5()
    with open(fp, 'rb') as f:
        while 1:
            c = f.read(block)
            if c:
                m.update(c)
            else:
                break
    return m.hexdigest()


def gen_rand_str(length=8, s_type='hex', prefix=None, postfix=None):
    """生成指定长度的随机数，可设置输出字符串的前缀、后缀字符串

    :param length: 随机字符串长度
    :param s_type:
    :param prefix: 前缀字符串
    :param postfix: 后缀字符串
    :return:
    """
    if s_type == 'digit':
        formatter = "{:0" + str(length) + "}"
        mid = formatter.format(random.randrange(10**length))
    elif s_type == 'ascii':
        mid = "".join([random.choice(string.ascii_letters) for _ in range(length)])
    elif s_type == "hex":
        formatter = "{:0" + str(length) + "x}"
        mid = formatter.format(random.randrange(16**length))
    else:
        mid = "".join([random.choice(string.ascii_letters+string.digits) for _ in range(length)])

    if prefix is not None:
        mid = prefix + mid
    if postfix is not None:
        mid = mid + postfix
    return mid


def low_case_to_camelcase(arg_name):
    """
    category_id -> categoryId
    :param arg_name:
    :return:
    """
    args = arg_name.split("_")
    return args[0]+"".join([a.capitalize() for a in args[1:]])

def came_case_to_lowcase(arg_name):
    """
    categoryId -> category_id
    :param arg_name:
    :return:
    """
    listy = ""
    for i in range(0, len(arg_name)):
        if arg_name[i].isupper():
            listy += '_'
            listy += arg_name[i].lower()
        else:
            listy += arg_name[i]
    return listy


class Counter(object):
    """
    一个简单的线程安全的计数器,每调用一次则增加1
    C = Counter()
    C.counter
    """

    def __init__(self, start=0):
        self._counter = start
        self.lock = threading.RLock()

    @property
    def counter(self):
        self.lock.acquire()
        self._counter += 1
        ret = self._counter
        self.lock.release()
        return ret

    @property
    def current(self):
        self.lock.acquire()
        ret = self._counter
        self.lock.release()
        return ret


def merge_dicts(d1, d2):
    """合并两个dict对象,如果子节点也是dict,同样会被合并"""
    common_keys = set(d1.keys()) & set(d2.keys())
    for k in common_keys:
        if isinstance(d1[k], dict) and isinstance(d2[k], dict):
            d2[k] = merge_dicts(d1[k], d2[k])
    d1.update(d2)
    return d1


def get_str_format(deci, n):
    x = "{:." + str(n) + "f}"
    return x.format(Decimal(deci))
