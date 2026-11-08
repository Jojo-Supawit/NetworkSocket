import socket
import threading
import json
import base64
import sys

if "--gui" in sys.argv:
    from gui_client import main as gui_main
    gui_main()
    sys.exit(0)

HOST = "localhost"
PORT = 9999

lock = threading.Lock()

is_logged_in = False
is_connected = True
login_response_event = threading.Event()

retriveFileQueue = {}

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

def openFileToString(path):
    output = ""
    with open(path, "rb") as file:
        output += file.read().hex()
    return output

def stringToFile(data, path):
    with open(path, "wb") as file:
        file.write(bytes.fromhex(data))

def base64StringToFile(data, path):
    with open(path, "wb") as file:
        file.write(base64.b64decode(data))

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
                        formatted = []
                        for item in raw_list:
                            if isinstance(item, dict):
                                members_str = ", ".join(item.get("members", []))
                                formatted.append(f"{item.get('group')} (members: {members_str})")
                            else:
                                formatted.append(str(item))
                        print(f"\n[Server]: {', '.join(formatted)}\n> ", end="", flush=True)
                    case "121":
                        raw_list = res.get("data", [])
                        print(f"\n[Server]: {', '.join(raw_list)}\n> ", end="", flush=True)
                    # case "130":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "131":
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
                    # case "340":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "341":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "341r":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "331":
                        data = res.get('data', {})
                        print(f"\n[(Group: {data.get("group")}): {data.get("from")}@{getAddressAndPort(data.get("addr"))}]: {data.get("msg")}\n> ", end="", flush=True)
                    # case "400":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "401":
                        data = res.get('data', {})
                        print(f"\n[{data.get("from")}@{getAddressAndPort(data.get("addr"))}]: Sent file: {data.get("file_name")}\n> ", end="", flush=True)
                    # case "401r":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "410":
                        data = res.get('data', {})
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                retriveFileQueue.pop(data.get("file_name"))
                        print(f"\n[Server]: {data.get("msg")}\n> ", end="", flush=True)   
                    case "411":
                        data = res.get('data', {})
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                stringToFile(data.get("data"), retriveFileQueue.get(data.get("file_name")))   
                                retriveFileQueue.pop(data.get("file_name")) 
                                print(f"\n[Client]: Saved {data.get("file_name")}\n> ", end="", flush=True)         
                    # case "420":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "421":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)  
                    case "431":
                        data = res.get('data', {})
                        print(f"\n[(Group: {data.get("group")}): {data.get("from")}@{getAddressAndPort(data.get("addr"))}]: Sent file: {data.get("file_name")}\n> ", end="", flush=True)
                    # case "431r":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "440":
                        data = res.get('data', {})
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                retriveFileQueue.pop(data.get("file_name"))
                        print(f"\n[Server]: {data.get("msg")}\n> ", end="", flush=True)   
                    case "441":
                        data = res.get('data', {})
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                stringToFile(data.get("data"), retriveFileQueue.get(data.get("file_name")))     
                                retriveFileQueue.pop(data.get("file_name"))
                                print(f"\n[Client]: Saved {data.get("file_name")}\n> ", end="", flush=True)
                    # case "450":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)
                    # case "451":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)  
                    # case "500":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)  
                    case "501":
                        print(f"\n[Gemini]: {res.get('data', '')}\n> ", end="", flush=True)
                    case "510":
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                retriveFileQueue.pop(data.get("file_name"))
                        print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)  
                    case "511":
                        data = res.get('data', {})
                        with lock:
                            if(data.get("file_name") in retriveFileQueue.keys()):
                                base64StringToFile(data.get("data"), retriveFileQueue.get(data.get("file_name")))
                                retriveFileQueue.pop(data.get("file_name"))
                                print(f"\n[Client]: Saved {data.get("file_name")}\n> ", end="", flush=True)
                    # case "520":
                    #     print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)  
                    case "521":
                        print(f"\n[Gemini summarize]: {res.get('data', '')}\n> ", end="", flush=True)
                    case _:
                        print(f"\n[Server]: {res.get('data', '')}\n> ", end="", flush=True)

        except Exception:
            is_connected = False
            login_response_event.set()
            break

