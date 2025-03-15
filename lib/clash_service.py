import atexit
import copy
import itertools
import os
import random
import signal
import socket
import subprocess
import sys
import traceback
from urllib.parse import urlencode, quote
import yaml
import requests

SUBSCRIBE_URL = "https://api.immtel.co/?L1N1YnNjcmlwdGlvbi9DbGFzaD9zaWQ9MTA0NjgmdG9rZW49ZnZJZ0dIdHpXdnEmbW09MjA1NTQmNjcyNmExMTk2"
CLASH_BIN = "/home/ray/Downloads/clash_2.0.24_linux_amd64/clash"


try:
    conf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conf")
    conf_fp1 = os.path.join(conf_dir, "1.yaml")
    if not os.path.exists(conf_fp1):
        os.makedirs(conf_dir, exist_ok=True)
        response = requests.get(SUBSCRIBE_URL)
        with open(conf_fp1, 'wb') as f:
            f.write(response.content)

    with open(conf_fp1, 'rb') as conf_file1:
        conf_yaml1 = yaml.safe_load(conf_file1.read())

    print("yaml loaded")
except Exception:
    print("获取订阅失败")
    traceback.print_exc()

class ClashService:
    port_offset = 7890
    port = 7890
    socks_port = 7891
    external_controller_port = 9090

    group_name = "Proxies"

    def __init__(self, port_offset=7890, index=1):
        """
        初始化时寻找几个可用端口，并启动 clash 服务。
        :param num_ports: 要查找的可用端口数量（默认3个）
        :param config_path: 可选的 clash 配置文件目录，如果有则传入
        """
        self.port_offset = port_offset
        self.port, self.socks_port, self.external_controller_port = (self._find_available_port() for _ in range(3))

        conf_fp = os.path.join(conf_dir, f"{str(index)}.yaml")
        conf_yaml = copy.deepcopy(conf_yaml1)
        conf_yaml['port'] = self.port
        conf_yaml['socks-port'] = self.socks_port
        conf_yaml['external-controller'] = f":{self.external_controller_port}"
        with open(conf_fp, 'w', encoding='utf-8') as file:
            yaml.dump(conf_yaml, file, allow_unicode=True)
        # 拼接启动 clash 的命令，-external-controller 用于开启外部控制接口
        cmd = [CLASH_BIN, "-f", conf_fp]

        # 后台启动 clash 服务
        self.process = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,  # 以文本模式读取输出
                                        bufsize=1,  # 行缓冲模式
                                        )

        def cleanup():
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()

        def handle_signal(sig, frame):
            cleanup()
            sys.exit(0)

        atexit.register(cleanup)
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        target_string = "RESTful API listening at:"
        found = False

        # 循环读取stdout输出
        while True:
            # 逐行读取stdout
            line = self.process.stdout.readline()
            if line:
                print(line.strip())  # 可选：实时打印输出
                if target_string in line:
                    found = True
                    break
            else:
                # 检查子进程是否已退出
                if self.process.poll() is not None:
                    break

        # 检查是否找到目标字符串
        if not found:
            # 处理未找到的情况（如超时或进程异常退出）
            error = self.process.stderr.read()
            raise RuntimeError(f"目标字符串未找到，进程可能已失败：\n{error}")

        self.http_proxy = f'http://127.0.0.1:{str(self.port)}'
        print(f"Clash {index} 启动成功")


    def _find_available_port(self):
        """查找一个可用的端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            for port in itertools.count(self.port_offset):
                try:
                    self.port_offset += 1
                    s.bind(('', port))

                    return port
                except OSError:
                    continue

    def check_node_delay(self, node_name, threshold=500):
        """
        测试指定节点的延迟是否低于阈值（默认500毫秒）。

        :param threshold: 延迟阈值，单位毫秒，默认500
        :return: 如果延迟低于阈值返回 True，否则返回 False
        """
        # 构造测试延迟的 URL，注意对节点名称进行 URL 编码
        url = f"http://127.0.0.1:{self.external_controller_port}/proxies/{quote(self.group_name)}/delay?timeout=5000&url=https://www.google.com"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            # 假设返回 JSON 中包含 "delay" 字段，单位为毫秒
            data = response.json()
            delay = data.get("delay")
            if delay is None:
                print("未获取到延迟信息，请检查返回数据：", data)
                return False
            print(f"节点 '{node_name}' 的延迟为 {delay} 毫秒")
            if delay < threshold:
                print(f"延迟低于 {threshold} 毫秒")
                return True
            else:
                print(f"延迟不低于 {threshold} 毫秒")
                return False
        except Exception as e:
            print(f"请求延迟测试时出错: {e}")
            return False

    def switch(self):
        """
        随机切换代理组中的节点

        :param group: 代理组名称（字符串），例如 "Proxy Group"
        :param nodes: 节点名称列表（列表），例如 ["节点1", "节点2", "节点3"]
        :return: 被切换到的节点名称，如果失败返回 None
        """
        while True:
            selected_node = random.choice(conf_yaml1['proxy-groups'][0]['proxies'][1:])

            # URL 中如果包含中文，需要进行 URL 编码
            url = f"http://127.0.0.1:{self.external_controller_port}/proxies/{quote(self.group_name)}"
            payload = {"name": selected_node}
            try:
                # 如果配置文件里没有设置 secret，这里不需要添加认证头
                response = requests.put(url, json=payload)
                response.raise_for_status()
                print(f"代理组 '{self.group_name}' 已切换到节点 '{selected_node}'。")
                return selected_node
            except Exception as e:
                print(f"切换节点时出错：{e}")
                return None

            if self.check_node_delay(selected_node):
                break

    def stop(self):
        """停止 clash 服务"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("Clash 服务已停止。")


if __name__ == '__main__':
    clash_service = ClashService(9999, 1)
    clash_service.switch()
    while True:
        pass
