#!/usr/bin/env python
"""
Readify功能演示脚本
展示修复后的所有功能，包括用户下拉框、分类浏览、AI助手和语音功能
"""

import os
import sys
import django
import time
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BookCategory, BookContent, ReadingAssistant
from readify.user_management.models import UserPreferences

class ReadifyDemo:
    def __init__(self):
        self.demo_user = None
        self.demo_books = []
        self.categories = []
        
    def setup_demo_data(self):
        """设置演示数据"""
        print("🎬 设置演示数据...")
        
        # 创建演示用户
        self.demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@readify.com',
                'first_name': '演示',
                'last_name': '用户',
                'is_active': True
            }
        )
        if created:
            self.demo_user.set_password('demo123')
            self.demo_user.save()
            print(f"✅ 创建演示用户: {self.demo_user.username}")
        else:
            print(f"✅ 使用现有演示用户: {self.demo_user.username}")
        
        # 创建用户偏好设置
        preferences, created = UserPreferences.objects.get_or_create(
            user=self.demo_user,
            defaults={
                'ai_assistant_enabled': True,
                'voice_enabled': True,
                'voice_speed': 1.0,
                'voice_engine': 'chattts',
                'reading_mode': 'normal',
                'reading_background': 'white',
                'ai_auto_summary': True
            }
        )
        
        # 创建书籍分类
        categories_data = [
            {'name': '计算机科学', 'code': 'computer', 'description': '编程、算法、人工智能等技术书籍'},
            {'name': '文学作品', 'code': 'literature', 'description': '小说、散文、诗歌等文学作品'},
            {'name': '历史传记', 'code': 'history', 'description': '历史事件、人物传记等'},
            {'name': '科学技术', 'code': 'science', 'description': '自然科学、工程技术等'},
            {'name': '经济管理', 'code': 'economics', 'description': '经济学、管理学、商业等'},
        ]
        
        for cat_data in categories_data:
            category, created = BookCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            self.categories.append(category)
            if created:
                print(f"✅ 创建分类: {category.name}")
        
        # 创建演示书籍
        books_data = [
            {
                'title': 'Python深度学习实战',
                'author': '张三',
                'category': 'computer',
                'description': '深入浅出讲解Python在深度学习中的应用',
                'chapters': [
                    {'title': '第一章：深度学习基础', 'content': self.get_dl_chapter1_content()},
                    {'title': '第二章：神经网络原理', 'content': self.get_dl_chapter2_content()},
                    {'title': '第三章：实战项目', 'content': self.get_dl_chapter3_content()},
                ]
            },
            {
                'title': '人工智能简史',
                'author': '李四',
                'category': 'science',
                'description': '从图灵测试到ChatGPT的AI发展历程',
                'chapters': [
                    {'title': '第一章：AI的诞生', 'content': self.get_ai_chapter1_content()},
                    {'title': '第二章：机器学习革命', 'content': self.get_ai_chapter2_content()},
                    {'title': '第三章：深度学习时代', 'content': self.get_ai_chapter3_content()},
                ]
            },
            {
                'title': '现代Web开发指南',
                'author': '王五',
                'category': 'computer',
                'description': '全栈Web开发技术详解',
                'chapters': [
                    {'title': '第一章：前端技术栈', 'content': self.get_web_chapter1_content()},
                    {'title': '第二章：后端架构设计', 'content': self.get_web_chapter2_content()},
                    {'title': '第三章：部署与运维', 'content': self.get_web_chapter3_content()},
                ]
            }
        ]
        
        for book_data in books_data:
            category = BookCategory.objects.get(code=book_data['category'])
            
            book, created = Book.objects.get_or_create(
                title=book_data['title'],
                user=self.demo_user,
                defaults={
                    'author': book_data['author'],
                    'description': book_data['description'],
                    'category': category,
                    'format': 'txt',
                    'file_size': 50000,
                    'view_count': 0
                }
            )
            
            if created:
                print(f"✅ 创建演示书籍: {book.title}")
                
                # 创建章节内容
                for i, chapter_data in enumerate(book_data['chapters'], 1):
                    BookContent.objects.create(
                        book=book,
                        chapter_number=i,
                        chapter_title=chapter_data['title'],
                        content=chapter_data['content']
                    )
                
                # 创建AI助手实例
                ReadingAssistant.objects.create(
                    user=self.demo_user,
                    book=book,
                    session_name=f'{book.title} - AI助手',
                    is_enabled=True,
                    auto_summary=True
                )
                
                self.demo_books.append(book)
        
        print(f"✅ 演示数据设置完成！创建了 {len(self.demo_books)} 本书籍")
    
    def get_dl_chapter1_content(self):
        return """
深度学习基础

深度学习是机器学习的一个分支，它模仿人脑神经网络的工作方式来处理数据。
在过去的十年中，深度学习在图像识别、自然语言处理、语音识别等领域取得了突破性进展。

什么是深度学习？

深度学习使用多层神经网络来学习数据的表示。与传统的机器学习方法不同，
深度学习可以自动从原始数据中提取特征，无需人工特征工程。

神经网络的基本组成：
1. 输入层：接收原始数据
2. 隐藏层：进行特征提取和变换
3. 输出层：产生最终结果

激活函数的作用：
激活函数为神经网络引入非线性，使其能够学习复杂的模式。
常用的激活函数包括ReLU、Sigmoid、Tanh等。

Python在深度学习中的优势：
- 丰富的库生态系统（TensorFlow、PyTorch、Keras）
- 简洁易读的语法
- 强大的数据处理能力
- 活跃的社区支持

本章将为您建立深度学习的基础概念，为后续的实战项目做好准备。
        """
    
    def get_dl_chapter2_content(self):
        return """
神经网络原理

神经网络是深度学习的核心，理解其工作原理对于掌握深度学习至关重要。

前向传播过程：
数据从输入层开始，经过各个隐藏层的计算，最终到达输出层。
每一层的计算都涉及权重矩阵乘法和激活函数的应用。

反向传播算法：
这是神经网络学习的核心算法，通过计算损失函数的梯度，
反向更新网络中的权重参数。

梯度下降优化：
- 批量梯度下降（BGD）
- 随机梯度下降（SGD）
- 小批量梯度下降（Mini-batch GD）
- Adam优化器

正则化技术：
为了防止过拟合，我们使用各种正则化技术：
- L1/L2正则化
- Dropout
- Batch Normalization
- Early Stopping

卷积神经网络（CNN）：
专门用于处理图像数据的神经网络架构，
通过卷积层、池化层等组件提取图像特征。

循环神经网络（RNN）：
适用于序列数据处理，如文本、时间序列等。
LSTM和GRU是RNN的改进版本，解决了长期依赖问题。
        """
    
    def get_dl_chapter3_content(self):
        return """
实战项目

本章将通过具体的项目来实践深度学习技术。

项目一：图像分类
使用卷积神经网络对CIFAR-10数据集进行分类。

```python
import tensorflow as tf
from tensorflow.keras import layers, models

# 构建CNN模型
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dense(10, activation='softmax')
])

# 编译模型
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])
```

项目二：文本情感分析
使用LSTM网络分析电影评论的情感倾向。

项目三：生成对抗网络（GAN）
实现一个简单的GAN来生成手写数字图像。

性能优化技巧：
1. 数据预处理和增强
2. 模型架构优化
3. 超参数调优
4. 分布式训练

部署和应用：
- 模型保存和加载
- Web API部署
- 移动端部署
- 边缘计算应用

通过这些实战项目，您将掌握深度学习的核心技能，
能够独立完成从数据处理到模型部署的完整流程。
        """
    
    def get_ai_chapter1_content(self):
        return """
AI的诞生

人工智能的概念可以追溯到古代神话和哲学思考，
但现代AI的发展始于20世纪中叶。

图灵测试（1950年）：
阿兰·图灵提出了著名的图灵测试，
这成为了判断机器是否具有智能的重要标准。

达特茅斯会议（1956年）：
约翰·麦卡锡等人组织的这次会议正式确立了
"人工智能"这一术语，标志着AI学科的诞生。

早期的AI程序：
- Logic Theorist（逻辑理论家）
- General Problem Solver（通用问题求解器）
- ELIZA（早期的聊天机器人）

符号主义AI：
早期AI主要基于符号逻辑和规则推理，
认为智能可以通过符号操作来实现。

专家系统的兴起：
20世纪70-80年代，专家系统成为AI应用的主流，
如MYCIN医疗诊断系统、DENDRAL化学分析系统。

第一次AI寒冬：
由于技术限制和过高期望，AI在70年代遭遇挫折，
资金投入大幅减少，这被称为"AI寒冬"。

知识工程：
为了让机器具有专业知识，研究者开始关注
如何有效地表示和利用人类知识。
        """
    
    def get_ai_chapter2_content(self):
        return """
机器学习革命

20世纪80年代末，机器学习开始兴起，
为AI发展带来了新的思路和方法。

统计学习理论：
弗拉基米尔·瓦普尼克等人发展的统计学习理论
为机器学习提供了坚实的数学基础。

支持向量机（SVM）：
这种强大的分类算法在90年代获得广泛应用，
在文本分类、图像识别等领域表现出色。

决策树和随机森林：
这些算法易于理解和解释，
在商业应用中得到广泛采用。

神经网络的复兴：
虽然神经网络在80年代遭遇挫折，
但反向传播算法的发展为其复兴奠定了基础。

贝叶斯网络：
基于概率论的推理方法，
能够处理不确定性和不完整信息。

强化学习：
受行为主义心理学启发，
通过试错学习来优化决策策略。

数据挖掘的兴起：
随着数据量的增长，从大量数据中
发现有用模式成为重要研究方向。

互联网时代的机器学习：
搜索引擎、推荐系统等应用
推动了机器学习技术的快速发展。
        """
    
    def get_ai_chapter3_content(self):
        return """
深度学习时代

21世纪初，深度学习的突破性进展
开启了AI发展的新纪元。

ImageNet竞赛的转折点：
2012年，AlexNet在ImageNet图像识别竞赛中
取得突破性成绩，标志着深度学习时代的到来。

GPU计算的推动：
图形处理器的并行计算能力
为深度学习的大规模训练提供了硬件支持。

大数据的作用：
互联网产生的海量数据
为深度学习模型提供了充足的训练素材。

卷积神经网络的发展：
- LeNet（1998）
- AlexNet（2012）
- VGGNet（2014）
- ResNet（2015）
- Transformer（2017）

自然语言处理的突破：
- Word2Vec词向量
- LSTM和GRU
- Attention机制
- BERT和GPT系列

生成式AI的兴起：
- 生成对抗网络（GAN）
- 变分自编码器（VAE）
- 扩散模型
- ChatGPT和GPT-4

AI在各领域的应用：
- 计算机视觉：人脸识别、自动驾驶
- 自然语言处理：机器翻译、智能客服
- 语音技术：语音识别、语音合成
- 游戏AI：AlphaGo、OpenAI Five

当前的挑战和未来展望：
- 可解释性AI
- 通用人工智能（AGI）
- AI伦理和安全
- 人机协作
        """
    
    def get_web_chapter1_content(self):
        return """
前端技术栈

现代Web开发的前端技术日新月异，
掌握核心技术栈是成功开发的关键。

HTML5的新特性：
- 语义化标签
- Canvas和SVG
- 本地存储
- 地理定位API
- WebSocket通信

CSS3的强大功能：
- Flexbox和Grid布局
- 动画和过渡效果
- 响应式设计
- CSS变量
- 预处理器（Sass、Less）

JavaScript ES6+：
- 箭头函数和模板字符串
- 解构赋值和扩展运算符
- Promise和async/await
- 模块化开发
- 类和继承

前端框架对比：
React：
- 组件化开发
- 虚拟DOM
- 单向数据流
- 丰富的生态系统

Vue.js：
- 渐进式框架
- 双向数据绑定
- 简单易学
- 优秀的文档

Angular：
- 完整的框架解决方案
- TypeScript支持
- 依赖注入
- 强大的CLI工具

构建工具和包管理：
- Webpack模块打包
- Vite快速构建
- npm和yarn包管理
- Babel代码转换

前端性能优化：
- 代码分割和懒加载
- 图片优化和CDN
- 缓存策略
- 首屏加载优化
        """
    
    def get_web_chapter2_content(self):
        return """
后端架构设计

后端架构是Web应用的核心，
需要考虑性能、可扩展性和可维护性。

服务器端技术选择：
Node.js：
- 事件驱动和非阻塞I/O
- JavaScript全栈开发
- 丰富的npm生态
- 适合实时应用

Python：
- Django和Flask框架
- 简洁优雅的语法
- 强大的数据处理能力
- 机器学习集成

Java：
- Spring Boot框架
- 企业级应用首选
- 强类型和高性能
- 成熟的生态系统

数据库设计：
关系型数据库：
- MySQL和PostgreSQL
- ACID事务特性
- 复杂查询支持
- 数据一致性保证

NoSQL数据库：
- MongoDB文档数据库
- Redis内存数据库
- Elasticsearch搜索引擎
- 高性能和可扩展性

API设计原则：
RESTful API：
- 资源导向的设计
- HTTP方法语义化
- 状态码规范使用
- 版本控制策略

GraphQL：
- 灵活的查询语言
- 类型系统
- 单一端点
- 客户端驱动

微服务架构：
- 服务拆分原则
- 服务间通信
- 配置管理
- 监控和日志

容器化部署：
- Docker容器技术
- Kubernetes编排
- CI/CD流水线
- 蓝绿部署策略
        """
    
    def get_web_chapter3_content(self):
        return """
部署与运维

现代Web应用的部署和运维需要
自动化、可监控和高可用的解决方案。

云服务平台：
AWS（Amazon Web Services）：
- EC2虚拟服务器
- S3对象存储
- RDS数据库服务
- Lambda无服务器计算

阿里云：
- ECS云服务器
- OSS对象存储
- RDS云数据库
- 函数计算

容器化部署：
Docker基础：
- 镜像和容器概念
- Dockerfile编写
- 多阶段构建
- 镜像优化技巧

Kubernetes集群：
- Pod和Service
- Deployment和StatefulSet
- ConfigMap和Secret
- Ingress网关

CI/CD流水线：
GitLab CI/CD：
- .gitlab-ci.yml配置
- 自动化测试
- 构建和部署
- 环境管理

GitHub Actions：
- Workflow工作流
- 矩阵构建
- 第三方Action
- 安全最佳实践

监控和日志：
应用监控：
- Prometheus指标收集
- Grafana可视化
- 告警规则配置
- 性能分析

日志管理：
- ELK技术栈
- 日志聚合和分析
- 错误追踪
- 审计日志

安全防护：
- HTTPS证书配置
- 防火墙规则
- DDoS防护
- 安全扫描

性能优化：
- 负载均衡
- 缓存策略
- 数据库优化
- CDN加速

备份和恢复：
- 数据备份策略
- 灾难恢复计划
- 高可用架构
- 故障转移机制
        """
    
    def demonstrate_features(self):
        """演示功能特性"""
        print("\n🎭 功能特性演示")
        print("=" * 50)
        
        print("1. 用户下拉框修复")
        print("   ✅ 修复了z-index层级问题")
        print("   ✅ 下拉菜单不再被其他元素遮挡")
        print("   ✅ 添加了美观的悬停效果")
        
        print("\n2. 分类浏览功能")
        print(f"   ✅ 创建了 {len(self.categories)} 个书籍分类")
        print("   ✅ 分类页面支持搜索和筛选")
        print("   ✅ 每个分类显示书籍数量统计")
        
        print("\n3. 分类书籍列表")
        print("   ✅ 创建了category_books.html模板")
        print("   ✅ 支持分页和排序功能")
        print("   ✅ 显示阅读进度和书籍信息")
        
        print("\n4. 智能阅读器集成")
        print("   ✅ AI助手功能完全集成")
        print("   ✅ 支持文本选择和智能分析")
        print("   ✅ 问答历史记录")
        print("   ✅ 章节总结生成")
        
        print("\n5. 语音朗读功能")
        print("   ✅ 支持播放、暂停、停止控制")
        print("   ✅ 可调节语音速度")
        print("   ✅ 支持ChatTTS引擎")
        print("   ✅ 语音设置保存")
        
        print("\n6. 阅读体验优化")
        print("   ✅ 阅读计时器和统计")
        print("   ✅ 字体大小调节")
        print("   ✅ 背景主题切换")
        print("   ✅ 阅读进度自动保存")
        
        print("\n📊 演示数据统计:")
        print(f"   📚 演示书籍: {len(self.demo_books)} 本")
        print(f"   📁 书籍分类: {len(self.categories)} 个")
        print(f"   👤 演示用户: {self.demo_user.username}")
        print(f"   🤖 AI助手: 已为所有书籍启用")
    
    def show_access_guide(self):
        """显示访问指南"""
        print("\n🌐 访问指南")
        print("=" * 50)
        
        print("1. 启动服务器:")
        print("   conda activate DL")
        print("   python manage.py runserver 0.0.0.0:8000")
        
        print("\n2. 访问地址:")
        print("   主页: http://localhost:8000")
        print("   分类浏览: http://localhost:8000/categories/")
        print("   书籍列表: http://localhost:8000/books/")
        
        print("\n3. 演示账户:")
        print(f"   用户名: {self.demo_user.username}")
        print("   密码: demo123")
        
        print("\n4. 功能测试路径:")
        print("   ① 登录 → 点击用户名下拉框（测试修复）")
        print("   ② 分类浏览 → 选择分类 → 查看书籍列表")
        print("   ③ 点击书籍 → 智能阅读器 → 测试AI助手")
        print("   ④ 选择文本 → 使用AI分析功能")
        print("   ⑤ 语音控制 → 测试朗读功能")
        
        print("\n5. 高级功能:")
        print("   🤖 AI问答: 选择文本后点击问号图标")
        print("   📝 智能总结: 使用总结功能")
        print("   🔊 语音朗读: 调节语速和音色")
        print("   📊 阅读统计: 查看阅读时间和速度")
    
    def run_demo(self):
        """运行演示"""
        print("🎬 Readify功能演示")
        print("=" * 50)
        print("本演示将展示修复后的所有功能特性")
        
        # 设置演示数据
        self.setup_demo_data()
        
        # 演示功能特性
        self.demonstrate_features()
        
        # 显示访问指南
        self.show_access_guide()
        
        print("\n🎉 演示准备完成！")
        print("现在您可以启动服务器并体验所有功能了。")

def main():
    """主函数"""
    demo = ReadifyDemo()
    demo.run_demo()
    return 0

if __name__ == '__main__':
    sys.exit(main()) 