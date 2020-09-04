# -*- coding: utf-8 -*-

from abc import ABCMeta

datastore_attr_name = '__datastore__'


class LinkedAttr:
    """
    该描述符实现了自动根据id属性映射到了具体的model对象
    eg: merchant.store = "12345"
    merchant.store 不再返回一个字符串,而是一个StoreData对象(如果id存在)
    """

    def __init__(self, attr_name):
        if attr_name == "":
            raise ValueError("disallowed empty attr name")
        self.attr_name = attr_name

    def __get__(self, instance, owner):
        data_store = getattr(instance, datastore_attr_name)
        val = instance.__dict__[self.attr_name]
        for f in (data_store.find_obj_by_id, data_store.find_obj_by_label, data_store.find_obj_by_group):
            ret = f(val)
            if ret is not None:
                return ret

    def __set__(self, instance, value):
        instance.__dict__[self.attr_name] = value


class GroupedAttr(object):

    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __get__(self, instance, owner):
        data_store = getattr(instance, datastore_attr_name)
        ret = []
        for g in instance.__dict__.get(self.attr_name, []):
            for f in (data_store.find_obj_by_id, data_store.find_obj_by_label, data_store.find_obj_by_group):
                s = f(g)
                if s is not None:
                    ret.append(s)
                    break
        return ret

    def __set__(self, instance, value):
        if instance.__dict__.get(self.attr_name, None) is None:
            if isinstance(value, list) or isinstance(value, tuple):
                instance.__dict__[self.attr_name] = value  # value 是list或者tuple
            else:
                instance.__dict__[self.attr_name] = [value]  # value 是string
        else:
            if isinstance(value, list) or isinstance(value, tuple):
                instance.__dict__[self.attr_name].extend(value)
            else:
                instance.__dict__[self.attr_name].append(value)


class AbstractData(metaclass=ABCMeta):
    __datastore__ = None

    @classmethod
    def inst_from_dict(cls, d):
        pass


class MetaData(AbstractData):

    def __getitem__(self, item):
        if item.endswith("_id") and hasattr(self, item[:-3]):
            return getattr(getattr(self, item[:-3]), "id")
        raise AttributeError("not attribute named: {}".format(item))

    def __getattr__(self, item):
        return self.__getitem__(item)

    @classmethod
    def inst_from_dict(cls, d):
        instance = cls()
        for k, v in d.items():
            setattr(instance, k, v)
        return instance

    def __repr__(self):
        return "<{}> - {} - {}".format(self.__class__.__name__, self.__datastore__.__repr__(),
                                       {k: v for k, v in self.__dict__.items() if k != datastore_attr_name})
