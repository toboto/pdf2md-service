# Default output directory
DIST_DIR ?= ../dist

# Get current branch name
BRANCH_NAME := $(shell git rev-parse --abbrev-ref HEAD)

# Default targets
.PHONY: all install clean help

all: install

# Install target: extract current branch files to specified directory
install:
	@echo "Extracting current branch $(BRANCH_NAME) to $(DIST_DIR)"
	@mkdir -p $(DIST_DIR)
	@git archive HEAD | tar -x -C $(DIST_DIR)
	@echo "Files extracted to $(DIST_DIR)"

# Clean target: remove extracted files
clean:
	@echo "Cleaning output directory..."
	@rm -rf $(DIST_DIR)/*
	@echo "Output directory cleaned"

# Help information
help:
	@echo "Usage:"
	@echo "  make install [DIST_DIR=../dist]  - Extract current branch to specified directory"
	@echo "  make clean                      - Clean output directory"
	@echo "  make help                       - Show this help information" 