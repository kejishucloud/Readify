# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, Union, List, Tuple
import os
import time
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncpg

from configs.config_loader import ConfigLoader, default_config_loader, get_database_config


class PostgreSQLConnection:
    """
    PostgreSQL 连接类，支持通过 URL 或配置文件进行同步和异步连接，默认重试三次。
    可以通过参数 `database` 指定在配置文件模式下使用的数据库名称。
    """

    def __init__(
        self,
        db_type: str = 'postgresql',
        config_loader: Optional[ConfigLoader] = None,
        url: Optional[str] = None,
        database: Optional[str] = None,
        retry: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 PostgreSQL 连接类。
        :param db_type: 在配置文件中对应的配置类型名称，默认 'postgresql'
        :param config_loader: 配置加载器实例，默认为全局默认加载器
        :param url: PostgreSQL 连接 URL，提供后优先使用
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
        self.connect_timeout: int = cfg.get('connect_timeout', 10)
        self.application_name: Optional[str] = cfg.get('application_name')
        self.ssl_mode: Optional[str] = cfg.get('ssl_mode')
        self.ssl: Optional[Dict[str, str]] = cfg.get('ssl')
        self.min_size: int = cfg.get('min_size', 1)
        self.max_size: int = cfg.get('max_size', 10)

        # 客户端实例
        self._sync_conn = None
        self._async_pool = None

    def _build_dsn(self) -> str:
        """
        从配置参数构建 PostgreSQL 连接字符串。
        :return: PostgreSQL 连接字符串
        """
        parts = []
        
        if self.host:
            parts.append(f"host={self.host}")
        
        if self.port:
            parts.append(f"port={self.port}")
            
        if self.username:
            parts.append(f"user={self.username}")
            
        if self.password:
            parts.append(f"password={self.password}")
            
        if self.database:
            parts.append(f"dbname={self.database}")
            
        if self.connect_timeout:
            parts.append(f"connect_timeout={self.connect_timeout}")
            
        if self.application_name:
            parts.append(f"application_name={self.application_name}")
            
        if self.ssl_mode:
            parts.append(f"sslmode={self.ssl_mode}")
            
        return " ".join(parts)

    def connect_sync(self) -> psycopg2.extensions.connection:
        """
        建立同步 PostgreSQL 连接，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: psycopg2.extensions.connection 实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                if self.url:
                    conn = psycopg2.connect(self.url, cursor_factory=RealDictCursor)
                else:
                    if not self.database:
                        raise ValueError("数据库名称未配置，请传入参数 `database` 或在配置文件中添加")
                    
                    dsn = self._build_dsn()
                    conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)

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

    async def connect_async(self) -> asyncpg.Pool:
        """
        建立异步 PostgreSQL 连接池，优先使用 URL，其次通过配置文件和传入参数，失败时重试。
        :return: asyncpg.Pool 连接池实例
        """
        attempts = 0
        while attempts < self.retry:
            try:
                if self.url:
                    pool = await asyncpg.create_pool(
                        dsn=self.url,
                        min_size=self.min_size,
                        max_size=self.max_size,
                        timeout=self.connect_timeout
                    )
                else:
                    if not self.database:
                        raise ValueError("数据库名称未配置，请传入参数 `database` 或在配置文件中添加")
                    
                    pool = await asyncpg.create_pool(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        database=self.database,
                        min_size=self.min_size,
                        max_size=self.max_size,
                        timeout=self.connect_timeout,
                        ssl=self.ssl_mode == 'require'
                    )

                # 验证连接
                async with pool.acquire() as conn:
                    await conn.execute('SELECT 1')
                    
                self._async_pool = pool
                return pool
            except Exception:
                attempts += 1
                if attempts >= self.retry:
                    raise
                await asyncio.sleep(self.retry_delay)

    def close_sync(self) -> None:
        """
        关闭同步 PostgreSQL 连接。
        """
        if self._sync_conn:
            self._sync_conn.close()

    async def close_async(self) -> None:
        """
        关闭异步 PostgreSQL 连接池。
        """
        if self._async_pool:
            await self._async_pool.close()


if __name__ == "__main__":
    # 同步连接测试
    print("同步连接测试...")
    conn = PostgreSQLConnection(database='webui')
    db = conn.connect_sync()
    with db.cursor() as cursor:
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"PostgreSQL 版本: {version}")
    conn.close_sync()

    # 异步连接测试
    print("异步连接测试...")
    async def async_test():
        conn2 = PostgreSQLConnection(database="test_db")
        pool = await conn2.connect_async()
        async with pool.acquire() as connection:
            version = await connection.fetchval("SELECT version()")
            print(f"PostgreSQL 异步版本: {version}")
        await conn2.close_async()

    asyncio.run(async_test())
