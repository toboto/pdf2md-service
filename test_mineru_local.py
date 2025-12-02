#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MinerU 2.6.5 解析测试脚本
用于在生产环境验证 PDF 解析功能是否正常
"""

import os
import sys
import json
import shutil
import argparse
import logging
import time

# 添加 src 目录到 Python 路径，以便导入 pdf_process_service
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from pdf_process_service import PDFProcessService
except ImportError as e:
    print(f"Import Error: {e}")
    print("请确保脚本在项目根目录下运行，或者 src 目录在 PYTHONPATH 中。")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test_mineru')

class MockPDFService(PDFProcessService):
    """
    Mock PDFService，覆盖部分依赖外部服务的方法，仅用于测试解析功能
    """
    def __init__(self):
        # 初始化时不加载完整配置，只初始化解析需要的属性
        self.config = {}
        self.cloud_log_enabled = False
        self.log_project = None
        self.log_store = None
        # Mock logger
        pass

    def log_remotely(self, level, message, extra_fields=None):
        """覆盖远程日志，只打印到控制台"""
        if level == "INFO":
            logger.info(f"{message} | {extra_fields if extra_fields else ''}")
        elif level == "WARNING":
            logger.warning(f"{message} | {extra_fields if extra_fields else ''}")
        elif level == "ERROR":
            logger.error(f"{message} | {extra_fields if extra_fields else ''}")

def main():
    parser = argparse.ArgumentParser(description='MinerU 解析测试脚本')
    parser.add_argument('pdf_path', help='输入的PDF文件路径')
    parser.add_argument('--output-dir', '-o', default='test_output', help='输出目录 (默认: test_output)')
    parser.add_argument('--article-id', '-id', default='test_article', help='模拟的文章ID')
    
    args = parser.parse_args()
    
    pdf_path = args.pdf_path
    output_base_dir = args.output_dir
    article_id = args.article_id
    
    # 检查输入文件
    if not os.path.exists(pdf_path):
        logger.error(f"PDF文件不存在: {pdf_path}")
        sys.exit(1)
        
    # 准备输出目录
    markdown_dir = os.path.join(output_base_dir, 'markdown')
    image_dir = os.path.join(output_base_dir, 'images', article_id)
    
    # 清理旧的输出目录（如果存在）
    if os.path.exists(output_base_dir):
        logger.info(f"清理输出目录: {output_base_dir}")
        shutil.rmtree(output_base_dir)
        
    os.makedirs(markdown_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    
    logger.info(f"开始测试解析 PDF: {pdf_path}")
    logger.info(f"输出目录: {output_base_dir}")
    
    start_time = time.time()
    
    try:
        # 初始化 Mock 服务
        service = MockPDFService()
        
        # 调用解析方法
        result = service.process_pdf(
            pdf_path=pdf_path,
            article_id=article_id,
            image_dir=image_dir,
            markdown_dir=markdown_dir
        )
        
        duration = time.time() - start_time
        logger.info(f"解析完成! 耗时: {duration:.2f}秒")
        logger.info(f"结果详情:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        # 验证输出文件
        if os.path.exists(result['markdown_path']):
            logger.info(f"✅ Markdown 文件已生成: {result['markdown_path']}")
        else:
            logger.error(f"❌ Markdown 文件未生成")
            
        if os.path.exists(result['json_middle_path']):
             logger.info(f"✅ Middle JSON 文件已生成: {result['json_middle_path']}")
        else:
             logger.error(f"❌ Middle JSON 文件未生成")

    except Exception as e:
        logger.error(f"解析失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

