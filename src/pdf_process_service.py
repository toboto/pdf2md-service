#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务
用于从阿里云MNS队列接收消息，处理PDF文件并上传到OSS
"""

import subprocess
import shutil
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
import copy
from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.utils.enum_class import MakeMode

# from magic_pdf.data.dataset import PymuDocDataset
# from magic_pdf.data.data_reader_writer import FileBasedDataWriter
# from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
# from magic_pdf.config.enums import SupportedPdfParseMethod
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

        # 初始化通知配置
        self.notice_hook_url = self.config.get('notice', {}).get('corp_wechat_hook_url', '')

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
                    self.notice_manager(message)
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
    
    def notice_manager(self, message):
        """
        通知管理员
        Args:
            message: MNS消息对象
        """
        if not self.notice_hook_url:
            return
        
        content = json.loads(message.message_body)
        # 发送通知
        requests.post(self.notice_hook_url, json={
            "msgtype": "text",
            "text": {
                "content": f"全文数据{content['article_id']}多次处理失败，请检查数据有效性; 数据详情: {message}"
            }
        }, timeout=10)

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
        处理PDF文件 - 使用mineru Python API (Pipeline模式)
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
            
            # 读取PDF文件内容
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
                
            # 准备参数列表（pipeline API 需要列表输入）
            pdf_bytes_list = [pdf_bytes]
            # PDF文件名用于准备环境等
            pdf_file_name = f"{article_id}"
            
            # 1. 预处理PDF (convert_pdf_bytes_to_bytes_by_pypdfium2)
            # 默认从第0页开始解析所有页面
            start_page_id = 0
            end_page_id = None
            
            self.log_remotely("INFO", f"预处理PDF文件", {"article_id": article_id})
            new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            pdf_bytes_list[0] = new_pdf_bytes
            
            # 2. 执行Pipeline分析 (pipeline_doc_analyze)
            # 参数: pdf_bytes_list, p_lang_list, parse_method='auto', formula_enable=True, table_enable=True
            p_lang_list = ['en'] # 默认为英文，大多数文章是英文
            
            self.log_remotely("INFO", f"执行Pipeline分析", {"article_id": article_id})
            infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(
                pdf_bytes_list, 
                p_lang_list, 
                parse_method='auto', 
                formula_enable=True, 
                table_enable=True
            )
            
            # 获取第一个（也是唯一一个）结果
            idx = 0
            model_list = infer_results[idx]
            model_json = copy.deepcopy(model_list)
            images_list = all_image_lists[idx]
            pdf_doc = all_pdf_docs[idx]
            _lang = lang_list[idx]
            _ocr_enable = ocr_enabled_list[idx]
            
            # 3. 准备输出环境 (prepare_env 会创建目录，但我们已经有了传入的目录，这里主要利用 FileBasedDataWriter)
            # 注意：prepare_env 会在 output_dir 下创建 pdf_file_name 目录，我们需要适配我们的目录结构
            # 为了复用mineru逻辑，我们手动创建Writer指向我们的目标目录
            
            # image_dir 和 markdown_dir 是调用方传入的最终目录
            # 确保目录存在
            os.makedirs(image_dir, exist_ok=True)
            os.makedirs(markdown_dir, exist_ok=True)
            
            image_writer = FileBasedDataWriter(image_dir)
            md_writer = FileBasedDataWriter(markdown_dir)
            
            # 4. 转换结果为中间JSON (pipeline_result_to_middle_json)
            self.log_remotely("INFO", f"生成中间JSON结果", {"article_id": article_id})
            middle_json = pipeline_result_to_middle_json(
                model_list, 
                images_list, 
                pdf_doc, 
                image_writer, 
                _lang, 
                _ocr_enable
            )
            
            pdf_info = middle_json["pdf_info"]
            
            # 5. 生成最终输出文件 (_process_output logic from demo.py adapted)
            # 我们需要生成: Markdown, content_list.json, middle.json, model.json (可选)
            # 图片已经在 pipeline_result_to_middle_json 过程中通过 image_writer 写入了
            
            # 定义输出文件名
            md_filename = f"{article_id}.md"
            middle_json_filename = f"{article_id}_middle.json"
            content_list_filename = f"{article_id}_content_list.json"
            # model_json_filename = f"{article_id}_model.json"
            
            # 5.1 生成Markdown
            # pipeline模式使用 pipeline_union_make
            # image_dir 参数在 markdown 中引用图片时的路径前缀。
            # 如果图片和md在同一目录或相对路径，这里需要设置正确。
            # 在本服务的逻辑中，图片通常在 oss 上的 images_path，或者本地的 image_dir。
            # 这里我们传入 image_dir 的 basename，假设 Markdown 中引用图片是相对路径
            # 注意：如果最终展示需要特定路径，可能需要调整这里
            img_dir_rel = os.path.basename(image_dir.rstrip('/'))
            
            md_content_str = pipeline_union_make(pdf_info, MakeMode.MM_MD, img_dir_rel)
            md_writer.write_string(md_filename, md_content_str)
            
            # 5.2 生成 Content List JSON
            content_list = pipeline_union_make(pdf_info, MakeMode.CONTENT_LIST, img_dir_rel)
            md_writer.write_string(
                content_list_filename,
                json.dumps(content_list, ensure_ascii=False, indent=4)
            )
            
            # 5.3 生成 Middle JSON
            md_writer.write_string(
                middle_json_filename,
                json.dumps(middle_json, ensure_ascii=False, indent=4)
            )
            
            # 5.4 (可选) 生成 Model JSON
            # md_writer.write_string(
            #     model_json_filename,
            #     json.dumps(model_json, ensure_ascii=False, indent=4)
            # )
            
            # 构建结果路径返回
            markdown_path = os.path.join(markdown_dir, md_filename)
            json_middle_path = os.path.join(markdown_dir, middle_json_filename)
            json_content_list_path = os.path.join(markdown_dir, content_list_filename)
            
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