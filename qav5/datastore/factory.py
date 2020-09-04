# -*- coding: utf-8 -*-

import uuid
from .model import MetaData
from .datastore import DataStore


class DataFactory:
    obj_map = {"normal": MetaData}

    def __init__(self, data_store):
        if not isinstance(data_store, DataStore):
            raise TypeError("need an instance of DataStore, not {}".format(type(data_store)))
        self.data_store = data_store

    def create_data_inst(self, record, auto_insert_id=True):
        """实例化MetaData的子类

        :param record: eg. {"id": "123", "@object": "people", "name": "Jack", "@extended": {"label": "default"}}
        :param auto_insert_id:
        :return:
        """
        if not isinstance(record, dict):
            raise TypeError('need a dict instance')

        if 'id' not in record:
            if auto_insert_id:
                record['id'] = str(uuid.uuid4())
            else:
                raise ValueError("lack of `id` property")

        obj_type = record.pop('@object', "normal")
        extended = record.pop("@extended", None)
        namespace = label = group = None
        if extended:
            namespace = extended.get("namespace", None)
            label = extended.get("label", None)
            group = extended.get("group", None)

        inst = self.obj_map[obj_type].inst_from_dict(record)
        self.data_store.receive(inst, label=label, group=group, namespace=namespace)
        return inst

    def update_obj_map(self, new_map):
        """更新对象class映射关系"""
        for k, v in new_map.items():
            if not issubclass(v, MetaData):
                raise TypeError("expect a subclass of 'MetaData', not {}".format(v.__class__.__name__))

        self.obj_map.update(new_map)
