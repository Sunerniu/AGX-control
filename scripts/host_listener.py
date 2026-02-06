import socket
import json
import time
import os
import math

# 配置参数 (需与 C++ 设置保持一致)
BIND_IP = "0.0.0.0"  # 监听本机所有 IP
BIND_PORT = 14550    # 默认 UDP 端口
BUFFER_SIZE = 10240  # 加大缓冲区以容纳包含队列的长 JSON

def clear_screen():
    """跨平台清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def calculate_distance(lat1, lon1, lat2, lon2):
    """粗略计算两点间距离(米)"""
    if lat1 == 0 or lat2 == 0: return 0.0
    R = 6378137.0 # 地球半径
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def print_status(s, addr):
    clear_screen()
    
    # --- 1. 基础遥测数据解析 ---
    ts = s.get('timestamp', 0)
    local_time = time.strftime('%H:%M:%S', time.localtime(ts))
    
    pos = s.get('position', {})
    cur_lat = pos.get('lat', 0.0)
    cur_lon = pos.get('lon', 0.0)
    cur_alt = pos.get('alt', 0.0)
    
    vel = s.get('velocity', {})
    att = s.get('attitude', {})
    bat = s.get('battery', {})
    f_status = s.get('flight_status', -1)
    
    # --- 2. 导航数据解析 (用户自定义结构) ---
    nav = s.get('navigation', {})
    is_navigating = nav.get('is_navigating', False)
    has_target = nav.get('has_target', False)
    
    # 解析当前目标
    curr_target = nav.get('current_target', {})
    if curr_target is None: curr_target = {}
    
    tgt_lat = curr_target.get('lat', 0.0)
    tgt_lon = curr_target.get('lon', 0.0)
    tgt_alt = curr_target.get('alt', 0.0)
    tgt_spd = curr_target.get('speed', 0.0)
    
    # 解析队列
    queue_count = nav.get('queue_count', 0)
    queue_list = nav.get('queue', [])

    # 计算距离
    dist_to_target = 0.0
    if has_target:
        dist_to_target = calculate_distance(cur_lat, cur_lon, tgt_lat, tgt_lon)

    # --- 3. 界面显示 ---
    print(f"========== DJI AGX 地面站监控 ==========")
    print(f"来源: {addr[0]}:{addr[1]} | 更新: {local_time}")
    print("=" * 40)
    
    # A. 导航状态模块
    status_str = "🟢 正在巡航" if is_navigating else "⚪ 待机/手动"
    print(f"【导航系统】 {status_str}")
    
    if has_target:
        print(f"  📍 当前奔赴: Lat {tgt_lat:.6f}, Lon {tgt_lon:.6f}")
        print(f"     目标高度: {tgt_alt:.1f}m | 设定速度: {tgt_spd:.1f} m/s")
        print(f"  📏 剩余距离: {dist_to_target:.1f} 米")
    else:
        print(f"  📍 当前目标: 无")
        
    print(f"  📚 待飞队列: {queue_count} 个航点")
    
    # 显示队列前几个点（如果有）
    if queue_count > 0 and queue_list:
        print(f"     [下一点] Lat {queue_list[0].get('lat',0):.4f}... " + ("(还有更多)" if queue_count > 1 else ""))

    print("-" * 40)

    # B. 实时飞行数据模块
    print(f"【实时状态】")
    print(f"  🌍 位置: {cur_lat:.7f}, {cur_lon:.7f}, {cur_alt:.1f}m")
    print(f"  📐 姿态: R {att.get('roll', 0):.1f}°, P {att.get('pitch', 0):.1f}°, Y {att.get('yaw', 0):.1f}°")
    print(f"  🚀 速度: N {vel.get('vx', 0):.1f}, E {vel.get('vy', 0):.1f}, D {vel.get('vz', 0):.1f} m/s")
    
    # 简单的电量条
    bat_pct = bat.get('percent', 0)
    bar_len = int(bat_pct / 5)
    bat_bar = "█" * bar_len + "░" * (20 - bar_len)
    print(f"  🔋 电量: [{bat_bar}] {bat_pct}% ({bat.get('voltage',0)}mV)")
    
    print("=" * 40)
    print("按 Ctrl+C 退出监听")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 允许端口复用（防止重启脚本时端口被占）
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((BIND_IP, BIND_PORT))
        print(f"[INFO] 正在监听 UDP 端口 {BIND_PORT} ...")
        
        while True:
            try:
                # 接收数据
                data, addr = sock.recvfrom(BUFFER_SIZE)
                
                # 解码
                json_str = data.decode('utf-8')
                status = json.loads(json_str)
                
                # 打印
                print_status(status, addr)
                
            except json.JSONDecodeError:
                pass # 忽略不完整的包
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n[INFO] 停止监听")
    finally:
        sock.close()

if __name__ == "__main__":
    main()