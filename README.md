# PDF2MD Service

A service for converting PDF documents to Markdown format, designed to run as a system service on macOS.

## Overview

PDF2MD Service is a Python-based application that provides automated PDF to Markdown conversion capabilities. It's designed to run as a persistent system service on macOS, handling document conversion tasks efficiently and reliably.

## Project Structure 
.
├── config/ # Configuration files
├── docs/ # Documentation
├── logs/ # Log files
├── outputs/ # Converted markdown files
├── samples/ # Sample PDF files
├── src/ # Source code
├── temp/ # Temporary files
├── tests/ # Unit tests
├── setup.py # Project setup and dependencies
└── start_service.sh # Service startup script


## Features

- PDF to Markdown conversion
- Runs as a macOS system service
- Automated document processing
- Logging and monitoring
- OSS storage integration

## Requirements

- Python 3.x
- macOS
- Required Python packages:
  - requests
  - oss2
  - pyyaml

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

Logs are stored in the following locations:
- Service logs: `logs/pdf_service.log`
- Error logs: `logs/error.log`

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