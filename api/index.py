# -*- coding: UTF-8 -*-
import requests
import re
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 设置超时时间（避免请求挂起）
TIMEOUT = 10

def list_split(items, n):
    """将列表按n个元素一组分割"""
    return [items[i:i + n] for i in range(0, len(items), n)]

def getdata(name):
    """获取GitHub用户的贡献数据"""
    try:
        # 1. 发送请求（带超时和User-Agent，避免被反爬）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(
            f"https://github.com/{name}",
            headers=headers,
            timeout=TIMEOUT
        )
        response.raise_for_status()  # 触发HTTP错误（如404用户不存在）
        data = response.text

        # 2. 正则匹配（优化匹配规则，提高稳定性）
        datadatereg = re.compile(r'data-date="([\d-]+)"[^>]*data-level')
        datacountreg = re.compile(r'<span class="sr-only">(\d+|No) contribution')
        
        datadate = datadatereg.findall(data)
        datacount = datacountreg.findall(data)

        # 3. 处理空数据（如用户不存在或无贡献）
        if not datadate or not datacount:
            return {"error": "No contribution data found", "total": 0, "contributions": []}

        # 4. 转换贡献次数为整数
        datacount = [0 if cnt == "No" else int(cnt) for cnt in datacount]

        # 5. 按日期排序（确保时间顺序正确）
        sorted_data = sorted(zip(datadate, datacount), key=lambda x: x[0])
        datadate, datacount = zip(*sorted_data)

        # 6. 格式化返回数据
        contributions = sum(datacount)
        datalist = [{"date": d, "count": c} for d, c in zip(datadate, datacount)]
        return {
            "total": contributions,
            "contributions": list_split(datalist, 7)
        }

    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}", "total": 0, "contributions": []}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "total": 0, "contributions": []}
    except Exception as e:
        return {"error": f"Data processing error: {str(e)}", "total": 0, "contributions": []}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 1. 解析URL参数（正确获取用户名）
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            user = query_params.get('user', [None])[0]  # 支持 /api?user=用户名 格式

            if not user:
                # 返回参数错误提示
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing 'user' parameter (use ?user=github_username)"}).encode('utf-8'))
                return

            # 2. 获取数据并返回
            data = getdata(user)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))

        except Exception as e:
            # 捕获所有未处理的异常，避免服务器崩溃
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Server error: {str(e)}"}).encode('utf-8'))
        return
