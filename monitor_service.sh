#!/bin/bash

# 设置日志文件路径
LOG_FILE="logs/pdf_service.log"
# 设置心跳超时时间（分钟）
HEARTBEAT_TIMEOUT=10
# 设置检查间隔（秒）
CHECK_INTERVAL=60

# 确保日志文件存在
if [ ! -f "$LOG_FILE" ]; then
    echo "日志文件不存在，启动服务..."
    ./start_service.sh
    exit 0
fi

# 主循环
while true; do
    # 获取当前时间戳
    current_time=$(date +%s)
    
    # 查找最后一条心跳日志
    last_heartbeat=$(grep "心跳检测" "$LOG_FILE" | tail -n 1)
    
    if [ -z "$last_heartbeat" ]; then
        # 没有找到心跳日志，启动服务
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 未检测到心跳日志，启动服务..."
        ./start_service.sh
    else
        # 提取日志中的时间戳（使用 sed 替代 grep -P）
        log_time=$(echo "$last_heartbeat" | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}).*/\1/')
        # 在 macOS 上使用 -j 选项解析日期
        log_timestamp=$(date -j -f "%Y-%m-%d %H:%M:%S" "$log_time" +%s)
        
        # 计算时间差（分钟）
        time_diff=$(( (current_time - log_timestamp) / 60 ))
        
        if [ "$time_diff" -gt "$HEARTBEAT_TIMEOUT" ]; then
            # 心跳超时，停止服务
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 心跳超时（${time_diff}分钟），停止服务..."
            ./stop_service.sh
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 服务正常运行，最后心跳 ${time_diff} 分钟前"
        fi
    fi
    
    # 等待下一次检查
    sleep $CHECK_INTERVAL
done 