#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理服务的示例程序
用于测试PDFProcessService的process_pdf方法
"""

import argparse
import logging
from pdf_process_service import PDFProcessService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='PDF处理服务测试程序')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--article_id', default='test_article', help='文章ID')
    parser.add_argument('--image_dir', default='outputs/images', help='图片输出目录')
    parser.add_argument('--markdown_dir', default='outputs/markdown', help='Markdown输出目录')
    parser.add_argument('--config', default='config/config.yaml', help='配置文件路径')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    try:
        # 创建服务实例
        service = PDFProcessService(args.config)
        
        # 处理PDF
        result = service.process_pdf(
            args.pdf_path,
            args.article_id,
            args.image_dir,
            args.markdown_dir
        )
        
        logger.info(f'处理完成，结果：{result}')
        
    except Exception as e:
        logger.error(f'处理失败: {e}', exc_info=True)
        raise

if __name__ == '__main__':
    main() 