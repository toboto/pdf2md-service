#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务
用于从阿里云MNS队列接收消息，处理PDF文件并上传到OSS
"""

import json
import os
import yaml
import logging
import requests
import oss2
from mns.account import Account
from mns.queue import *
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFProcessService:
    """
    PDF处理服务类
    处理从MNS接收的消息，将PDF转换为Markdown并上传到OSS
    """
    
    def __init__(self, config_path):
        """
        初始化服务
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # # 初始化MNS客户端
        # self.mns_account = Account(
        #     self.config['mns']['endpoint'],
        #     self.config['mns']['access_id'],
        #     self.config['mns']['access_key']
        # )
        # self.queue = self.mns_account.get_queue(self.config['mns']['queue_name'])
        
        # # 初始化OSS客户端
        # self.oss_auth = oss2.Auth(
        #     self.config['oss']['access_id'],
        #     self.config['oss']['access_key']
        # )
        # self.bucket = oss2.Bucket(
        #     self.oss_auth,
        #     self.config['oss']['endpoint'],
        #     self.config['oss']['bucket_name']
        # )
        
        # # 创建临时目录
        # for dir_path in self.config['temp'].values():
        #     os.makedirs(dir_path, exist_ok=True)

    def start(self):
        """
        启动服务，开始监听消息队列
        """
        logger.info('PDF处理服务已启动，等待消息...')
        while True:
            try:
                # 接收消息
                message = self.queue.receive_message(wait_seconds=30)
                
                # 处理消息
                self.process_message(message)
                
                # 删除已处理的消息
                self.queue.delete_message(message.receipt_handle)
                
            except MNSExceptionBase as e:
                if e.type == "MessageNotExist":
                    continue
                logger.error(f"接收消息失败: {e}")
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

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
            pdf_url = content['pdf_url']
            markdown_oss_path = content['markdown_path']
            images_oss_path = content['images_path']
            json_oss_path = content['json_path']
            
            logger.info(f'开始处理文章 {article_id}')
            
            # 下载PDF文件
            pdf_path = os.path.join(self.config['temp']['pdf_dir'], f'{article_id}.pdf')
            self.download_file(pdf_url, pdf_path)
            
            # 处理PDF文件
            result = self.process_pdf(
                pdf_path,
                article_id,
                self.config['temp']['image_dir'],
                self.config['temp']['markdown_dir']
            )
            
            # 上传处理结果到OSS
            self.upload_results(
                article_id,
                result,
                markdown_oss_path,
                images_oss_path,
                json_oss_path
            )
            
            logger.info(f'文章 {article_id} 处理完成')
            
        except Exception as e:
            logger.error(f'处理消息失败: {e}', exc_info=True)
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
        # 读取PDF文件
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # 创建数据集实例
        ds = PymuDocDataset(pdf_bytes)
        
        # 配置输出writer
        image_writer = FileBasedDataWriter(image_dir)
        md_writer = FileBasedDataWriter(markdown_dir)
        
        # 处理PDF
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
            
        # 获取处理结果
        markdown_path = os.path.join(markdown_dir, f'{article_id}.md')
        json_path = os.path.join(markdown_dir, f'{article_id}_middle.json')
        
        # 导出结果文件
        pipe_result.dump_md(md_writer, f'{article_id}.md', 'images')
        pipe_result.dump_middle_json(md_writer, f'{article_id}_middle.json')
        
        return {
            'markdown_path': markdown_path,
            'json_path': json_path,
            'image_dir': image_dir
        }

    def download_file(self, url, local_path):
        """
        下载文件
        Args:
            url: 文件URL
            local_path: 本地保存路径
        """
        response = requests.get(url)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)

    def upload_results(self, article_id, result, markdown_oss_path, images_oss_path, json_oss_path):
        """
        上传处理结果到OSS
        Args:
            article_id: 文章ID
            result: 处理结果字典
            markdown_oss_path: Markdown文件的OSS路径
            images_oss_path: 图片文件的OSS路径
            json_oss_path: JSON文件的OSS路径
        """
        # 上传Markdown文件
        self.bucket.put_object_from_file(
            markdown_oss_path,
            result['markdown_path']
        )
        
        # 上传JSON文件
        self.bucket.put_object_from_file(
            json_oss_path,
            result['json_path']
        )
        
        # 上传图片文件
        for image_name in os.listdir(result['image_dir']):
            if image_name.endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(result['image_dir'], image_name)
                oss_image_path = f'{images_oss_path}/{image_name}'
                self.bucket.put_object_from_file(
                    oss_image_path,
                    image_path
                )

if __name__ == '__main__':
    service = PDFProcessService('config/config.yaml')
    service.start() 