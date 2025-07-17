#!/bin/bash

# Default parameter values
LOG_FILE="logs/pdf_service.log"
LOG_TIMEOUT=20
HEARTBEAT_TIMEOUT=10
CHECK_INTERVAL=60
UNAME_STR=$(uname)

# Parse command line arguments
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
            echo "  -f, --log-file FILE                Log file path (default: $LOG_FILE)"
            echo "  -t, --timeout MINUTES              General log timeout in minutes (default: $LOG_TIMEOUT)"
            echo "  -b, --heartbeat-timeout MINUTES    Heartbeat log timeout in minutes (default: $HEARTBEAT_TIMEOUT)"
            echo "  -i, --interval SECONDS             Check interval in seconds (default: $CHECK_INTERVAL)"
            echo "  -h, --help                         Show help information"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Ensure log file exists
if [ ! -f "$LOG_FILE" ]; then
    if [ "$UNAME_STR" = "Darwin" ]; then
        echo "Log file does not exist, starting service..."
        ./start_service.sh
        exit 0
    else
        echo "Log file does not exist, please start service manually"
        exit 1
    fi
fi

# Main loop
while true; do
    # Get current timestamp
    current_time=$(date +%s)
    
    # Find the last INFO log
    last_heartbeat=$(grep "[INFO]" "$LOG_FILE" | tail -n 1)

    timeout=$LOG_TIMEOUT
    # Check if it's a heartbeat log, if so use heartbeat timeout
    if echo "$last_heartbeat" | grep -q "心跳"; then
        timeout=$HEARTBEAT_TIMEOUT
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Detected heartbeat log, using heartbeat timeout: $HEARTBEAT_TIMEOUT minutes"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Using processing log timeout: $LOG_TIMEOUT minutes"
    fi

    
    
    if [ -z "$last_heartbeat" ]; then
        # No INFO log found, start service
        echo "$(date '+%Y-%m-%d %H:%M:%S') - No INFO log detected, starting service..."
        if [ "$UNAME_STR" = "Darwin" ]; then
            ./start_service.sh
        else
            pids=$(ps aux | grep 'pdf_process_service.py' | grep -v grep | awk '{print $2}')
            if [ -n "$pids" ]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Detected pdf_process_service.py process, attempting to kill: $pids, and starting service"
                kill $pids
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') - No pdf_process_service.py process detected, please manually start system service"
                ./start_service.sh
            fi
        fi
    else
        # Extract timestamp from log (using sed instead of grep -P)
        log_time=$(echo "$last_heartbeat" | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}).*/\1/')
        
        # Determine current operating system, adapt to macOS and Linux date commands
        if [ "$UNAME_STR" = "Darwin" ]; then
            # macOS uses -j option
            log_timestamp=$(date -j -f "%Y-%m-%d %H:%M:%S" "$log_time" +%s)
        else
            # Linux direct parsing
            log_timestamp=$(date -d "$log_time" +%s)
        fi
        
        # Calculate time difference (minutes)
        time_diff=$(( (current_time - log_timestamp) / 60 ))
        
        if [ "$time_diff" -gt "$LOG_TIMEOUT" ]; then
            # Log timeout, stop service
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Log timeout (${time_diff} minutes), stopping service..."
            if [ "$UNAME_STR" = "Darwin" ]; then
                launchctl stop com.rbase.pdf2md
            else
                # Find pdf_process_service.py process via ps command and terminate (no root permission required)
                pids=$(ps aux | grep 'pdf_process_service.py' | grep -v grep | awk '{print $2}')
                if [ -n "$pids" ]; then
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - Detected pdf_process_service.py process, attempting to kill: $pids"
                    kill $pids
                else
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - No pdf_process_service.py process detected, cannot terminate process"
                fi
            fi
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Service running normally, last log ${time_diff} minutes ago"
        fi
    fi
    
    # Wait for next check
    sleep $CHECK_INTERVAL
done 