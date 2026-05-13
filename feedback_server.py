#!/usr/bin/env python3
"""Tards 反馈接收服务器。

独立运行，监听TCP端口，接收来自游戏客户端的反馈数据并保存为JSON文件。

用法：
    python feedback_server.py --port 9999

默认端口：9999
"""

import argparse
import json
import os
import socketserver
import threading
from datetime import datetime
from typing import Any, Dict

FEEDBACK_DIR = "feedback"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_feedback(data: Dict[str, Any]) -> str:
    """保存反馈数据到本地JSON文件，返回保存路径。"""
    ensure_dir(FEEDBACK_DIR)
    player_name = data.get("player_name", "unknown")
    timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ts = timestamp.replace(":", "-").replace(" ", "_")
    fname = f"feedback_{player_name}_{ts}.json"
    path = os.path.join(FEEDBACK_DIR, fname)

    # 如果文件名冲突，追加序号
    if os.path.exists(path):
        base, ext = os.path.splitext(fname)
        i = 1
        while os.path.exists(path):
            fname = f"{base}_{i}{ext}"
            path = os.path.join(FEEDBACK_DIR, fname)
            i += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


class FeedbackHandler(socketserver.StreamRequestHandler):
    """处理单个TCP连接中的反馈数据。"""

    def handle(self):
        client_addr = self.client_address[0]
        try:
            # 读取一行JSON数据
            line = self.rfile.readline()
            if not line:
                return
            data = json.loads(line.decode("utf-8"))

            # 保存
            path = save_feedback(data)

            # 控制台打印摘要
            player = data.get("player_name", "unknown")
            desc = data.get("description", "")[:60]
            log_file = data.get("log_file", "N/A")
            print(f"[反馈] 来自 {player} ({client_addr})")
            print(f"       描述: {desc}")
            print(f"       日志: {log_file}")
            print(f"       已保存: {path}")
            print()

            # 发送确认
            self.wfile.write(b'{"status":"OK"}\n')
        except json.JSONDecodeError as e:
            print(f"[错误] 来自 {client_addr} 的JSON解析失败: {e}")
            self.wfile.write(b'{"status":"ERROR","reason":"invalid_json"}\n')
        except Exception as e:
            print(f"[错误] 处理 {client_addr} 的反馈时出错: {e}")
            self.wfile.write(b'{"status":"ERROR","reason":"server_error"}\n')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """支持多线程的TCP服务器。"""
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="Tards 反馈接收服务器")
    parser.add_argument("--port", type=int, default=9999, help="监听端口（默认 9999）")
    args = parser.parse_args()

    host = "0.0.0.0"
    port = args.port

    ensure_dir(FEEDBACK_DIR)
    server = ThreadedTCPServer((host, port), FeedbackHandler)

    print(f"=" * 50)
    print(f"Tards 反馈接收服务器已启动")
    print(f"监听地址: {host}:{port}")
    print(f"保存目录: {os.path.abspath(FEEDBACK_DIR)}")
    print(f"按 Ctrl+C 停止")
    print(f"=" * 50)
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.shutdown()
        server.server_close()
        print("已停止。")


if __name__ == "__main__":
    main()
