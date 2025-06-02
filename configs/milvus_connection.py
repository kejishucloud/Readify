# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List, Union
import os
import time

from loguru import logger
from pymilvus import connections, Collection, utility

from configs.config_loader import ConfigLoader, default_config_loader, get_database_config

class MilvusConnection:
    """
    Milvus 连接类，提供与 Milvus 实例的连接管理。
    支持通过配置文件或显式参数进行同步连接，支持自动重试。
    """
    def __init__(
        self,
        db_type: str = 'milvus',
        config_loader: Optional[ConfigLoader] = None,
        url: Optional[str] = None,
        database: Optional[str] = None,
        retry: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化连接配置。
        :param db_type: 配置类型名称，默认 'milvus'
        :param config_loader: 配置加载器实例，默认使用全局默认加载器
        :param url: 连接 URL (host:port)，优先级高于配置文件
        :param database: 指定数据库名称，优先级高于配置文件
        :param retry: 最大重试次数
        :param retry_delay: 重试间隔秒数
        """
        self.config_loader = config_loader or default_config_loader
        self.db_type = db_type
        self.url = url
        self.retry = retry
        self.retry_delay = retry_delay
        self.database = database

        # 从配置加载器或 URL 解析配置
        cfg = {} if url else get_database_config(self.db_type, self.config_loader)
        self.host: Optional[str] = cfg.get('host')
        self.port: Optional[int] = cfg.get('port')
        self.username: Optional[str] = cfg.get('username')
        self.password: Optional[str] = cfg.get('password')
        if not url:
            self.database = self.database or cfg.get('database', 'default')

        self.secure: bool = cfg.get('secure', False)
        self.timeout: int = cfg.get('timeout', 10)
        self._alias: str = 'default'
        self._connected: bool = False

        if self.url:
            parts = self.url.split(':')
            self.host = parts[0]
            if len(parts) > 1:
                try:
                    self.port = int(parts[1])
                except ValueError:
                    logger.warning(f"无法解析端口: {parts[1]}")

    def connect(self) -> bool:
        """
        建立到 Milvus 的连接，失败时重试。
        :return: 连接是否成功
        """
        attempts = 0
        while attempts < self.retry:
            try:
                connections.connect(
                    alias=self._alias,
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    db_name=self.database,
                    secure=self.secure,
                    timeout=self.timeout
                )
                if connections.has_connection(self._alias):
                    self._connected = True
                    return True
                raise ConnectionError("Milvus 连接创建失败")
            except Exception as e:
                attempts += 1
                logger.warning(f"第{attempts}次连接失败: {e}")
                time.sleep(self.retry_delay)
        return False

    def ensure_connection(self) -> None:
        """
        确保已建立连接，否则抛出异常。
        """
        if not self._connected:
            if not self.connect():
                raise ConnectionError("无法建立 Milvus 连接")

    def close(self) -> None:
        """
        断开与 Milvus 的连接。
        """
        if self._connected:
            connections.disconnect(self._alias)
            self._connected = False

    def list_collections(self) -> List[str]:
        """
        列出当前数据库下所有集合名称。
        :return: 集合名称列表
        """
        self.ensure_connection()
        return utility.list_collections()

    def has_collection(self, name: str) -> bool:
        """
        检查指定集合是否存在。
        :param name: 集合名称
        :return: 是否存在
        """
        self.ensure_connection()
        return utility.has_collection(name)

    def drop_collection(self, name: str) -> None:
        """
        删除指定集合及其所有数据。
        :param name: 集合名称
        """
        self.ensure_connection()
        utility.drop_collection(name)

    def get_collection(self, name: str) -> Collection:
        """
        获取已存在集合的对象。
        :param name: 集合名称
        :return: Collection 实例
        """
        self.ensure_connection()
        return Collection(name=name, using=self._alias)


if __name__ == "__main__":
    # 连接测试
    print("Milvus连接测试...")
    conn = MilvusConnection()
    conn.connect()
    collections = conn.list_collections()
    print(f"Milvus集合列表: {collections}")
    conn.close()
