# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, Union, List
import os
import time
import asyncio
import redis
from redis.asyncio import Redis as AsyncRedis

from configs.config_loader import ConfigLoader, default_config_loader, get_database_config


class RedisConnection:
    """
    Redis 连接类，支持通过 URL 或配置文件进行同步和异步连接，默认重试三次。
    可以通过参数 `database` 指定在配置文件模式下使用的数据库索引。
    """

    def __init__(
        self,
        db_type: str = 'redis',
        config_loader: Optional[ConfigLoader] = None,
        url: Optional[str] = None,
        database: Optional[int] = None,
        retry: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 Redis 连接类。
        :param db_type: 在配置文件中对应的配置类型名称，默认 'redis'
        :param config_loader: 配置加载器实例，默认为全局默认加载器
        :param url: Redis 连接 URL，提供后优先使用
        :param database: 当未使用 URL 时，通过此参数指定数据库索引，优先于配置文件中的设置
        :param retry: 最大重试次数，默认 3 次
        :param retry_delay: 重试间隔时间（秒），默认 1.0 秒
        """
        self.config_loader = config_loader or default_config_loader
        self.db_type = db_type
        self.url = url
        self.retry = retry
        self.retry_delay = retry_delay
        self.database = database  # 数据库索引，优先级高于配置文件

        # 从配置加载器获取数据库配置
        cfg = {} if url else get_database_config(self.db_type, self.config_loader)
        self.host: Optional[str] = cfg.get('host')
        self.port: Optional[int] = cfg.get('port')
        self.password: Optional[str] = cfg.get('password')
        
        # 如果未传入 database，使用配置文件中的，如果配置文件中也没有，则默认为0
        if not url and self.database is None:
            self.database = cfg.get('db', 0)
            
        # 其他连接参数
        self.socket_timeout: int = cfg.get('socket_timeout', 5)
        self.socket_connect_timeout: int = cfg.get('socket_connect_timeout', 5)
        self.decode_responses: bool = cfg.get('decode_responses', True)
        self.encoding: str = cfg.get('encoding', 'utf-8')

        # 客户端实例
        self._sync_client = None
        self._async_client = None

    def connect_sync(self) -> redis.Redis:
        """
        建立同步 Redis 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: redis.Redis 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                # 创建客户端
                if self.url:
                    client = redis.from_url(
                        self.url,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        decode_responses=self.decode_responses,
                        encoding=self.encoding
                    )
                else:
                    client = redis.Redis(
                        host=self.host,
                        port=self.port,
                        password=self.password,
                        db=self.database,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        decode_responses=self.decode_responses,
                        encoding=self.encoding
                    )

                # 验证连接
                client.ping()
                self._sync_client = client
                return client
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                time.sleep(self.retry_delay)

    async def connect_async(self) -> AsyncRedis:
        """
        建立异步 Redis 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: redis.asyncio.Redis 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                if self.url:
                    client = AsyncRedis.from_url(
                        self.url,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        decode_responses=self.decode_responses,
                        encoding=self.encoding
                    )
                else:
                    client = AsyncRedis(
                        host=self.host,
                        port=self.port,
                        password=self.password,
                        db=self.database,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        decode_responses=self.decode_responses,
                        encoding=self.encoding
                    )

                # 验证连接
                await client.ping()
                self._async_client = client
                return client
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                await asyncio.sleep(self.retry_delay)

    def close_sync(self) -> None:
        """
        关闭同步 Redis 连接。
        """
        if self._sync_client:
            self._sync_client.close()

    async def close_async(self) -> None:
        """
        关闭异步 Redis 连接。
        """
        if self._async_client:
            await self._async_client.close()


if __name__ == "__main__":
    # 同步连接测试
    print("同步连接测试...")
    conn = RedisConnection()
    client = conn.connect_sync()
    print("Redis连接成功:", client.ping())
    conn.close_sync()

    # 异步连接测试
    print("异步连接测试...")
    async def async_test():
        conn2 = RedisConnection()
        client2 = await conn2.connect_async()
        print("异步Redis连接成功:", await client2.ping())
        await conn2.close_async()

    asyncio.run(async_test())
