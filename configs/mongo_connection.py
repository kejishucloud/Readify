# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
import os
import time
import asyncio
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from configs.config_loader import ConfigLoader, default_config_loader, get_database_config
class MongoConnection:
    """
    MongoDB 连接类，支持通过 URL 或配置文件进行同步和异步连接，默认重试三次。
    可以通过参数 `database` 指定在配置文件模式下使用的数据库名称。
    """

    def __init__(
        self,
        db_type: str = 'mongodb',
        config_loader: Optional[ConfigLoader] = None,
        url: Optional[str] = None,
        database: Optional[str] = None,
        retry: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 MongoDB 连接类。
        :param db_type: 在配置文件中对应的配置类型名称，默认 'mongodb'
        :param config_loader: 配置加载器实例，默认为全局默认加载器
        :param url: MongoDB 连接 URL，提供后优先使用
        :param database: 当未使用 URL 时，通过此参数指定数据库名称，优先于配置文件中的设置
        :param retry: 最大重试次数，默认 3 次
        :param retry_delay: 重试间隔时间（秒），默认 1.0 秒
        """
        self.config_loader = config_loader or default_config_loader
        self.db_type = db_type
        self.url = url
        self.retry = retry
        self.retry_delay = retry_delay
        self.database = database  # 优先级高于配置文件中的数据库名

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
        self.max_pool_size: int = cfg.get('maxPoolSize', 50)
        self.connect_timeout_ms: int = cfg.get('connectTimeoutMS', 10000)
        self.server_selection_timeout_ms: int = cfg.get('serverSelectionTimeoutMS', 10000)

        # 客户端实例
        self._sync_client = None
        self._sync_db = None
        self._async_client = None
        self._async_db = None

    def connect_sync(self) -> 'pymongo.database.Database':
        """
        建立同步 MongoDB 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: pymongo.database.Database 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                # 创建客户端
                if self.url:
                    client = MongoClient(
                        self.url,
                        maxPoolSize=self.max_pool_size,
                        connectTimeoutMS=self.connect_timeout_ms,
                        serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                        connect=False
                    )
                    # 尝试解析 URI 默认数据库
                    db = client.get_default_database()
                    if not db.name:
                        raise ValueError('未在 URL 中找到数据库名称，请在 URL 中指定')
                else:
                    client = MongoClient(
                        host=self.host,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        maxPoolSize=self.max_pool_size,
                        connectTimeoutMS=self.connect_timeout_ms,
                        serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                        connect=False
                    )
                    if not self.database:
                        raise ValueError('数据库名称未配置，请传入参数 `database` 或在配置文件中添加')
                    db = client[self.database]

                # 验证连接
                db.list_collection_names()
                self._sync_client = client
                self._sync_db = db
                return db
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                time.sleep(self.retry_delay)

    async def connect_async(self) -> AsyncIOMotorDatabase:
        """
        建立异步 MongoDB 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: AsyncIOMotorDatabase 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                if self.url:
                    client = AsyncIOMotorClient(
                        self.url,
                        maxPoolSize=self.max_pool_size,
                        connectTimeoutMS=self.connect_timeout_ms,
                        serverSelectionTimeoutMS=self.server_selection_timeout_ms
                    )
                    db = client.get_default_database()
                    if not db.name:
                        raise ValueError('未在 URL 中找到数据库名称，请在 URL 中指定')
                else:
                    client = AsyncIOMotorClient(
                        host=self.host,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        maxPoolSize=self.max_pool_size,
                        connectTimeoutMS=self.connect_timeout_ms,
                        serverSelectionTimeoutMS=self.server_selection_timeout_ms
                    )
                    if not self.database:
                        raise ValueError('数据库名称未配置，请传入参数 `database` 或在配置文件中添加')
                    db = client[self.database]

                # 验证连接
                await db.list_collection_names()
                self._async_client = client
                self._async_db = db
                return db
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                await asyncio.sleep(self.retry_delay)

    def close_sync(self) -> None:
        """
        关闭同步 MongoDB 连接。
        """
        if self._sync_client:
            self._sync_client.close()

    async def close_async(self) -> None:
        """
        关闭异步 MongoDB 连接。
        """
        if self._async_client:
            self._async_client.close()


if __name__ == "__main__":
    # 同步连接测试（配置文件模式，需要传入 database）
    print("同步连接测试...")
    conn = MongoConnection(
        db_type='mongodb',
        database='jiasu_data_db'
    )
    db = conn.connect_sync()
    print("Collections:", db.list_collection_names())
    conn.close_sync()

    # 异步连接测试
    print("异步连接测试...")
    async def async_test():
        conn2 = MongoConnection(
            db_type='mongodb',
            database='jiasu_data_db'
        )
        db2 = await conn2.connect_async()
        print("Async Collections:", await db2.list_collection_names())
        await conn2.close_async()

    asyncio.run(async_test())


