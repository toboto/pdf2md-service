# PDF2MD Service

A service for converting PDF documents to Markdown format, designed to run as a system service on macOS and Linux.

## Overview

PDF2MD Service is a Python-based application that provides automated PDF to Markdown conversion capabilities. It's designed to run as a persistent system service on macOS and Linux, handling document conversion tasks efficiently and reliably. The service integrates with Aliyun cloud services for message queuing, object storage, and centralized logging.

## Project Structure 
```
.
├── config/         # Configuration files
├── docs/           # Documentation
├── logs/           # Log files
├── outputs/        # Converted Markdown files
├── samples/        # Sample PDF files
├── src/            # Source code
├── temp/           # Temporary files
├── tests/          # Unit tests
├── setup.py        # Project setup and dependencies
├── start_service.sh # Service startup script
├── stop_service.sh  # Service stop script
├── monitor_service.sh # Service monitoring script
└── com.rbase.pdf2md.plist # macOS service configuration
```

## Features

- **PDF to Markdown conversion** with OCR support
- **Cross-platform support** for macOS and Linux
- **Automated document processing** via message queues
- **Comprehensive logging and monitoring**
- **OSS storage integration** for result storage
- **Aliyun Log Service integration** for centralized logging
- **Enterprise WeChat notification** for error alerts
- **Service monitoring** with automatic restart capabilities
- **Heartbeat monitoring** for service health checks
- **Graceful error handling** with fallback mechanisms

## Requirements

- Python 3.8+
- macOS or Linux
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
  - psutil>=5.9.0

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd pdf2md-service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the service:

### macOS
```bash
# Copy the service configuration file
sudo cp com.rbase.pdf2md.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.rbase.pdf2md.plist
```

### Linux
```bash
# Create systemd service file
sudo cp systemd/pdf2md.service /etc/systemd/system/

# Enable and start the service
sudo systemctl enable pdf2md.service
sudo systemctl start pdf2md.service
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
  enabled: true  # Enable/disable cloud logging
  endpoint: "cn-region.log.aliyuncs.com"  # Log service endpoint
  access_id: "YOUR_ACCESS_ID"  # Aliyun access key ID
  access_key: "YOUR_ACCESS_KEY"  # Aliyun access key secret
  project: "your-project-name"  # Log project name
  logstore: "your-logstore-name"  # Log store name
  topic: "pdf-service"  # Log topic
  source: "server-name"  # Log source identifier, unique per server
```

#### Notification Configuration
```yaml
notice:
  corp_wechat_hook_url: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY'
```

### Temporary Files Configuration
```yaml
temp:
  pdf_dir: 'temp/pdf'
  image_dir: 'temp/images'
  markdown_dir: 'temp/markdown'
```

## Usage

### Manual Service Management

1. Start the service:
```bash
./start_service.sh
```

2. Stop the service:
```bash
./stop_service.sh
```

3. Monitor service status:
```bash
# Check service logs
tail -f logs/pdf_service.log

# Check service status (macOS)
launchctl list | grep com.rbase.pdf2md

# Check service status (Linux)
systemctl status pdf2md.service
```

### Service Monitoring

The service includes a monitoring script that automatically restarts the service if it becomes unresponsive:

```bash
# Start monitoring (with default settings)
./monitor_service.sh

# Custom monitoring options
./monitor_service.sh --log-file logs/pdf_service.log --timeout 20 --heartbeat-timeout 10 --interval 60
```

Monitoring options:
- `-f, --log-file`: Log file path (default: logs/pdf_service.log)
- `-t, --timeout`: General log timeout in minutes (default: 20)
- `-b, --heartbeat-timeout`: Heartbeat log timeout in minutes (default: 10)
- `-i, --interval`: Check interval in seconds (default: 60)
- `-h, --help`: Show help information

## Development

### Code Style
- Maximum line length: 100 characters
- Indentation: 4 spaces
- Quote style: Single quotes
- All code must be documented with comprehensive comments

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
- Follow Git Commit Conventions for commit messages

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
  - Service uptime and memory usage (heartbeat logs)

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
  message: "heartbeat"  # Find heartbeat logs
  ```

### Heartbeat Monitoring
The service sends heartbeat logs every 5 minutes (configurable) to indicate it's running properly. These logs include:
- Service uptime
- Memory usage
- Current timestamp

## Error Handling

The service includes comprehensive error handling:

1. **PDF Processing Errors**: Automatic fallback to OCR mode when text extraction fails
2. **Network Errors**: Retry mechanisms for file downloads and uploads
3. **Service Monitoring**: Automatic restart when service becomes unresponsive
4. **Notification System**: Enterprise WeChat notifications for critical errors
5. **Graceful Degradation**: Service continues running even when some components fail

## Performance

- **Concurrent Processing**: Handles multiple PDF files simultaneously
- **Memory Management**: Efficient memory usage with automatic cleanup
- **Resource Monitoring**: Tracks memory usage and service health
- **Timeout Handling**: Configurable timeouts for various operations

## Security

- **Access Control**: Uses Aliyun access keys for secure cloud service access
- **Error Logging**: Sensitive information is not logged
- **Service Isolation**: Runs as a dedicated system service
- **Configuration Security**: Configuration files should be protected with appropriate permissions

## Troubleshooting

### Common Issues

1. **Service won't start**:
   - Check configuration file syntax
   - Verify Aliyun credentials
   - Check log files for error messages

2. **PDF processing fails**:
   - Ensure PDF files are not corrupted
   - Check available disk space
   - Verify magic-pdf installation

3. **Monitoring alerts**:
   - Check service logs for errors
   - Verify network connectivity
   - Ensure sufficient system resources

### Debug Mode
Run the service in debug mode for detailed logging:
```bash
python src/pdf_process_service.py --config config/config.yaml --wait-seconds 30 --max-runtime 3600 --log-heartbeat-period 300
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