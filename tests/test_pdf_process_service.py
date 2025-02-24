#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务的单元测试
主要测试process_message方法的功能
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf_process_service import PDFProcessService

class TestPDFProcessService(unittest.TestCase):
    """
    PDF处理服务测试类
    """
    
    def setUp(self):
        """
        测试前的准备工作
        """
        # 模拟配置文件内容
        self.mock_config = {
            'mns': {
                'endpoint': 'http://test.mns.com',
                'access_id': 'test_id',
                'access_key': 'test_key',
                'queue_name': 'test_queue'
            },
            'oss': {
                'endpoint': 'http://test.oss.com',
                'access_id': 'test_id',
                'access_key': 'test_key',
                'bucket_name': 'test_bucket'
            },
            'temp': {
                'pdf_dir': '/tmp/pdf',
                'image_dir': '/tmp/images',
                'markdown_dir': '/tmp/markdown'
            }
        }
        
        # 模拟配置文件内容
        self.mock_config_str = json.dumps(self.mock_config)
        
        # 模拟消息内容
        self.mock_message_body = {
            'article_id': 'test123',
            'pdf_url': 'http://test.com/test.pdf',
            'markdown_path': 'markdown/test.md',
            'images_path': 'images/test',
            'json_path': 'json/test.json'
        }
        
        # 创建测试用的临时目录
        for dir_path in self.mock_config['temp'].values():
            os.makedirs(dir_path, exist_ok=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('oss2.Auth')
    @patch('oss2.Bucket')
    @patch('mns.account.Account')
    def test_process_message_success(self, mock_mns_account, mock_bucket, mock_auth, mock_yaml_load, mock_file):
        """
        测试消息处理成功的情况
        """
        # 配置所有需要的mock
        mock_yaml_load.return_value = self.mock_config
        mock_message = Mock()
        mock_message.message_body = json.dumps(self.mock_message_body)
        mock_message.receipt_handle = 'test_receipt'
        
        # 创建服务实例
        service = PDFProcessService('fake_config.yaml')
        
        # Mock download_file方法
        service.download_file = Mock()
        
        # Mock process_pdf方法
        mock_process_result = {
            'markdown_path': '/tmp/markdown/test123.md',
            'json_path': '/tmp/markdown/test123_middle.json',
            'image_dir': '/tmp/images'
        }
        service.process_pdf = Mock(return_value=mock_process_result)
        
        # Mock upload_results方法
        service.upload_results = Mock()
        
        # 执行测试
        service.process_message(mock_message)
        
        # 验证方法调用
        service.download_file.assert_called_once_with(
            self.mock_message_body['pdf_url'],
            os.path.join(self.mock_config['temp']['pdf_dir'], 'test123.pdf')
        )
        
        service.process_pdf.assert_called_once_with(
            os.path.join(self.mock_config['temp']['pdf_dir'], 'test123.pdf'),
            'test123',
            self.mock_config['temp']['image_dir'],
            self.mock_config['temp']['markdown_dir']
        )
        
        service.upload_results.assert_called_once_with(
            'test123',
            mock_process_result,
            self.mock_message_body['markdown_path'],
            self.mock_message_body['images_path'],
            self.mock_message_body['json_path']
        )

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('oss2.Auth')
    @patch('oss2.Bucket')
    @patch('mns.account.Account')
    def test_process_message_invalid_json(self, mock_mns_account, mock_bucket, mock_auth, mock_yaml_load, mock_file):
        """
        测试消息体JSON无效的情况
        """
        mock_yaml_load.return_value = self.mock_config
        mock_message = Mock()
        mock_message.message_body = "invalid json"
        
        service = PDFProcessService('fake_config.yaml')
        
        # 验证是否抛出异常
        with self.assertRaises(json.JSONDecodeError):
            service.process_message(mock_message)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('oss2.Auth')
    @patch('oss2.Bucket')
    @patch('mns.account.Account')
    def test_process_message_missing_fields(self, mock_mns_account, mock_bucket, mock_auth, mock_yaml_load, mock_file):
        """
        测试消息体缺少必要字段的情况
        """
        mock_yaml_load.return_value = self.mock_config
        mock_message = Mock()
        # 缺少必要字段的消息体
        invalid_message_body = {
            'article_id': 'test123'
            # 缺少其他必要字段
        }
        mock_message.message_body = json.dumps(invalid_message_body)
        
        service = PDFProcessService('fake_config.yaml')
        
        # 验证是否抛出KeyError
        with self.assertRaises(KeyError):
            service.process_message(mock_message)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('oss2.Auth')
    @patch('oss2.Bucket')
    @patch('mns.account.Account')
    def test_process_message_download_failure(self, mock_mns_account, mock_bucket, mock_auth, mock_yaml_load, mock_file):
        """
        测试PDF下载失败的情况
        """
        mock_yaml_load.return_value = self.mock_config
        mock_message = Mock()
        mock_message.message_body = json.dumps(self.mock_message_body)
        
        service = PDFProcessService('fake_config.yaml')
        
        # Mock download_file方法使其抛出异常
        service.download_file = Mock(side_effect=Exception("Download failed"))
        
        # 验证是否抛出异常
        with self.assertRaises(Exception) as context:
            service.process_message(mock_message)
        
        self.assertEqual(str(context.exception), "Download failed")

    def tearDown(self):
        """
        测试后的清理工作
        """
        # 清理测试创建的临时目录
        for dir_path in self.mock_config['temp'].values():
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(dir_path)

if __name__ == '__main__':
    unittest.main() 