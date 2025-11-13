"""
抖音热搜实时监控服务器
提供API接口供前端页面调用
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import subprocess
from datetime import datetime
import urllib.parse

class MonitorHandler(BaseHTTPRequestHandler):
    """处理监控请求的处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            # 返回监控页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open('monitor.html', 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        
        elif self.path == '/api/latest':
            # 返回最新数据
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data = self.get_latest_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        
        elif self.path == '/api/history':
            # 返回历史数据
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            history = self.get_history_data()
            self.wfile.write(json.dumps(history, ensure_ascii=False).encode('utf-8'))
        
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/fetch':
            # 触发数据抓取
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                # 运行main.py抓取数据
                result = subprocess.run(
                    ['python', 'main.py'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                # 获取最新数据（现在返回多个平台）
                platforms_data = self.get_latest_data()
                response = {
                    'success': True,
                    'message': '数据抓取成功',
                    'platforms': platforms_data
                }
            except Exception as e:
                response = {
                    'success': False,
                    'message': f'数据抓取失败: {str(e)}',
                    'data': None
                }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_latest_data(self):
        """获取最新的多平台热搜数据"""
        try:
            # 查找最新的txt文件
            output_dir = 'output'
            latest_file = None
            latest_time = None
            
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.endswith('.txt') and 'txt' in root:
                        file_path = os.path.join(root, file)
                        file_time = os.path.getmtime(file_path)
                        if latest_time is None or file_time > latest_time:
                            latest_time = file_time
                            latest_file = file_path
            
            if not latest_file:
                return [{
                    'platform': 'douyin',
                    'platformName': '抖音',
                    'items': [],
                    'timestamp': datetime.now().isoformat(),
                    'message': '暂无数据'
                }]
            
            # 读取文件内容
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按平台分割数据
            platforms_data = []
            platform_sections = content.split('\n\n')
            
            platform_name_map = {
                'douyin': '抖音',
                'weibo': '微博',
                'zhihu': '知乎',
                'bilibili': 'B站'
            }
            
            for section in platform_sections:
                if not section.strip():
                    continue
                
                lines = section.strip().split('\n')
                if len(lines) < 2:
                    continue
                
                # 第一行是平台信息
                platform_line = lines[0]
                if ' | ' not in platform_line:
                    continue
                
                platform_id, platform_name = platform_line.split(' | ')
                
                # 解析该平台的热搜数据
                items = []
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    # 解析每一行
                    parts = line.strip().split(' [URL:')
                    if len(parts) >= 2:
                        title_part = parts[0]
                        # 处理可能有多个URL的情况
                        urls = ' [URL:'.join(parts[1:])
                        url = urls.split(']')[0]
                        
                        # 提取排名和标题
                        if '. ' in title_part:
                            rank_str, title = title_part.split('. ', 1)
                            try:
                                rank = int(rank_str)
                            except:
                                continue
                        else:
                            continue
                        
                        items.append({
                            'rank': rank,
                            'title': title,
                            'url': url,
                            'timestamp': datetime.fromtimestamp(latest_time).isoformat()
                        })
                
                platforms_data.append({
                    'platform': platform_id,
                    'platformName': platform_name_map.get(platform_id, platform_name),
                    'items': items,
                    'timestamp': datetime.fromtimestamp(latest_time).isoformat()
                })
            
            return platforms_data if platforms_data else [{
                'platform': 'douyin',
                'platformName': '抖音',
                'items': [],
                'timestamp': datetime.now().isoformat(),
                'message': '暂无数据'
            }]
            
        except Exception as e:
            print(f'获取数据失败: {e}')
            import traceback
            traceback.print_exc()
            return [{
                'platform': 'douyin',
                'platformName': '抖音',
                'items': [],
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }]
    
    def get_history_data(self):
        """获取历史数据"""
        try:
            history = []
            output_dir = 'output'
            
            # 遍历所有日期文件夹
            for date_folder in os.listdir(output_dir):
                date_path = os.path.join(output_dir, date_folder)
                if not os.path.isdir(date_path):
                    continue
                
                txt_path = os.path.join(date_path, 'txt')
                if not os.path.exists(txt_path):
                    continue
                
                # 读取该日期下的所有txt文件
                for file in os.listdir(txt_path):
                    if file.endswith('.txt'):
                        file_path = os.path.join(txt_path, file)
                        file_time = os.path.getmtime(file_path)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        # 解析并筛选包含关键词的内容
                        keywords = ['胡歌', '可隆', 'kolon', 'KOLON']
                        matched_items = []
                        
                        for line in lines[1:]:
                            if not line.strip():
                                continue
                            
                            parts = line.strip().split(' [URL:')
                            if len(parts) == 2:
                                title = parts[0].split('. ', 1)[-1]
                                if any(keyword.lower() in title.lower() for keyword in keywords):
                                    matched_items.append(title)
                        
                        if matched_items:
                            history.append({
                                'date': date_folder,
                                'time': file.replace('.txt', ''),
                                'timestamp': datetime.fromtimestamp(file_time).isoformat(),
                                'count': len(matched_items),
                                'items': matched_items
                            })
            
            # 按时间倒序排序
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            return history[:20]  # 只返回最近20条
            
        except Exception as e:
            print(f'获取历史数据失败: {e}')
            return []
    
    def log_message(self, format, *args):
        """重写日志方法，使用UTF-8编码"""
        message = format % args
        print(f"{self.address_string()} - [{self.log_date_time_string()}] {message}")


def run_server(port=8000):
    """运行监控服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MonitorHandler)
    
    print('=' * 60)
    print('🚀 抖音热搜实时监控服务器启动成功!')
    print('=' * 60)
    print(f'📡 服务地址: http://localhost:{port}')
    print(f'🌐 监控页面: http://localhost:{port}/')
    print(f'📊 API接口: http://localhost:{port}/api/latest')
    print('=' * 60)
    print('💡 使用说明:')
    print('   1. 在浏览器打开监控页面')
    print('   2. 点击"立即刷新"手动更新数据')
    print('   3. 开启"自动刷新"实现持续监控')
    print('=' * 60)
    print('⏹️  按 Ctrl+C 停止服务器\n')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n\n服务器已停止')
        httpd.server_close()


if __name__ == '__main__':
    run_server()

