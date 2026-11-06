import socket
import threading
import json

HOST = "localhost"
PORT = 9999

is_logged_in = False
is_connected = True
login_response_event = threading.Event()

def getAddressAndPort(addr):
    return f"{addr[0]}:{addr[1]}"

def send_request(conn, action, data):
    payload = {
        "action": action,
        "data": data
    }
    try:
        raw_data = (json.dumps(payload) + "\n").encode('utf-8')
        conn.sendall(raw_data)
    except Exception:
        pass

def receive_messages_handler(sock):
    global is_logged_in, is_connected
    buffer = ""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                print("\n[SERVER DISCONNECTED]")
                is_connected = False
                login_response_event.set()
                break
            
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                
                res = json.loads(line)
                status = res.get("status")

                match status:
                    # case "000":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "010":
                        is_logged_in = False
                        print(f"\n[Server]: {res.get('data', '')}")
                        login_response_event.set()
                    case "011":
                        is_logged_in = True
                        print(f"\n[Server]: {res.get('data', '')}")
                        login_response_event.set()
                    case "101":
                        raw_list = res.get("data", [])
                        users = [f"{item[0]}@{getAddressAndPort(item[1])}" for item in raw_list]
                        print(f"\n[Server]: {', '.join(users)}\n> ", end="", flush=True)
                    case "111":
                        raw_list = res.get("data", [])
                        print(f"\n[Server]: {', '.join(raw_list)}\n> ", end="", flush=True)
                    # case "200":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "201":
                        data = res.get('data', {})
                        print(f"\n[{data.get("from")}@{getAddressAndPort(data.get("addr"))}]: {data.get("msg")}\n> ", end="", flush=True)
                    # case "300":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "301":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "310":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "311":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "320":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "321":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "330":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "331":
                        data = res.get('data', {})
                        print(f"\n[(Group: {data.get("group")}): {data.get("from")}@{getAddressAndPort(data.get("addr"))}]: {data.get("msg")}\n> ", end="", flush=True)
                    case _:
                        print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
        except Exception:
            is_connected = False
            login_response_event.set()
            break

def main():
    HOST = input("HOST=")
    PORT = int(input("PORT="))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    threading.Thread(target=receive_messages_handler, args=(sock,), daemon=True).start()

    while not is_logged_in:
        if not is_connected:
            return
        username = input("Enter your username: ").strip()
        if not username:
            continue
        login_response_event.clear()
        send_request(sock, "login", {"username": username})
        login_response_event.wait()

    while is_connected:
        try:
            cmd_input = input("> ").strip()
            if not cmd_input:
                continue
            if cmd_input.lower() == "/quit":
                send_request(sock, "logout", None)
                break

            parts = cmd_input.split(" ")
            command = parts[0]

            match command:
                case "/list_users":
                    send_request(sock, "list_users", None)
                case "/list_groups":
                    send_request(sock, "list_groups", None)
                case "/direct_message":
                    send_request(sock, "direct_message", {"target_name": parts[1], "msg": parts[2]})
                case "/dm":
                    send_request(sock, "direct_message", {"target_name": parts[1], "msg": parts[2]})
                case "/create_group":
                    send_request(sock, "create_group", {"group": parts[1]})
                case "/join_group":
                    send_request(sock, "join_group", {"group": parts[1]})
                case "/join":
                    send_request(sock, "join_group", {"group": parts[1]})
                case "/leave_group":
                    send_request(sock, "leave_group", {"group": parts[1]})
                case "/leave":
                    send_request(sock, "leave_group", {"group": parts[1]})
                case "/group_message":
                    send_request(sock, "group_message", {"group": parts[1], "msg": parts[2]})
                case "/gm":
                    send_request(sock, "group_message", {"group": parts[1], "msg": parts[2]})
                case _:
                    print(f"Unknown command: {command}")

        except (KeyboardInterrupt, EOFError):
            break

    sock.close()

if __name__ == "__main__":
    main()
