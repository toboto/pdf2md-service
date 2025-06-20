#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务
用于从阿里云MNS队列接收消息，处理PDF文件并上传到OSS
"""

import json
import sys 
import os
import yaml
import logging
import requests
import oss2
from mns.account import Account
from mns.queue import *
from mns.topic import *
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
from aliyun.log import LogClient, LogItem, PutLogsRequest
from aliyun.log.logexception import LogException
import time
import psutil
import argparse

# 创建logs目录
os.makedirs('logs', exist_ok=True)

# 配置日志
logger = logging.getLogger('pdf_service')
logger.setLevel(logging.INFO)

# 创建处理器
file_handler = logging.FileHandler(filename='logs/pdf_service.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)s] [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)

class PDFProcessService:
    """
    PDF处理服务类
    处理从MNS接收的消息，将PDF转换为Markdown并上传到OSS
    """
    def __init__(self, config_path, wait_seconds=30, max_runtime=3600*6, log_heartbeat_period=300):
        """
        初始化服务
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # 初始化阿里云日志服务
        self.cloud_log_enabled = self.config.get('sls', {}).get('enabled', False)
        self.last_heartbeat_time = 0  # 记录上次心跳时间
        if self.cloud_log_enabled:
            try:
                self.log_client = LogClient(
                    endpoint=self.config['sls']['endpoint'],
                    accessKeyId=self.config['sls']['access_id'],
                    accessKey=self.config['sls']['access_key']
                )
                self.log_project = self.config['sls']['project']
                self.log_store = self.config['sls']['logstore']
                self.log_topic = self.config['sls']['topic']
                self.log_source = self.config['sls']['source']
                logger.info("阿里云日志服务初始化完成")
            except Exception as e:
                logger.error(f"阿里云日志服务初始化失败: {e}")
        else:
            self.cloud_log_enabled = False
            
        # 初始化MNS客户端
        self.mns_account = Account(
            self.config['mns']['endpoint'],
            self.config['mns']['access_id'],
            self.config['mns']['access_key']
        )
        self.queue = self.mns_account.get_queue(self.config['mns']['queue_name'])
        
        # 初始化主题服务
        if 'topic' in self.config['mns']:
            self.topic = self.mns_account.get_topic(self.config['mns']['topic']['topic_name'])
            logger.info(f"已初始化主题服务: {self.config['mns']['topic']['topic_name']}")
        
        # 初始化OSS客户端
        self.oss_auth = oss2.Auth(
            self.config['oss']['access_id'],
            self.config['oss']['access_key']
        )
        self.bucket = oss2.Bucket(
            self.oss_auth,
            self.config['oss']['endpoint'],
            self.config['oss']['bucket_name']
        )
        
        # 创建临时目录
        for dir_path in self.config['temp'].values():
            os.makedirs(dir_path, exist_ok=True)

        # 初始化服务时间
        self.start_time = time.time()
        self.wait_seconds = wait_seconds
        self.max_runtime = max_runtime
        self.log_heartbeat_period = log_heartbeat_period

    def log_remotely(self, level, message, extra_fields=None):
        """
        发送日志到阿里云日志服务
        Args:
            level: 日志级别
            message: 日志消息
            extra_fields: 额外的字段信息（字典格式）
        """
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            if "exc_info" in extra_fields:
                logger.error(message, exc_info=extra_fields["exc_info"])
            else:
                logger.error(message)
            
        if not self.cloud_log_enabled:
            return
            
        try:
            log_item = LogItem()
            log_item.push_back('level', level)
            log_item.push_back('message', message)
            log_item.push_back('timestamp', str(int(time.time())))
            
            # 添加额外字段
            if extra_fields:
                for key, value in extra_fields.items():
                    log_item.push_back(key, str(value))
            
            request = PutLogsRequest(
                project=self.log_project,
                logstore=self.log_store,
                topic=self.log_topic,
                source=self.log_source,
                logitems=[log_item]
            )
            
            self.log_client.put_logs(request)
        except LogException as e:
            logger.error(f"发送阿里云日志失败: {e}")
        except Exception as e:
            logger.error(f"发送阿里云日志时发生未知错误: {e}")

    def start(self):
        """
        启动服务，开始监听消息队列
        """
        self.log_remotely("INFO", "PDF处理服务已启动")
        
        while time.time() - self.start_time < self.max_runtime:
            try:
                # 检查心跳
                self.log_heartbeat()
                
                # 接收消息
                message = self.queue.receive_message(wait_seconds=self.wait_seconds)
                if message.dequeue_count >= 3:
                    self.log_remotely("INFO", f"消息 {message.message_id} 已重试3次，跳过处理")
                    self.queue.delete_message(message.receipt_handle)
                    continue
                
                # 处理消息
                self.process_message(message)
                
                # 删除已处理的消息
                self.log_remotely("INFO", f"删除已处理的消息 {message.message_id}")
                self.queue.delete_message(message.receipt_handle)
                
            except MNSExceptionBase as e:
                if e.type == "MessageNotExist":
                    continue
                self.log_remotely("ERROR", f"接收消息失败: {e}", {"exception_type": type(e).__name__, "exc_info": True})
            except Exception as e:
                self.log_remotely("ERROR", f"处理消息时发生错误: {e}", {"exception_type": type(e).__name__, "exc_info": True})

        self.log_remotely("INFO", f"PDF处理服务已运行 {int(time.time() - self.start_time)} 秒，即将关闭")

    def process_message(self, message):
        """
        处理单条消息
        Args:
            message: MNS消息对象
        """
        try:
            # 解析消息内容
            content = json.loads(message.message_body)
            article_id = content['article_id']
            tag = content['tag']
            pdf_url = content['pdf_url']
            markdown_oss_file = content['markdown_file']
            images_oss_path = content['images_path']
            json_oss_path = content['json_path']
            
            self.log_remotely("INFO", f"开始处理文章 {article_id}", {
                "article_id": article_id,
                "tag": tag,
                "pdf_url": pdf_url
            })
            
            # 下载PDF文件
            pdf_path = os.path.join(self.config['temp']['pdf_dir'], f'{article_id}.pdf')
            self.download_file(pdf_url, pdf_path)
            
            # 处理PDF文件
            result = self.process_pdf(
                pdf_path,
                article_id,
                self.config['temp']['image_dir']+f'/{article_id}/',
                self.config['temp']['markdown_dir']
            )

            # 上传处理结果到OSS
            self.upload_results(
                article_id,
                result,
                markdown_oss_file,
                images_oss_path,
                json_oss_path
            )
            
            # 发送主题消息，使用与接收到的消息相同的格式
            topic_message = {
                'article_id': article_id,
                'tag': tag,
                'pdf_url': pdf_url,
                'markdown_file': markdown_oss_file,
                'images_path': images_oss_path,
                'json_path': json_oss_path
            }
            self.send_topic_message(topic_message)
            
            self.log_remotely("INFO", f"文章 {article_id} 处理完成", {
                "article_id": article_id,
                "status": "success"
            })
            
        except Exception as e:
            self.log_remotely("ERROR", f"处理消息失败: {e}", {
                "article_id": article_id if 'article_id' in locals() else "unknown",
                "exception_type": type(e).__name__,
                "exc_info": True
            })
            raise

    def process_pdf(self, pdf_path, article_id, image_dir, markdown_dir):
        """
        处理PDF文件
        Args:
            pdf_path: PDF文件路径
            article_id: 文章ID
            image_dir: 图片输出目录
            markdown_dir: Markdown输出目录
        Returns:
            处理结果字典
        """
        try:
            self.log_remotely("INFO", f"开始处理PDF文件, 文章ID: {article_id}, 文件路径: {pdf_path}", {
                "article_id": article_id,
                "pdf_path": pdf_path
            })
            
            # 读取PDF文件
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
                
            # 创建数据集实例
            ds = PymuDocDataset(pdf_bytes)
            
            # 配置输出writer
            image_writer = FileBasedDataWriter(image_dir)
            md_writer = FileBasedDataWriter(markdown_dir)
            
            # 处理PDF - 添加异常处理
            self.log_remotely("INFO", f"分析PDF文件", {"article_id": article_id})
            try:
                if ds.classify() == SupportedPdfParseMethod.OCR:
                    infer_result = ds.apply(doc_analyze, ocr=True)
                    pipe_result = infer_result.pipe_ocr_mode(image_writer)
                else:
                    infer_result = ds.apply(doc_analyze, ocr=False)
                    pipe_result = infer_result.pipe_txt_mode(image_writer)
            except KeyError as e:
                # 当遇到Length1等字体相关错误时，强制使用OCR模式
                if 'Length1' in str(e) or 'fontfile' in str(e):
                    self.log_remotely("WARNING", f"PDF字体解析失败，强制使用OCR模式处理, 错误: {e}", {
                        "article_id": article_id,
                        "error_type": "font_parse_error",
                        "fallback_mode": "ocr"
                    })
                    infer_result = ds.apply(doc_analyze, ocr=True)
                    pipe_result = infer_result.pipe_ocr_mode(image_writer)
                else:
                    # 其他KeyError继续抛出
                    raise
            except Exception as e:
                # 其他异常也尝试使用OCR模式
                self.log_remotely("WARNING", f"PDF解析异常，尝试使用OCR模式处理, 错误: {e}", {
                    "article_id": article_id,
                    "error_type": "parse_error",
                    "fallback_mode": "ocr"
                })
                try:
                    infer_result = ds.apply(doc_analyze, ocr=True)
                    pipe_result = infer_result.pipe_ocr_mode(image_writer)
                except Exception as ocr_error:
                    # OCR模式也失败，记录错误并抛出
                    self.log_remotely("ERROR", f"OCR模式处理也失败: {ocr_error}", {
                        "article_id": article_id,
                        "original_error": str(e),
                        "ocr_error": str(ocr_error)
                    })
                    raise ocr_error
                
            # 获取处理结果
            markdown_path = os.path.join(markdown_dir, f'{article_id}.md')
            json_middle_path = os.path.join(markdown_dir, f'{article_id}_middle.json')
            json_content_list_path = os.path.join(markdown_dir, f'{article_id}_content_list.json')
            
            # 导出结果文件
            pipe_result.dump_md(md_writer, f'{article_id}.md', image_dir)
            pipe_result.dump_middle_json(md_writer, f'{article_id}_middle.json')
            pipe_result.dump_content_list(md_writer, f"{article_id}_content_list.json", image_dir)
            
            self.log_remotely("INFO", f"PDF文件处理完成, 文章ID: {article_id}, 文章路径: {markdown_path}", {
                "article_id": article_id,
                "markdown_path": markdown_path
            })
            
            return {
                'markdown_path': markdown_path,
                'json_middle_path': json_middle_path,
                'json_content_list_path': json_content_list_path,
                'image_dir': image_dir
            }
        except Exception as e:
            self.log_remotely("ERROR", f"处理PDF文件失败: {e}", {
                "article_id": article_id,
                "exception_type": type(e).__name__,
                "exc_info": True
            })
            raise

    def download_file(self, url, local_path):
        """
        下载文件
        Args:
            url: 文件URL
            local_path: 本地保存路径
        """
        try:
            self.log_remotely("INFO", f"开始下载文件, 文件URL: {url}, 本地路径: {local_path}", {
                "url": url,
                "local_path": local_path
            })
            
            response = requests.get(url)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            self.log_remotely("INFO", f"文件下载完成, 文件路径: {local_path}", {
                "local_path": local_path
            })
        except Exception as e:
            self.log_remotely("ERROR", f"下载文件失败: {e}", {
                "url": url,
                "exception_type": type(e).__name__,
                "exc_info": True
            })
            raise

    def upload_results(self, article_id, result, markdown_oss_file, images_oss_path, json_oss_path):
        """
        上传处理结果到OSS
        Args:
            article_id: 文章ID
            result: 处理结果字典
            markdown_oss_path: Markdown文件的OSS路径
            images_oss_path: 图片文件的OSS路径
            json_oss_path: JSON文件的OSS路径
        """
        try:
            self.log_remotely("INFO", f"开始上传处理结果到OSS, 文章ID: {article_id}", {
                "article_id": article_id,
                "markdown_oss_file": markdown_oss_file,
                "images_oss_path": images_oss_path
            })
            
            # 上传Markdown文件
            self.bucket.put_object_from_file(
                markdown_oss_file,
                result['markdown_path']
            )
            
            # 上传JSON文件
            # 上传中间JSON文件
            json_middle_name = os.path.basename(result['json_middle_path'])
            self.bucket.put_object_from_file(
                os.path.join(json_oss_path, json_middle_name),
                result['json_middle_path']
            )
            
            # 上传内容列表JSON文件
            json_content_list_name = os.path.basename(result['json_content_list_path']) 
            self.bucket.put_object_from_file(
                os.path.join(json_oss_path, json_content_list_name),
                result['json_content_list_path']
            )
            
            # 上传图片文件(如果存在图片目录)
            if os.path.exists(result['image_dir']):
                for image_name in os.listdir(result['image_dir']):
                    if image_name.endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(result['image_dir'], image_name)
                        oss_image_path = f'{images_oss_path}/{image_name}'
                        self.bucket.put_object_from_file(
                            oss_image_path,
                            image_path
                        )
                        
            self.log_remotely("INFO", f"处理结果上传完成, 文章ID: {article_id}", {
                "article_id": article_id,
                "status": "success"
            })
        except Exception as e:
            self.log_remotely("ERROR", f"上传处理结果失败: {e}", {
                "article_id": article_id,
                "exception_type": type(e).__name__,
                "exc_info": True
            })
            raise

    def send_topic_message(self, message_content):
        """
        向主题发送消息
        Args:
            message_content: 消息内容（JSON格式的字典）
        """
        try:
            # 检查主题是否已初始化
            if not hasattr(self, 'topic'):
                self.log_remotely("WARNING", "主题服务未初始化，无法发送消息")
                return None
            
            article_id = message_content.get('article_id', 'unknown')
            self.log_remotely("INFO", f"发送主题消息，文章ID: {article_id}", {
                "article_id": article_id
            })
            
            # 将消息内容转换为JSON字符串
            message_body = json.dumps(message_content)
            
            # 创建Base64编码的主题消息
            msg = Base64TopicMessage(message_body)
            
            # 设置消息标签
            message_tag = self.config['mns']['topic']['tag'] if message_content['tag'] is None else message_content['tag']
            msg.message_tag = message_tag
            
            # 发送消息
            res = self.topic.publish_message(msg)
            
            self.log_remotely("INFO", f"主题消息发送成功，消息ID: {res.message_id}", {
                "article_id": article_id,
                "message_id": res.message_id
            })
            
            return res.message_id
            
        except Exception as e:
            self.log_remotely("ERROR", f"发送主题消息失败: {e}", {
                "article_id": message_content.get('article_id', 'unknown'),
                "exception_type": type(e).__name__,
                "exc_info": True
            })
            raise

    def log_heartbeat(self):
        """
        记录服务心跳日志
        如果距离上次心跳超过5分钟，则输出心跳日志
        """
        current_time = time.time()
        if current_time - self.last_heartbeat_time >= self.log_heartbeat_period:  # 默认5分钟 = 300秒
            self.log_remotely("INFO", "PDF处理服务心跳检测", {
                "uptime": current_time - self.start_time,
                "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # 转换为MB
            })
            self.last_heartbeat_time = current_time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PDF处理服务')
    parser.add_argument('--config', '-c', type=str, default='config/config.yaml', help='配置文件路径')
    parser.add_argument('--wait-seconds', '-w', type=int, default=30, help='消息队列等待时长(秒)')
    parser.add_argument('--max-runtime', '-m', type=int, default=3600*6, help='最大运行时长(秒)')
    parser.add_argument('--log-heartbeat-period', '-l', type=int, default=300, help='心跳检测周期(秒)')
    args = parser.parse_args()

    logger.info("开始启动PDF处理服务")
    service = PDFProcessService(args.config, args.wait_seconds, args.max_runtime, args.log_heartbeat_period)
    service.start() 