# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, Union, List, Tuple
import os
import time
import asyncio
import pymysql
from pymysql.cursors import DictCursor
import aiomysql

from configs.config_loader import ConfigLoader, default_config_loader, get_database_config


class MySQLConnection:
    """
    MySQL 连接类，支持通过 URL 或配置文件进行同步和异步连接，默认重试三次。
    可以通过参数 `database` 指定在配置文件模式下使用的数据库名称。
    """

    def __init__(
        self,
        db_type: str = 'mysql',
        config_loader: Optional[ConfigLoader] = None,
        url: Optional[str] = None,
        database: Optional[str] = None,
        retry: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 MySQL 连接类。
        :param db_type: 在配置文件中对应的配置类型名称，默认 'mysql'
        :param config_loader: 配置加载器实例，默认为全局默认加载器
        :param url: MySQL 连接 URL，提供后优先使用
        :param database: 当未使用 URL 时，通过此参数指定数据库名称，优先于配置文件中的设置
        :param retry: 最大重试次数，默认 3 次
        :param retry_delay: 重试间隔时间（秒），默认 1.0 秒
        """
        self.config_loader = config_loader or default_config_loader
        self.db_type = db_type
        self.url = url
        self.retry = retry
        self.retry_delay = retry_delay
        self.database = database  # 数据库名称，优先级高于配置文件

        # 从配置加载器获取数据库配置
        cfg = {} if url else get_database_config(self.db_type, self.config_loader)
        self.host: Optional[str] = cfg.get('host')
        self.port: Optional[int] = cfg.get('port')
        self.username: Optional[str] = cfg.get('username')
        self.password: Optional[str] = cfg.get('password')
        
        # 如果未传入 database，使用配置文件中的
        if not url:
            self.database = self.database or cfg.get('database')
            
        # 其他连接参数
        self.charset: str = cfg.get('charset', 'utf8mb4')
        self.connect_timeout: int = cfg.get('connect_timeout', 10)
        self.autocommit: bool = cfg.get('autocommit', True)
        self.use_unicode: bool = cfg.get('use_unicode', True)
        self.ssl_mode: Optional[str] = cfg.get('ssl_mode')
        self.ssl: Optional[Dict[str, str]] = cfg.get('ssl')
        self.max_allowed_packet: int = cfg.get('max_allowed_packet', 16 * 1024 * 1024)

        # 客户端实例
        self._sync_conn = None
        self._async_pool = None

    def _parse_url(self) -> Tuple[str, int, str, str, str]:
        """
        解析MySQL URL 字符串，格式为 mysql://username:password@host:port/database。
        :return: (host, port, username, password, database) 元组
        """
        if not self.url:
            raise ValueError("URL不存在")
            
        # URL 例如: mysql://username:password@host:port/database
        url = self.url
        if url.startswith("mysql://"):
            url = url[8:]
        
        auth_part, conn_part = url.split('@', 1) if '@' in url else ("", url)
        
        # 解析认证部分
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
        else:
            username, password = auth_part, ""
            
        # 解析连接部分
        if '/' in conn_part:
            host_port, database = conn_part.split('/', 1)
        else:
            host_port, database = conn_part, ""
            
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host, port = host_port, 3306
            
        return host, port, username, password, database

    def connect_sync(self) -> pymysql.connections.Connection:
        """
        建立同步 MySQL 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: pymysql.connections.Connection 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                # 创建连接
                if self.url:
                    host, port, username, password, database = self._parse_url()
                    conn = pymysql.connect(
                        host=host,
                        port=port,
                        user=username,
                        password=password,
                        database=database,
                        charset=self.charset,
                        connect_timeout=self.connect_timeout,
                        autocommit=self.autocommit,
                        use_unicode=self.use_unicode,
                        ssl=self.ssl,
                        max_allowed_packet=self.max_allowed_packet,
                        cursorclass=DictCursor
                    )
                else:
                    if not self.database:
                        raise ValueError("数据库名称未配置，请传入参数 `database` 或在配置文件中添加")
                    
                    conn = pymysql.connect(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        database=self.database,
                        charset=self.charset,
                        connect_timeout=self.connect_timeout,
                        autocommit=self.autocommit,
                        use_unicode=self.use_unicode,
                        ssl=self.ssl,
                        max_allowed_packet=self.max_allowed_packet,
                        cursorclass=DictCursor
                    )

                # 验证连接
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    
                self._sync_conn = conn
                return conn
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                time.sleep(self.retry_delay)

    async def connect_async(self) -> aiomysql.Pool:
        """
        建立异步 MySQL 连接池，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: aiomysql.Pool 连接池实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                if self.url:
                    host, port, username, password, database = self._parse_url()
                    pool = await aiomysql.create_pool(
                        host=host,
                        port=port,
                        user=username,
                        password=password,
                        db=database,
                        charset=self.charset,
                        connect_timeout=self.connect_timeout,
                        autocommit=self.autocommit,
                        ssl=self.ssl
                    )
                else:
                    if not self.database:
                        raise ValueError("数据库名称未配置，请传入参数 `database` 或在配置文件中添加")
                    
                    pool = await aiomysql.create_pool(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        db=self.database,
                        charset=self.charset,
                        connect_timeout=self.connect_timeout,
                        autocommit=self.autocommit,
                        ssl=self.ssl
                    )

                # 验证连接
                async with pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute('SELECT 1')
                        
                self._async_pool = pool
                return pool
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                await asyncio.sleep(self.retry_delay)

    def close_sync(self) -> None:
        """
        关闭同步 MySQL 连接。
        """
        if self._sync_conn:
            self._sync_conn.close()

    async def close_async(self) -> None:
        """
        关闭异步 MySQL 连接池。
        """
        if self._async_pool:
            self._async_pool.close()
            await self._async_pool.wait_closed()


if __name__ == "__main__":
    # 同步连接测试
    print("同步连接测试...")
    conn = MySQLConnection(database="test_db")
    db = conn.connect_sync()
    with db.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"MySQL 版本: {version}")
    conn.close_sync()

    # 异步连接测试
    print("异步连接测试...")
    async def async_test():
        conn2 = MySQLConnection(database="test_db")
        pool = await conn2.connect_async()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT VERSION()")
                version = await cursor.fetchone()
                print(f"MySQL 异步版本: {version[0]}")
        await conn2.close_async()

    asyncio.run(async_test())
