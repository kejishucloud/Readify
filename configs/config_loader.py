# -*- coding: utf-8 -*-
import yaml
import os
import json
from typing import Any, Dict, Optional, Union, Type, List, Callable
import threading
import time
from functools import lru_cache
from utils.env_utils import get_env_type


class ConfigLoader:
    """
    配置加载类，用于从 YAML 文件中读取不同环境下的数据库及服务配置。
    支持配置层级覆盖和热加载。
    """
    # 记录所有实例，便于热加载时通知
    _instances = []
    # 记录文件最后修改时间
    _file_mtimes = {}
    # 控制热加载的线程锁
    _lock = threading.RLock()
    # 热加载监听线程
    _hot_reload_thread = None
    # 是否启用热加载
    _hot_reload_enabled = False

    def __init__(self,
                 filepath: Optional[str] = None,
                 environment: Optional[str] = None,
                 override_configs: Optional[List[Dict[str, Any]]] = None,
                 watch_changes: bool = False):
        """
        初始化配置加载器。
        :param filepath: YAML 配置文件路径，默认同目录下的 configs.yaml
        :param environment: 环境名称，例如 'TEST'、'PROD'，默认从 ENV 环境变量读取
        :param override_configs: 覆盖配置列表，按顺序应用，优先级高于文件配置
        :param watch_changes: 是否监控配置文件变化，自动热加载
        """
        # 确定环境类型
        self.environment = environment or get_env_type()
        # 确定配置文件路径
        if filepath:
            self.filepath = os.path.abspath(filepath)
        else:
            self.filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'configs.yaml'
            )
        
        # 多层配置覆盖列表
        self.override_configs = override_configs or []
        
        # 配置热加载
        self.watch_changes = watch_changes
        
        # 配置数据
        self._config_layers = []
        self._merged_config = {}
        
        # 添加到实例列表中，用于热加载
        with ConfigLoader._lock:
            ConfigLoader._instances.append(self)
            
        # 初始化时自动加载配置
        self.load()
        
        # 检查是否需要启动热加载线程
        if watch_changes and not ConfigLoader._hot_reload_enabled:
            self._start_hot_reload()

    def load(self) -> None:
        """
        从 YAML 文件加载配置到内存，然后应用所有覆盖配置。
        如果文件不存在或格式不正确，将抛出异常。
        """
        # 清空已有配置层
        self._config_layers = []
        
        # 加载基础配置文件
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(f"配置文件未找到: {self.filepath}")
            
        # 记录文件修改时间
        with ConfigLoader._lock:
            ConfigLoader._file_mtimes[self.filepath] = os.path.getmtime(self.filepath)
            
        # 加载文件内容
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if self.environment not in data:
            raise KeyError(f"环境 '{self.environment}' 未在配置文件中定义")
            
        # 添加基础配置层
        self._config_layers.append(data[self.environment])
        
        # 添加覆盖配置层
        for config in self.override_configs:
            self._config_layers.append(config)
            
        # 合并所有配置层
        self._merge_config_layers()

    def _merge_config_layers(self) -> None:
        """
        合并所有配置层为一个整体配置。
        后添加的层会覆盖先前的层。
        """
        result = {}
        
        # 递归合并字典函数
        def deep_merge(source: Dict, destination: Dict) -> Dict:
            for key, value in source.items():
                if key in destination:
                    if isinstance(value, dict) and isinstance(destination[key], dict):
                        deep_merge(value, destination[key])
                    else:
                        # 覆盖值
                        destination[key] = value
                else:
                    # 添加新键
                    destination[key] = value
            return destination
        
        # 按顺序应用所有配置层
        for layer in self._config_layers:
            deep_merge(layer, result)
            
        # 保存合并结果
        self._merged_config = result

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        获取指定键的配置值，支持嵌套键，通过点号分割。
        :param key: 配置键，例如 'mysql.host'
        :param default: 如果未找到键，则返回默认值
        :return: 配置值或默认值
        """
        parts = key.split('.')
        value = self._merged_config
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def set_override(self, config: Dict[str, Any], layer_index: Optional[int] = None) -> None:
        """
        设置配置覆盖层。
        :param config: 配置字典
        :param layer_index: 覆盖层索引，如果不指定则添加为最高优先级层
        """
        with ConfigLoader._lock:
            if layer_index is not None:
                # 确保layer_index有效，且跳过基础配置(索引0)
                if layer_index <= 0:
                    layer_index = 1
                
                # 扩展覆盖层列表，确保索引有效
                while len(self._config_layers) <= layer_index:
                    self._config_layers.append({})
                    
                # 设置指定索引的覆盖层
                self._config_layers[layer_index] = config
            else:
                # 添加为最高优先级层
                self._config_layers.append(config)
                
            # 重新合并配置
            self._merge_config_layers()

    def remove_override(self, layer_index: int) -> None:
        """
        移除配置覆盖层。
        :param layer_index: 覆盖层索引，索引0为基础配置，不能移除
        """
        with ConfigLoader._lock:
            if layer_index > 0 and layer_index < len(self._config_layers):
                del self._config_layers[layer_index]
                self._merge_config_layers()

    def export_config(self) -> Dict[str, Any]:
        """
        导出当前合并后的完整配置。
        :return: 配置字典
        """
        return self._merged_config.copy()

    def reload(self) -> None:
        """重新加载配置文件和所有覆盖层"""
        self.load()

    @classmethod
    def _start_hot_reload(cls) -> None:
        """启动热加载监控线程"""
        if cls._hot_reload_thread is not None and cls._hot_reload_thread.is_alive():
            return
            
        def _monitor_config_files():
            cls._hot_reload_enabled = True
            try:
                while cls._hot_reload_enabled:
                    changed_files = []
                    with cls._lock:
                        # 检查所有已记录的文件是否有变化
                        for filepath, last_mtime in cls._file_mtimes.items():
                            try:
                                current_mtime = os.path.getmtime(filepath)
                                if current_mtime > last_mtime:
                                    changed_files.append(filepath)
                                    cls._file_mtimes[filepath] = current_mtime
                            except (OSError, IOError):
                                pass
                    
                    # 如果有文件变化，通知所有实例重新加载
                    if changed_files:
                        with cls._lock:
                            for instance in cls._instances:
                                if instance.filepath in changed_files and instance.watch_changes:
                                    try:
                                        instance.reload()
                                    except Exception as e:
                                        print(f"配置重新加载失败: {e}")
                    
                    # 间隔检查
                    time.sleep(2)
            except:
                cls._hot_reload_enabled = False
                
        # 创建并启动线程
        cls._hot_reload_thread = threading.Thread(
            target=_monitor_config_files,
            name="ConfigHotReload",
            daemon=True
        )
        cls._hot_reload_thread.start()

    @classmethod
    def stop_hot_reload(cls) -> None:
        """停止热加载监控"""
        cls._hot_reload_enabled = False
        # 线程设置为daemon=True，会在主程序退出时自动退出

    def __del__(self):
        """实例销毁时，从实例列表中移除"""
        try:
            with ConfigLoader._lock:
                if self in ConfigLoader._instances:
                    ConfigLoader._instances.remove(self)
        except:
            pass


# 创建默认配置加载器实例
default_config_loader = ConfigLoader()


# 使用LRU缓存优化频繁获取的数据库配置
@lru_cache(maxsize=32)
def get_database_config(db_type: str, config_loader: Optional[ConfigLoader] = None) -> Dict[str, Any]:
    """
    从配置加载器获取指定数据库类型的配置

    :param db_type: 数据库类型名称，如'mysql', 'postgresql', 'mongodb', 'redis'等
    :param config_loader: 配置加载器实例，默认使用全局配置加载器
    :return: 数据库配置字典
    """
    loader = config_loader or default_config_loader
    config = {}

    # 首先检查该数据库类型是否存在于配置中
    if not loader.get(db_type):
        raise KeyError(f"数据库类型 '{db_type}' 在当前环境 '{loader.environment}' 的配置中不存在")

    # 获取基础连接参数
    host = loader.get(f'{db_type}.host')
    if host:
        config['host'] = host

    port = loader.get(f'{db_type}.port')
    if port:
        config['port'] = port

    username = loader.get(f'{db_type}.username')
    if username:
        config['username'] = username

    password = loader.get(f'{db_type}.password')
    if password:
        config['password'] = password

    database = loader.get(f'{db_type}.database')
    if database:
        config['database'] = database
        
    # 获取其他所有特定配置参数
    for key, value in loader.get(db_type, {}).items():
        if key not in ('host', 'port', 'username', 'password', 'database'):
            config[key] = value

    return config

@lru_cache(maxsize=32)
def get_model_config(model_type: str, config_loader: Optional[ConfigLoader] = None) -> Dict[str, Any]:
    """
    从配置加载器获取指定模型类型的配置

    :param model_type: 模型类型名称，如'llm', 'embedding', 'reranker'等
    :param config_loader: 配置加载器实例，默认使用全局配置加载器
    :return: 模型配置字典
    """
    loader = config_loader or default_config_loader
    config = {}

    # 首先检查该模型类型是否存在于配置中
    if not loader.get(model_type):
        raise KeyError(f"模型类型 '{model_type}' 在当前环境 '{loader.environment}' 的配置中不存在")

    # 获取基础配置参数
    base_url = loader.get(f'{model_type}.base_url')
    if base_url:
        config['base_url'] = base_url

    model_id = loader.get(f'{model_type}.model_id')
    if model_id:
        config['model_id'] = model_id

    key = loader.get(f'{model_type}.key')
    if key:
        config['key'] = key

    # 获取其他所有特定配置参数
    for key, value in loader.get(model_type, {}).items():
        if key not in ('base_url', 'model_id', 'key'):
            config[key] = value

    return config

if __name__ == "__main__":
    # 测试配置加载功能
    
    # 1. 基本功能测试
    config_loader = ConfigLoader(watch_changes=True)
    print(f"环境: {config_loader.environment}")
    
    # 2. 打印所有数据库配置
    mongodb_config = get_database_config('redis', config_loader)
    print(f"MongoDB配置: {json.dumps(mongodb_config, indent=2)}")

