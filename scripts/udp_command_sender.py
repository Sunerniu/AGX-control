import socket
import struct
import sys

# AGX 配置
AGX_IP = "10.129.12.126"  # AGX IP (请根据实际情况修改)
AGX_PORT = 14551          # AGX 监听端口 (UDP)

# 协议常量
PROTOCOL_HEADER = 0xAA55

# 命令定义 (需与C++ protocol.h 保持一致)
CMD_MAP = {
    "TAKEOFF": 0x01,
    "LAND": 0x02,
    "GOHOME": 0x03,
    "CANCEL_GOHOME": 0x04,
    "HOVER": 0x05,
    "CONFIRM_LAND": 0x06,
    "FORCE_LAND": 0x07,
    "CANCEL_LAND": 0x08,
    "GOTO": 0x10,
    "FLYTO": 0x11,
    "PLANTO": 0x12,
    "PLANSTO": 0x13,
    "KMZS": 0x14,
    "CHANGESTO": 0x15,
    "NAV_START": 0x20,
    "NAV_STOP": 0x21,
    "AUTH": 0x31
}

def calculate_checksum(packet_bytes_no_checksum):
    """简单累加校验和"""
    checksum = sum(packet_bytes_no_checksum)
    return checksum & 0xFFFF  # 截断为 uint16

def send_packet(cmd_type, lat=0.0, lon=0.0, alt=0.0, spd=0.0):
    # 构造包体 (不含校验和)
    # struct: header(H), cmd(B), reserved(B), lat(d), lon(d), alt(f), speed(f)
    # 小端序 (<)
    format_str_no_chk = "<HBBddff"
    
    header = PROTOCOL_HEADER
    reserved = 0
    
    # 第一次打包计算校验和
    data_no_chk = struct.pack(format_str_no_chk, header, cmd_type, reserved, lat, lon, alt, spd)
    
    checksum = calculate_checksum(data_no_chk)
    
    # 最终打包 (追加校验和 H)
    final_packet = data_no_chk + struct.pack("<H", checksum)
    
    print(f"[INFO] 发送UDP命令: 0x{cmd_type:02X}, 目标: {AGX_IP}:{AGX_PORT}")
    print(f"       Payload: Lat:{lat}, Lon:{lon}, Alt:{alt}, Spd:{spd}")
    print(f"       Checksum: {checksum}")
    
    try:
        # 使用 SOCK_DGRAM 创建 UDP 套接字
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # UDP 不需要 connect，直接 sendto
            s.sendto(final_packet, (AGX_IP, AGX_PORT))
            print("[OK] 数据包已发送")
            
    except Exception as e:
        print(f"[ERROR] 发送失败: {e}")

def print_usage():
    print("用法: python udp_sender.py <COMMAND> [args]")
    print("支持命令:")
    print("  TAKEOFF")
    print("  LAND")
    print("  GOHOME")
    print("  HOVER")
    print("  STOP_NAV")
    print("  AUTH")
    print("  PLANSTO <lat> <lon> <alt> [speed]")
    print("  CHANGESTO <lat> <lon> <alt> [speed]")
    print("\n示例:")
    print("  python udp_sender.py TAKEOFF")
    print("  python udp_sender.py PLANSTO 22.5428 113.9589 15.0 2.0")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
        
    cmd_name = sys.argv[1].upper()
    
    if cmd_name not in CMD_MAP:
        # 处理一些别名
        if cmd_name == "STOP": cmd_name = "NAV_STOP"
        elif cmd_name == "STOP_NAV": cmd_name = "NAV_STOP"
        else:
            print(f"[ERROR] 未知命令: {cmd_name}")
            print_usage()
            sys.exit(1)
            
    cmd_val = CMD_MAP[cmd_name]
    
    lat = 0.0
    lon = 0.0
    alt = 0.0
    spd = 0.0 # 默认速度
    
    # 解析参数
    # 如果是导航命令，需要参数
    if cmd_val >= 0x10 and cmd_val <= 0x1F:
        if len(sys.argv) < 5:
            print(f"[ERROR] 命令 {cmd_name} 需要至少 3 个参数: lat lon alt")
            print("格式: COMMAND lat lon alt [speed]")
            sys.exit(1)
        try:
            lat = float(sys.argv[2])
            lon = float(sys.argv[3])
            alt = float(sys.argv[4])
            if len(sys.argv) >= 6:
                spd = float(sys.argv[5])
        except ValueError:
            print("[ERROR] 参数必须是数字")
            sys.exit(1)
            
    send_packet(cmd_val, lat, lon, alt, spd)