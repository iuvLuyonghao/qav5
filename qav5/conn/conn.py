import logging
import paramiko
import timeit
import pymysql
import redis
import cx_Oracle
from qav5.utils import SingletonIfSameParameters
import psycopg2

LOGGER = logging.getLogger(__name__)


class _Proxy(object):

    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, item):
        return getattr(self.obj, item)

    def __setattr__(self, key, value):
        if key == "obj":
            object.__setattr__(self, key, value)
        else:
            try:
                object.__getattribute__(self, key)
                object.__setattr__(self, key, value)
            except AttributeError:
                setattr(self.obj, key, value)


class _ConnectionProxy(_Proxy):

    def __getattr__(self, item):
        if item == "cursor":
            def _cursor(*args, **kwargs):
                return _CursorProxy(getattr(self.obj, item)(*args, **kwargs))

            return _cursor
        if item == "close":
            def return_null(*args, **kwargs):
                LOGGER.warning("call `forced_close` if really wanner shutdown the mysql connections")
                return None

            return return_null
        if item == "forced_close":
            return super().__getattr__("close")
        return super(_ConnectionProxy, self).__getattr__(item)


class _CursorProxy(_Proxy):

    def __enter__(self):
        """不返回self.obj.__enter__，这样会导致不自动打印sql语句"""
        if getattr(self.obj, "__enter__"):  # 不用去捕捉异常
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return getattr(self.obj, "__exit__")(exc_type, exc_val, exc_tb)

    def __getattr__(self, item):
        if item == "execute":
            def _execute(*args, **kwargs):
                start = timeit.default_timer()
                ret = getattr(self.obj, item)(*args, **kwargs)
                execution_time = int((timeit.default_timer() - start) * 1000)
                if isinstance(self.obj, pymysql.cursors.Cursor):
                    if execution_time < 3000:
                        LOGGER.info(self.obj.mogrify(*args, **kwargs), extra={"execution_time": execution_time})
                    else:
                        LOGGER.warning(self.obj.mogrify(*args, **kwargs), extra={"execution_time": execution_time})
                else:
                    if execution_time < 3000:
                        LOGGER.info(self.obj.statement, extra={"execution_time": execution_time})  # 打印sql语句
                    else:
                        LOGGER.warning(self.obj.statement, extra={"execution_time": execution_time})
                return ret

            return _execute
        return super(_CursorProxy, self).__getattr__(item)


class MySQLConnectionMgr(metaclass=SingletonIfSameParameters):
    """
    确保只会连接一次mysql
    """

    BACKEND_PYMYSQL = "pymysql"
    BACKEND_OFFICIALMYSQL = "mysql-connector-python"

    def __init__(self, **kwargs):
        self._cnx = dict()
        self._backend = self.BACKEND_OFFICIALMYSQL
        self.kwargs = kwargs

    @property
    def _official_connection(self):
        try:
            import mysql.connector
        except ImportError:
            LOGGER.error("mysql-connector-python is not installed, switch to pymysql")
            self._backend = self.BACKEND_PYMYSQL
            return self._pymysql_connection
        cnx = self._cnx.get(self.BACKEND_OFFICIALMYSQL, None)
        if cnx is None:
            LOGGER.info("start to connect mysql", extra=self.kwargs)
            cnx = _ConnectionProxy(mysql.connector.connect(**self.kwargs))
            # cnx = mysql.connector.connect(**self.kwargs)
            cnx.autocommit = True  # 解决各种疑难杂症...
            self._cnx[self.BACKEND_OFFICIALMYSQL] = cnx
        else:
            if not cnx.is_connected():
                LOGGER.info("trying to reconnect mysql")
                cnx.reconnect()
                cnx.autocommit = True
        return cnx

    @property
    def _pymysql_connection(self):
        cnx = self._cnx.get(self.BACKEND_PYMYSQL, None)
        if cnx is None:
            con_params = self.kwargs.copy()
            cursor_cls = con_params.get('cursorclass')
            if cursor_cls:
                con_params['cursorclass'] = cursor_cls.__name__
            LOGGER.info("start to connect mysql", extra=con_params)
            cnx = _ConnectionProxy(pymysql.connect(**self.kwargs))
            cnx.autocommit_mode = True
            self._cnx[self.BACKEND_PYMYSQL] = cnx
        else:
            if not cnx.open:
                LOGGER.info("trying to reconnect mysql")
                cnx.connect()
        return cnx

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, backend):
        if backend == self.BACKEND_OFFICIALMYSQL:
            self._backend = backend
        else:
            self._backend = self.BACKEND_PYMYSQL

    @property
    def connection(self):
        if self.backend == self.BACKEND_OFFICIALMYSQL:
            return self._official_connection
        return self._pymysql_connection