def main():
    raw_host = input("HOST (default localhost) = ").strip()
    HOST = raw_host if raw_host else "localhost"
    raw_port = input("PORT (default 9999) = ").strip()
    PORT = int(raw_port) if raw_port else 9999
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

    current_room = {"type": None, "name": None}

    while is_connected:
        try:
            prompt_str = "> "
            if current_room["type"] == "private":
                prompt_str = f"[Room 💬 {current_room['name']}] > "
            elif current_room["type"] == "group":
                prompt_str = f"[Room 👥 {current_room['name']}] > "

            cmd_input = input(prompt_str).strip()
            if not cmd_input:
                continue
            if cmd_input.lower() == "/quit":
                send_request(sock, "logout", None)
                break

            # If not starting with '/', send directly to active room
            if not cmd_input.startswith("/"):
                if current_room["type"] == "private":
                    send_request(sock, "direct_message", {"target_name": current_room["name"], "msg": cmd_input})
                    print(f"[You -> {current_room['name']}]: {cmd_input}")
                elif current_room["type"] == "group":
                    send_request(sock, "group_message", {"group": current_room["name"], "msg": cmd_input})
                    print(f"[(Group: {current_room['name']}): You]: {cmd_input}")
                else:
                    print("Not in any room. Use /chat <username> or /group <group_name> to enter a room, or type a command starting with '/'.")
                continue

            parts = cmd_input.split(" ")
            command = parts[0]

            try:
                match command:
                    case "/chat":
                        current_room = {"type": "private", "name": parts[1]}
                        print(f"--- Entered Private Chat Room with {parts[1]} (R5, R6) ---")
                        print("Type messages directly to send. Type /leave to exit back to lobby.")
                    case "/group":
                        current_room = {"type": "group", "name": parts[1]}
                        print(f"--- Entered Group Chat Room: {parts[1]} (R5, R6) ---")
                        print("Type messages directly to send. Type /leave to exit back to lobby.")
                    case "/leave":
                        if current_room["type"] is not None:
                            print(f"--- Left {current_room['name']} room back to main lobby ---")
                            current_room = {"type": None, "name": None}
                        elif len(parts) > 1:
                            send_request(sock, "leave_group", {"group": parts[1]})
                        else:
                            print("Not in a room. To leave a group from server: /leave <group_name>")
                    case "/list_users":
                        send_request(sock, "list_users", None)
                    case "/list_groups":
                        send_request(sock, "list_groups", None)
                    case "/list_files":
                        send_request(sock, "list_direct_files", None)
                    case "/list_group_files":
                        send_request(sock, "list_group_files", {"group": parts[1]})
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
                    case "/group_message":
                        send_request(sock, "group_message", {"group": parts[1], "msg": parts[2]})
                    case "/gm":
                        send_request(sock, "group_message", {"group": parts[1], "msg": parts[2]})
                    case "/remove_group":
                        send_request(sock, "remove_group", {"group": parts[1]})
                    case "/send_file":
                        file_data = openFileToString(parts[3])
                        send_request(sock, "direct_send_file", {"target_name": parts[1], "file_name": parts[2], "data": file_data})
                    case "/retrieve_file":
                        with lock:
                            retriveFileQueue[parts[1]] = parts[2]
                        send_request(sock, "direct_retrieve_file", {"file_name": parts[1]})
                    case "/reject_file":
                        send_request(sock, "direct_reject_file", {"file_name": parts[1]})
                    case "/send_group_file":
                        file_data = openFileToString(parts[3])
                        send_request(sock, "group_send_file", {"group": parts[1], "file_name": parts[2], "data": file_data})
                    case "/retrieve_group_file":
                        with lock:
                            retriveFileQueue[parts[2]] = parts[3]
                        send_request(sock, "group_retrieve_file", {"group": parts[1], "file_name": parts[2]})
                    case "/remove_group_file":
                        send_request(sock, "group_remove_file", {"group": parts[1], "file_name": parts[2]})
                    case "/ask_gemini":
                        send_request(sock, "ask_gemini", {"prompt": " ".join(parts[1:])})
                    case "/generate_image": # file_name path prompt
                        with lock:
                            retriveFileQueue[parts[1]] = parts[2]
                        send_request(sock, "generate_image", {"file_name": parts[1], "prompt": " ".join(parts[3:])})
                    case "/pdf_sumarize":
                        file_data = openFileToString(parts[1])
                        send_request(sock, "pdf_sumarize", {"data": file_data})
                    case _:
                        print(f"Unknown command: {command}")
            except:
                print(f"Command {command} arguments miss match")

        except (KeyboardInterrupt, EOFError):
            break

    sock.close()

if __name__ == "__main__":
    main()
