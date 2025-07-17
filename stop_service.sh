#!/bin/bash

# 检查当前操作系统是否为macOS，如果不是则退出并报错
OS_NAME=$(uname)
if [ "$OS_NAME" = "Darwin" ]; then
    launchctl stop com.rbase.pdf2md
    launchctl unload com.rbase.pdf2md.plist
else
    pids=$(ps aux | grep 'pdf_process_service.py' | grep -v grep | awk '{print $2}')
    if [ -n "$pids" ]; then
        kill $pids
    else
        echo "No pdf_process_service.py process detected, cannot terminate process"
    fi
fi
