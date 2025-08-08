import socket
from pathlib import Path
import platform
from zeroconf import Zeroconf, ServiceInfo

SERVER_DOMAIN = "printer-server.local"

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"



def get_local_ip():
    """Find the local IP address on the LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We don't actually connect to Google, just use routing table
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def setup_domain(): 
    ip = get_local_ip()
    desc = {'path': '/'}  # Extra info (can be used by clients)

    info = ServiceInfo(
        "_http._tcp.local.",
        "Printer Server._http._tcp.local.",  # Service name
        addresses=[socket.inet_aton(ip)],
        port=8088,
        properties=desc,
        server=SERVER_DOMAIN
    )

    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    return zeroconf, info, ip



# def get_hosts_file_path():
#     if platform.system() == "Windows":
#         return Path(r"C:\Windows\System32\drivers\etc\hosts")
#     else:
#         return Path("/etc/hosts")

# def ensure_domain_mapping(domain, ip):
#     hosts_file = get_hosts_file_path()

#     # Read current content
#     try:
#         content = hosts_file.read_text().splitlines()
#     except PermissionError:
#         return {"error": "Permission denied. Run server as admin/root."}

#     # Check if already correct
#     for line in content:
#         if domain in line:
#             if f"{ip}" in line:
#                 return {"status": "ok", "message": f"{domain} is already mapped to {ip}"}
#             else:
#                 # Replace existing wrong mapping
#                 content = [l for l in content if domain not in l]
#                 content.append(f"{ip} {domain}")
#                 hosts_file.write_text("\n".join(content) + "\n")
#                 return {"status": "updated", "message": f"Updated mapping for {domain} to {ip}"}

#     # Not found → add it
#     content.append(f"{ip} {domain}")
#     hosts_file.write_text("\n".join(content) + "\n")
#     return {"status": "added", "message": f"Added mapping for {domain} to {ip}"}

# async def check_host():
#     server_ip = get_lan_ip()
#     server_ip = get_lan_ip()

#     try:
#         resolved_ip = socket.gethostbyname(SERVER_DOMAIN)
#     except socket.gaierror:
#         resolved_ip = None

#     if resolved_ip != server_ip:
#         result = ensure_domain_mapping(SERVER_DOMAIN, server_ip)
#         return {**result, "server_ip": server_ip, "resolved_ip": resolved_ip}

#     return {"status": "ok", "message": f"{SERVER_DOMAIN} is correctly mapped", "server_ip": server_ip}
