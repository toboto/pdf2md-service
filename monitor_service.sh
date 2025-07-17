#!/bin/bash

# 默认参数值
LOG_FILE="logs/pdf_service.log"
LOG_TIMEOUT=20
HEARTBEAT_TIMEOUT=10
CHECK_INTERVAL=60
UNAME_STR=$(uname)

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        -t|--timeout)
            LOG_TIMEOUT="$2"
            shift 2
            ;;
        -b|--heartbeat-timeout)
            HEARTBEAT_TIMEOUT="$2"
            shift 2
            ;;
        -i|--interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -f, --log-file FILE                日志文件路径 (默认: $LOG_FILE)"
            echo "  -t, --timeout MINUTES              一般日志超时时间(分钟) (默认: $LOG_TIMEOUT)"
            echo "  -b, --heartbeat-timeout MINUTES    心跳日志超时时间(分钟) (默认: $HEARTBEAT_TIMEOUT)"
            echo "  -i, --interval SECONDS             检查间隔(秒) (默认: $CHECK_INTERVAL)"
            echo "  -h, --help                         显示帮助信息"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

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
    
    # 查找最后一条INFO日志
    last_heartbeat=$(grep "[INFO]" "$LOG_FILE" | tail -n 1)

    timeout=$LOG_TIMEOUT
    # 检查是否为心跳日志，如果是则使用心跳超时时间
    if echo "$last_heartbeat" | grep -q "心跳"; then
        timeout=$HEARTBEAT_TIMEOUT
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 检测到心跳日志，使用心跳超时时间: $HEARTBEAT_TIMEOUT 分钟"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 使用标准日志超时时间: $LOG_TIMEOUT 分钟"
    fi

    
    
    if [ -z "$last_heartbeat" ]; then
        # 没有找到INFO日志，启动服务
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 未检测到INFO日志，启动服务..."
        if [ "$UNAME_STR" = "Darwin" ]; then
            ./start_service.sh
        else
            pids=$(ps aux | grep 'pdf_process_service.py' | grep -v grep | awk '{print $2}')
            if [ -n "$pids" ]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - 检测到pdf_process_service.py进程，尝试kill: $pids，并启动服务"
                kill $pids
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') - 未检测到pdf_process_service.py进程，请手动开启系统服务"
                ./start_service.sh
            fi
        fi
    else
        # 提取日志中的时间戳（使用 sed 替代 grep -P）
        log_time=$(echo "$last_heartbeat" | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}).*/\1/')
        
        # 判断当前操作系统，分别适配 macOS 和 Linux 的 date 命令
        if [ "$UNAME_STR" = "Darwin" ]; then
            # macOS 使用 -j 选项
            log_timestamp=$(date -j -f "%Y-%m-%d %H:%M:%S" "$log_time" +%s)
        else
            # Linux 下直接解析
            log_timestamp=$(date -d "$log_time" +%s)
        fi
        
        # 计算时间差（分钟）
        time_diff=$(( (current_time - log_timestamp) / 60 ))
        
        if [ "$time_diff" -gt "$LOG_TIMEOUT" ]; then
            # 日志超时，停止服务
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 日志超时（${time_diff}分钟），停止服务..."
            if [ "$UNAME_STR" = "Darwin" ]; then
                launchctl stop com.rbase.pdf2md
            else
                # 通过ps命令查找pdf_process_service.py进程并终止（无需root权限）
                pids=$(ps aux | grep 'pdf_process_service.py' | grep -v grep | awk '{print $2}')
                if [ -n "$pids" ]; then
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - 检测到pdf_process_service.py进程，尝试kill: $pids"
                    kill $pids
                else
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - 未检测到pdf_process_service.py进程，无法终止进程"
                fi
            fi
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 服务正常运行，最后日志${time_diff} 分钟前"
        fi
    fi
    
    # 等待下一次检查
    sleep $CHECK_INTERVAL
done 