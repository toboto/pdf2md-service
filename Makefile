# 默认输出目录
DIST_DIR ?= ../dist

# 获取当前分支名
BRANCH_NAME := $(shell git rev-parse --abbrev-ref HEAD)

# 获取当前时间作为版本号
VERSION := $(shell date +%Y%m%d_%H%M%S)

# 默认目标
.PHONY: all install clean

all: install

# 安装目标：将当前分支打包到指定目录
install:
	@echo "开始打包当前分支 $(BRANCH_NAME) 到 $(DIST_DIR)"
	@mkdir -p $(DIST_DIR)
	@git archive --format=tar.gz --output=$(DIST_DIR)/pdf2md-service_$(VERSION).tar.gz HEAD
	@echo "打包完成：$(DIST_DIR)/pdf2md-service_$(VERSION).tar.gz"

# 清理目标：删除打包文件
clean:
	@echo "清理打包文件..."
	@rm -f $(DIST_DIR)/pdf2md-service_*.tar.gz

# 帮助信息
help:
	@echo "用法："
	@echo "  make install [DIST_DIR=../dist]  - 打包当前分支到指定目录"
	@echo "  make clean                      - 清理打包文件"
	@echo "  make help                       - 显示帮助信息" 