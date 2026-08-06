#!/bin/bash
# OCR 双引擎监控: 任一引擎退出即报告
while true; do
    cloud_alive=0; local_alive=0
    ps -p 714 > /dev/null 2>&1 && cloud_alive=1
    ps -p 722 > /dev/null 2>&1 && local_alive=1
    if [ $cloud_alive -eq 0 ] && [ $local_alive -eq 0 ]; then
        echo "双引擎都已完成"
        exit 0
    fi
    if [ $cloud_alive -eq 0 ]; then
        echo "云端引擎已完成 (PID 714)，本地引擎仍在运行"
        exit 0
    fi
    if [ $local_alive -eq 0 ]; then
        echo "本地引擎已完成 (PID 722)，云端引擎仍在运行"
        exit 0
    fi
    sleep 60
done
