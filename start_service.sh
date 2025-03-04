#!/bin/bash

# 函数：停止服务
stop_service() {
    echo "正在停止服务..."
    launchctl stop com.rbase.pdf2md
    launchctl unload com.rbase.pdf2md.plist
    echo "服务已停止"
}

# 检查是否需要先停止服务
if launchctl list | grep -q com.rbase.pdf2md; then
    echo "服务已经在运行，先停止它"
    stop_service
fi

# 获取当前目录的绝对路径
CURRENT_DIR=$(pwd)

# 备份原始plist文件
cp com.rbase.pdf2md.plist com.rbase.pdf2md.plist.bak

# 将plist文件中的[dist_home]替换为当前目录
sed -i '' "s|\[dist_home\]|$CURRENT_DIR|g" com.rbase.pdf2md.plist

echo "已将plist文件中的[dist_home]替换为当前目录: $CURRENT_DIR"

# 加载服务
echo "正在加载服务..."
launchctl load com.rbase.pdf2md.plist
if [ $? -eq 0 ]; then
    echo "服务加载成功"
else
    echo "服务加载失败"
    exit 1
fi

# 启动服务
echo "正在启动服务..."
launchctl start com.rbase.pdf2md
if [ $? -eq 0 ]; then
    echo "服务启动成功"
else
    echo "服务启动失败"
    exit 1
fi

# 检查服务是否正在运行
echo "检查服务状态..."
launchctl list | grep com.rbase.pdf2md
if [ $? -eq 0 ]; then
    echo "服务正在运行"
else
    echo "服务未运行，请检查日志文件"
    exit 1
fi

# 等待服务完全启动
echo "等待服务完全启动..."
sleep 3

# 检查日志文件
echo "检查日志文件..."
if [ -f "$CURRENT_DIR/logs/pdf_service.log" ]; then
    echo "最近的日志内容："
    tail -n 10 "$CURRENT_DIR/logs/pdf_service.log"
else
    echo "警告：日志文件不存在，请手动检查服务状态"
fi

# 检查错误日志
if [ -f "$CURRENT_DIR/logs/error.log" ] && [ -s "$CURRENT_DIR/logs/error.log" ]; then
    echo "错误日志内容："
    tail -n 10 "$CURRENT_DIR/logs/error.log"
    echo "警告：发现错误日志，请检查服务是否正常运行"
fi

echo "服务已成功启动"

# 使用说明
echo ""
echo "如需停止服务，请运行："
echo "launchctl stop com.rbase.pdf2md && launchctl unload com.rbase.pdf2md.plist"
