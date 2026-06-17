import socket
import time

def send_sms(host, port, phone, message):
    token_path = r"C:\Users\user\.emulator_console_auth_token"
    with open(token_path, "r") as f:
        token = f.read().strip()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((host, port))
        time.sleep(0.5)

        banner = b""
        while True:
            try:
                chunk = s.recv(4096)
                banner += chunk
                if b"OK" in chunk:
                    break
            except socket.timeout:
                break

        print("Banner:", banner.decode("utf-8", errors="ignore").strip())

        s.sendall(f"auth {token}\n".encode("utf-8"))
        time.sleep(0.3)
        auth_resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
        print("Auth:", auth_resp)

        s.sendall(f"sms send {phone} {message}\n".encode("utf-8"))
        time.sleep(0.3)
        sms_resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
        print("SMS:", sms_resp)

send_sms("127.0.0.1", 5554, "01000000000", "[Web] 인증번호 [123456]입니다.")
