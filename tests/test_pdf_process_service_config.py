#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务初始化测试脚本
测试PDFProcessService类的初始化和notice_manager方法
"""

import sys
import os
import json
import yaml
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_process_service import PDFProcessService


class TestPDFProcessServiceInit(unittest.TestCase):
    """
    PDF处理服务初始化测试类
    """
    
    def setUp(self):
        """
        测试前的准备工作
        """
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置文件
        self.config_path = os.path.join(self.temp_dir, 'test_config.yaml')
        self.create_test_config()
        
        # 创建必要的目录
        os.makedirs('logs', exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'temp', 'pdf_dir'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'temp', 'image_dir'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'temp', 'markdown_dir'), exist_ok=True)
    
    def tearDown(self):
        """
        测试后的清理工作
        """
        # 删除临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_config(self):
        """
        创建测试配置文件
        """
        config = {
            'sls': {
                'enabled': False,
                'endpoint': 'https://cn-hangzhou.log.aliyuncs.com',
                'access_id': 'test_access_id',
                'access_key': 'test_access_key',
                'project': 'test_project',
                'logstore': 'test_logstore',
                'topic': 'test_topic',
                'source': 'test_source'
            },
            'mns': {
                'endpoint': 'https://123456789.mns.cn-hangzhou.aliyuncs.com',
                'access_id': 'test_access_id',
                'access_key': 'test_access_key',
                'queue_name': 'test_queue',
                'topic': {
                    'topic_name': 'test_topic',
                    'tag': 'test_tag'
                }
            },
            'oss': {
                'endpoint': 'https://oss-cn-hangzhou.aliyuncs.com',
                'access_id': 'test_access_id',
                'access_key': 'test_access_key',
                'bucket_name': 'test_bucket'
            },
            'temp': {
                'pdf_dir': os.path.join(self.temp_dir, 'temp', 'pdf_dir'),
                'image_dir': os.path.join(self.temp_dir, 'temp', 'image_dir'),
                'markdown_dir': os.path.join(self.temp_dir, 'temp', 'markdown_dir')
            },
            'notice': {
                'corp_wechat_hook_url': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key'
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    @patch('pdf_process_service.Account')
    @patch('pdf_process_service.oss2.Auth')
    @patch('pdf_process_service.oss2.Bucket')
    @patch('pdf_process_service.LogClient')
    def test_pdf_process_service_init(self, mock_log_client, mock_bucket, mock_auth, mock_account):
        """
        测试PDFProcessService类初始化
        """
        # 模拟MNS Account
        mock_account_instance = Mock()
        mock_account.return_value = mock_account_instance
        
        # 模拟Queue
        mock_queue = Mock()
        mock_account_instance.get_queue.return_value = mock_queue
        
        # 模拟Topic
        mock_topic = Mock()
        mock_account_instance.get_topic.return_value = mock_topic
        
        # 模拟OSS Auth
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        
        # 模拟OSS Bucket
        mock_bucket_instance = Mock()
        mock_bucket.return_value = mock_bucket_instance
        
        # 模拟LogClient
        mock_log_client_instance = Mock()
        mock_log_client.return_value = mock_log_client_instance
        
        try:
            # 初始化服务
            service = PDFProcessService(self.config_path)
            
            # 验证基本属性
            self.assertIsNotNone(service.config)
            self.assertEqual(service.wait_seconds, 30)
            self.assertEqual(service.max_runtime, 3600*6)
            self.assertEqual(service.log_heartbeat_period, 300)
            self.assertEqual(service.notice_hook_url, 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key')
            
            # 验证MNS初始化
            mock_account.assert_called_once()
            mock_account_instance.get_queue.assert_called_once_with('test_queue')
            mock_account_instance.get_topic.assert_called_once_with('test_topic')
            
            # 验证OSS初始化
            mock_auth.assert_called_once()
            mock_bucket.assert_called_once()
            
            print("✅ PDFProcessService初始化测试通过")
            
        except Exception as e:
            self.fail(f"PDFProcessService初始化失败: {e}")
    
    @patch('pdf_process_service.Account')
    @patch('pdf_process_service.oss2.Auth')
    @patch('pdf_process_service.oss2.Bucket')
    @patch('pdf_process_service.LogClient')
    @patch('pdf_process_service.requests.post')
    def test_notice_manager_with_hook_url(self, mock_post, mock_log_client, mock_bucket, mock_auth, mock_account):
        """
        测试notice_manager方法（有hook URL的情况）
        """
        # 模拟MNS Account
        mock_account_instance = Mock()
        mock_account.return_value = mock_account_instance
        
        # 模拟Queue
        mock_queue = Mock()
        mock_account_instance.get_queue.return_value = mock_queue
        
        # 模拟Topic
        mock_topic = Mock()
        mock_account_instance.get_topic.return_value = mock_topic
        
        # 模拟OSS Auth
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        
        # 模拟OSS Bucket
        mock_bucket_instance = Mock()
        mock_bucket.return_value = mock_bucket_instance
        
        # 模拟LogClient
        mock_log_client_instance = Mock()
        mock_log_client.return_value = mock_log_client_instance
        
        # 模拟requests.post
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # 创建服务实例
        service = PDFProcessService(self.config_path)
        
        # 创建模拟消息
        mock_message = Mock()
        mock_message.message_body = json.dumps({
            'article_id': 'test_article_123',
            'tag': 'test_tag',
            'pdf_url': 'https://example.com/test.pdf'
        })
        
        # 调用notice_manager方法
        service.notice_manager(mock_message)
        
        # 验证requests.post被调用
        mock_post.assert_called_once()
        
        # 验证请求参数
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key')
        
        # 验证请求体
        request_body = call_args[1]['json']
        self.assertEqual(request_body['msgtype'], 'text')
        self.assertIn('test_article_123', request_body['text']['content'])
        
        print("✅ notice_manager方法测试通过（有hook URL）")
    
    @patch('pdf_process_service.Account')
    @patch('pdf_process_service.oss2.Auth')
    @patch('pdf_process_service.oss2.Bucket')
    @patch('pdf_process_service.LogClient')
    def test_notice_manager_without_hook_url(self, mock_log_client, mock_bucket, mock_auth, mock_account):
        """
        测试notice_manager方法（没有hook URL的情况）
        """
        # 模拟MNS Account
        mock_account_instance = Mock()
        mock_account.return_value = mock_account_instance
        
        # 模拟Queue
        mock_queue = Mock()
        mock_account_instance.get_queue.return_value = mock_queue
        
        # 模拟OSS Auth
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        
        # 模拟OSS Bucket
        mock_bucket_instance = Mock()
        mock_bucket.return_value = mock_bucket_instance
        
        # 模拟LogClient
        mock_log_client_instance = Mock()
        mock_log_client.return_value = mock_log_client_instance
        
        # 创建没有notice配置的配置文件
        config_without_notice = {
            'sls': {'enabled': False},
            'mns': {
                'endpoint': 'https://test.mns.aliyuncs.com',
                'access_id': 'test_access_id',
                'access_key': 'test_access_key',
                'queue_name': 'test_queue'
            },
            'oss': {
                'endpoint': 'https://oss-cn-hangzhou.aliyuncs.com',
                'access_id': 'test_access_id',
                'access_key': 'test_access_key',
                'bucket_name': 'test_bucket'
            },
            'temp': {
                'pdf_dir': os.path.join(self.temp_dir, 'temp', 'pdf_dir'),
                'image_dir': os.path.join(self.temp_dir, 'temp', 'image_dir'),
                'markdown_dir': os.path.join(self.temp_dir, 'temp', 'markdown_dir')
            },
            'notice': {
                'corp_wechat_hook_url': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key'
            }
        }
        
        config_path_no_notice = os.path.join(self.temp_dir, 'config_no_notice.yaml')
        with open(config_path_no_notice, 'w', encoding='utf-8') as f:
            yaml.dump(config_without_notice, f, default_flow_style=False, allow_unicode=True)
        
        # 创建服务实例
        service = PDFProcessService(config_path_no_notice)
        
        # 创建模拟消息
        mock_message = Mock()
        mock_message.message_body = json.dumps({
            'article_id': 'test_article_456',
            'tag': 'test_tag',
            'pdf_url': 'https://example.com/test.pdf'
        })
        
        # 调用notice_manager方法（应该不会抛出异常）
        try:
            service.notice_manager(mock_message)
            print("✅ notice_manager方法测试通过（没有hook URL）")
        except Exception as e:
            self.fail(f"notice_manager方法在没有hook URL时应该正常工作，但抛出了异常: {e}")


def test_pdf_process_service_manual():
    """
    手动测试PDFProcessService的初始化和notice_manager方法
    """
    print("🚀 开始手动测试PDFProcessService...")
    
    # 创建测试实例
    test_instance = TestPDFProcessServiceInit()
    test_instance.setUp()
    
    try:
        # 测试初始化
        print("\n📋 测试1: PDFProcessService初始化")
        with patch('pdf_process_service.Account'), \
             patch('pdf_process_service.oss2.Auth'), \
             patch('pdf_process_service.oss2.Bucket'), \
             patch('pdf_process_service.LogClient'):
            test_instance.test_pdf_process_service_init()
        
        # 测试notice_manager（有hook URL）
        print("\n📋 测试2: notice_manager方法（有hook URL）")
        with patch('pdf_process_service.Account'), \
             patch('pdf_process_service.oss2.Auth'), \
             patch('pdf_process_service.oss2.Bucket'), \
             patch('pdf_process_service.LogClient'), \
             patch('pdf_process_service.requests.post'):
            test_instance.test_notice_manager_with_hook_url()
        
        # 测试notice_manager（没有hook URL）
        print("\n📋 测试3: notice_manager方法（没有hook URL）")
        with patch('pdf_process_service.Account'), \
             patch('pdf_process_service.oss2.Auth'), \
             patch('pdf_process_service.oss2.Bucket'), \
             patch('pdf_process_service.LogClient'):
            test_instance.test_notice_manager_without_hook_url()
        
        print("\n🎉 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        test_instance.tearDown()


if __name__ == '__main__':
    # 运行手动测试
    test_pdf_process_service_manual()
    
    # 运行单元测试
    print("\n" + "="*50)
    print("运行单元测试套件...")
    unittest.main(argv=[''], exit=False, verbosity=2) 