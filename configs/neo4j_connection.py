# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List, Tuple, Union
import os
import time
import asyncio
from neo4j import GraphDatabase
import aioneo4j
from loguru import logger

from configs.config_loader import ConfigLoader, default_config_loader, get_database_config


class Neo4jConnection:
    """
    Neo4j 连接类，支持通过 URL 或配置文件进行同步和异步连接，默认重试三次。
    新增 skip_default_database 开关：如果为 True，则 connect_sync/async
    建立连接时不会在 session() 中指定 database。
    """

    def __init__(
            self,
            db_type: str = 'neo4j',
            config_loader: Optional[ConfigLoader] = None,
            url: Optional[str] = None,
            database: Optional[str] = None,
            retry: int = 3,
            retry_delay: float = 1.0,
            skip_default_database: bool = False,
    ):
        """
        :param db_type:      配置文件中对应的数据库类型，默认为 'neo4j'
        :param config_loader: 配置加载器实例，默认为 global default_config_loader
        :param url:          完整 Bolt URI，如 bolt://host:port
        :param database:     默认要连接的数据库名，若 skip_default_database=True 则忽略此参数
        :param retry:        最大重试次数
        :param retry_delay:  重试间隔（秒）
        :param skip_default_database: 如果为 True，则 connect 时不指定 database 参数
        """
        # 加载配置
        self.config_loader = config_loader or default_config_loader
        cfg = {} if url else get_database_config(db_type, self.config_loader)
        # 基本参数
        self.url = url
        self.host = cfg.get('host')
        self.port = cfg.get('port')
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.encrypted = cfg.get('encrypted', False)
        self.connection_timeout = cfg.get('connection_timeout', 30)
        self.max_connection_lifetime = cfg.get('max_connection_lifetime', 3600)
        self.max_connection_pool_size = cfg.get('max_connection_pool_size', 50)

        self.retry = retry
        self.retry_delay = retry_delay
        # 如果跳过默认库，就清空 database
        self.skip_default_database = skip_default_database
        self.database = None if skip_default_database else (database or cfg.get('database'))

        # 驱动实例占位
        self._sync_driver = None
        self._async_client = None

    def _make_uri(self) -> str:
        """
        构造 Bolt URI，如果用户传入 url 则优先使用，否则拼装。
        """
        if self.url:
            return self.url
        scheme = "neo4j+s" if self.encrypted else "bolt"
        return f"{scheme}://{self.host}:{self.port}"

    def connect_sync(self) -> GraphDatabase.driver:
        """
        同步建立 Bolt 连接。System 库使用 SHOW DATABASES 验证，其它库使用 RETURN 1。
        """
        attempts = 0
        while attempts < self.retry:
            try:
                uri = self._make_uri()
                auth = (self.username, self.password) if self.username else None
                driver = GraphDatabase.driver(
                    uri,
                    auth=auth,
                    connection_timeout=self.connection_timeout,
                    max_connection_lifetime=self.max_connection_lifetime,
                    max_connection_pool_size=self.max_connection_pool_size,
                )
                # 验证连接
                if self.database == "system":
                    # system 库只支持 SHOW DATABASES
                    with driver.session(database="system") as sess:
                        sess.run("SHOW DATABASES")  # 列出所有库，验证权限 :contentReference[oaicite:4]{index=4}
                else:
                    # 普通库使用轻量查询
                    with driver.session(database=self.database) as sess:
                        sess.run("RETURN 1")  # 简单验证 :contentReference[oaicite:5]{index=5}
                self._sync_driver = driver
                return driver
            except Exception as e:
                attempts += 1
                logger.warning(
                    f"第 {attempts} 次同步连接失败: {e!r}，{self.retry - attempts} 次重试剩余"
                )
                time.sleep(self.retry_delay)
        raise RuntimeError(f"Sync connect failed after {self.retry} attempts")

    async def connect_async(self) -> aioneo4j.Neo4j:
        """
        异步建立 HTTP(s) 连接。System 库使用 SHOW DATABASES 验证，其它库使用 RETURN 1。
        """
        attempts = 0
        while attempts < self.retry:
            try:
                uri = self._make_uri()
                if not uri.startswith(("http://", "https://")):
                    uri = uri.replace("bolt://", "http://").replace("neo4j://", "http://")
                if self.username:
                    proto, rest = uri.split("://", 1)
                    uri = f"{proto}://{self.username}:{self.password}@{rest}"
                client = aioneo4j.Neo4j(uri, self.database or "")
                # 验证连接
                if self.database == "system":
                    await client.cypher("SHOW DATABASES")  # 异步执行管理命令 :contentReference[oaicite:6]{index=6}
                else:
                    await client.cypher("RETURN 1", database=self.database)
                self._async_client = client
                return client
            except Exception as e:
                attempts += 1
                logger.warning(f"[async] 第 {attempts} 次连接失败: {e!r}，{self.retry - attempts} 次重试剩余")
                await asyncio.sleep(self.retry_delay)
        raise RuntimeError(f"Async connect failed after {self.retry} attempts")

    def close_sync(self) -> None:
        """关闭同步驱动"""
        if self._sync_driver:
            self._sync_driver.close()
            self._sync_driver = None

    async def close_async(self) -> None:
        """关闭异步客户端"""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None


if __name__ == "__main__":
    # 同步连接测试
    print("同步连接测试...")
    conn = Neo4jConnection(database='neo4j')
    driver = conn.connect_sync()
    with driver.session(database=conn.database) as session:
        result = session.run("MATCH (n) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"Neo4j 节点数量: {count}")
    conn.close_sync()