class SSHClientMgr(metaclass=SingletonIfSameParameters):

    def __init__(self, **kwargs):
        self._client = paramiko.SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.has_connected = False
        self.kwargs = kwargs

    @property
    def client(self):
        if self.has_connected is False:
            LOGGER.info("start a ssh connection", extra=self.kwargs)
            kwargs = self.kwargs.copy()
            host = kwargs.pop('host', None) or kwargs.pop('hostname', None)
            if not host:
                raise ValueError
            self._client.connect(host, **kwargs)
            self.has_connected = True
        return self._client


class RedisConnectionMgr(metaclass=SingletonIfSameParameters):

    def __init__(self, **kwargs):
        self._redis_client = None
        self._params = kwargs

    @property
    def client(self):
        if self._redis_client is None:
            LOGGER.info("start a redis connection", extra=self._params)
            self._redis_client = redis.StrictRedis(**self._params, decode_responses=True)
        return self._redis_client


class RedisConnection:
    def __init__(self, host, port, password, decode_responses=True):
        """ Connect to the Redis """
        try:
            self.redis = redis.Redis(host=host, port=port, password=password, decode_responses=decode_responses)
        except redis.ConnectionError as e:
            LOGGER.error("redis client connect error: %s" % e)

    def get_information(self, key):
        """获取指定key的值"""
        return self.redis.get(key)

    def set_value(self, key, value):
        """向指定key添加value"""
        try:
            self.redis.set(key, value)
        except redis.ResponseError as e:
            LOGGER.error("redis set datas error: %s" % e)


class OracleClient:

    def __init__(self, username, password, connection_str):
        """ Connect to the database. """
        try:
            self.conn = cx_Oracle.connect(username, password, connection_str, encoding="UTF-8")
            self.conn.autocommit = True  # 自动commit
        except cx_Oracle.DatabaseError as e:
            LOGGER.error("oracle client connect error: s%", e)

        self.cursor = self.conn.cursor()

    def execute_query(self, query, bindvars={}):
        """ exec. select sql
        :param query: sql select
        :param bindvars dict var
        :return:
        """
        return self.cursor.execute(query, bindvars)

    def execute_no_query(self, sql, bindvars={}):
        """ sql update, delete
        :param sql: sql statements
        :param bindvars is a dictionary of variables you pass to execute.
        exp: cursor.execute('SELECT * FROM employees WHERE department_id=:dept_id AND salary>:sal', named_params)
        """

        try:
            self.cursor.execute(sql, bindvars)
            return self.cursor.rowcount
        except cx_Oracle.DatabaseError as e:
            LOGGER.error("oracle client execute no_query sql error: %s", e)

    def disconnect(self):
        """
        Disconnect from the database. If this fails, log error
        """

        try:
            self.cursor.close()
            self.conn.close()
        except cx_Oracle.DatabaseError as e:
            LOGGER.error("oracle client close error: %s", e)


class PostGreSQLClient:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        try:
            self.conn = psycopg2.connect(host=self.host, port=self.port, database=self.database, user=self.user,
                                         password=self.password)
        except psycopg2.DatabaseError as e:
            LOGGER.error("pg connection error: %s", e)

        self.cursor = self.conn.cursor()

    def execute_query(self, query, bindvar: tuple = None):
        """ exec. select sql
        :param query: sql select
        :param bindvar exp. (,)
        :return:
        """
        self.cursor.execute(query, bindvar)
        return self.cursor.fetchall()

    def execute_no_query(self, sql, bindvar: tuple, commit=True):
        """sql update, delete
        :param sql: Execute whatever SQL statements are passed to the method
        :param bindvar is a dictionary of variables you pass to execute.
        :param commit: True by default
        :return:
        """

        try:
            self.cursor.execute(sql, bindvar)
        except psycopg2.DatabaseError as e:
            LOGGER.error("pg client execute no_query sql error: %s", e)
        # commit by default
        if commit:
            self.conn.commit()

    def disconnect(self):
        """
        Disconnect from the database. If this fails, log error
        """

        try:
            self.cursor.close()
            self.conn.close()
        except psycopg2.DatabaseError as e:
            LOGGER.error("pg client close error: %s", e)

if __name__=='__main__':
    OracleClient('projects','reach123','192.168.9.248:1521/REACH')