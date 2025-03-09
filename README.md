# PDF2MD Service

A service for converting PDF documents to Markdown format, designed to run as a system service on macOS.

## Overview

PDF2MD Service is a Python-based application that provides automated PDF to Markdown conversion capabilities. It's designed to run as a persistent system service on macOS, handling document conversion tasks efficiently and reliably.

## Project Structure 
```
.
├── config/         # 配置文件
├── docs/           # 文档
├── logs/           # 日志文件
├── outputs/        # 转换后的 Markdown 文件
├── samples/        # 示例 PDF 文件
├── src/            # 源代码
├── temp/           # 临时文件
├── tests/          # 单元测试
├── setup.py        # 项目设置和依赖
└── start_service.sh # 服务启动脚本
```

## Features

- PDF to Markdown conversion
- Runs as a macOS system service
- Automated document processing
- Logging and monitoring
- OSS storage integration
- Aliyun Log Service integration for centralized logging

## Requirements

- Python 3.x
- macOS
- Required Python packages:
  - requests>=2.32.0
  - oss2>=2.19.0
  - pyyaml>=6.0.0
  - aliyun-mns-sdk>=1.2.0
  - aliyun-log-python-sdk>=0.9.0
  - aliyun-python-sdk-core>=2.16.0
  - aliyun-python-sdk-kms>=2.16.0
  - magic-pdf>=1.1.0
  - numpy>=1.26.0
  - pandas>=2.2.0
  - pymupdf>=1.24.0
  - python-dateutil>=2.9.0

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the service:
```bash
# Copy the service configuration file
sudo cp com.rbase.pdf2md.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.rbase.pdf2md.plist
```

## Configuration

### Aliyun Services Configuration

The service uses several Aliyun cloud services that need to be configured in `config/config.yaml`:

#### MNS (Message Service)
```yaml
mns:
  endpoint: 'https://xxxx.mns.cn-region.aliyuncs.com'
  access_id: 'YOUR_ACCESS_ID'
  access_key: 'YOUR_ACCESS_KEY'
  queue_name: 'your-queue-name'
  topic:
    topic_name: 'your-topic-name'
    tag: ''  # Optional message tag
```

#### OSS (Object Storage Service)
```yaml
oss:
  endpoint: 'http://oss-cn-region.aliyuncs.com'
  access_id: 'YOUR_ACCESS_ID'
  access_key: 'YOUR_ACCESS_KEY'
  bucket_name: 'your-bucket-name'
```

#### SLS (Log Service)
```yaml
sls:
  endpoint: "cn-region.log.aliyuncs.com"  # Log service endpoint
  access_id: "YOUR_ACCESS_ID"  # Aliyun access key ID
  access_key: "YOUR_ACCESS_KEY"  # Aliyun access key secret
  project: "your-project-name"  # Log project name
  logstore: "your-logstore-name"  # Log store name
  topic: "pdf-service"  # Log topic
  source: "server-name"  # Log source identifier, unique per server
```

### Temporary Files Configuration
```yaml
temp:
  pdf_dir: 'temp/pdf'
  image_dir: 'temp/images'
  markdown_dir: 'temp/markdown'
```

## Usage

1. Start the service:
```bash
./start_service.sh
```

2. Monitor service status:
```bash
# Check service logs
tail -f logs/pdf_service.log

# Check service status
launchctl list | grep com.rbase.pdf2md
```

## Development

### Code Style
- Maximum line length: 100 characters
- Indentation: 4 spaces
- Quote style: Single quotes

### Testing
Run tests using pytest:
```bash
pytest tests/
```

### Project Rules
- All code must have unit tests
- All functions must be documented
- All classes must be documented
- All modules must be documented
- All configurations must be documented
- All exceptions must be documented

## Directory Structure Details

- `config/`: Configuration files for the service
- `docs/`: Project documentation
- `logs/`: Service logs and error reports
- `outputs/`: Generated markdown files
- `samples/`: Sample PDF files for testing
- `src/`: Main source code
- `temp/`: Temporary processing files
- `tests/`: Unit tests and test fixtures

## Logging

### Local Logging
Logs are stored in the following locations:
- Service logs: `logs/pdf_service.log`
- Error logs: `logs/error.log`

### Cloud Logging (Aliyun SLS)
The service also sends logs to Aliyun Log Service (SLS) for centralized logging:

- Each log entry includes:
  - Level (INFO/WARNING/ERROR)
  - Message
  - Timestamp
  - Additional context (article_id, file paths, etc.)
  - Source identifier (configured per server)

- To view logs in Aliyun console:
  1. Log in to the Aliyun console
  2. Navigate to Log Service (SLS)
  3. Select your project and logstore
  4. Use the query interface to search logs

- Common log queries:
  ```
  level: ERROR  # Find all error logs
  article_id: 12345  # Find logs for a specific article
  source: server-name  # Find logs from a specific server
  ```

## License

This project is proprietary software owned by Rbase.
All rights reserved. Unauthorized copying, modification, distribution, or use of this software, 
via any medium, is strictly prohibited.

This software is intended for internal use only within Rbase and by authorized personnel.
See the LICENSE file in the project root for the full license text.

## Contributing

This is an internal project. Please follow the project's coding standards and submit your changes through the internal code review process.

## Support

For internal support and bug reports, please contact the development team. 