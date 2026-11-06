import socket
import threading
import json

HOST = '0.0.0.0'
PORT = 9999

lock = threading.Lock()

connections = {}
users = {} # username -> {conn, addr, groups}
groups = {} # group_name -> {members}

def send_response(conn, status, data):
    payload = {
        "status": status,
        "data": data
    }

    try:
        raw_data = (json.dumps(payload) + "\n").encode('utf-8')
        conn.sendall(raw_data)
    except Exception:
        pass

def authentication(conn):
    with lock:
        if(conn not in connections.keys()):
            send_response(conn, "000", "Not authenticated")
            return False
        return True


def login(conn, addr, username):
    with lock:
        if(username in users.keys()):
            send_response(conn, "010", "Username already used")
        else:
            users[username] = {"conn": conn, "addr": addr, "groups": set({})}
            connections[conn] = username
            send_response(conn, "011", "Logging in successfully")

def listingUsers(conn):
    if(authentication(conn)):
        with lock:
            userlist = [(user, users.get(user).get("addr")) for user in users.keys()]
            send_response(conn, "101", userlist)

def directMessage(conn, target_name, msg):
    if(authentication(conn)):
        with lock:
            if(target_name not in users):
                send_response(conn, "200", "Target not found")
            else:
                uname = connections.get(conn)
                send_response(users.get(target_name).get("conn"), "201", {"from": uname, "addr": users.get(uname).get("addr"), "msg": msg})

def createGroup(conn, group_name):
    if(authentication(conn)):
        with lock:
            if(group_name in groups.keys()):
                send_response(conn, "300", "This group already exist")
            else:
                uname = connections.get(conn)
                groups[group_name] = {"members": {uname}}
                users.get(uname).get("groups").add(group_name)
                print(f"[GROUPS]: create new group: {group_name}, by: {uname}")
                send_response(conn, "301", f"Created {group_name}")

def listingGroups(conn):
    if(authentication(conn)):
            with lock:
                grouplist = [group for group in groups.keys()]
                send_response(conn, "111", grouplist)

def joinGroup(conn, group_name):
    if(authentication(conn)):
        with lock:
            if(group_name not in groups.keys()):
                send_response(conn, "310", "This group does not exist")
            else:
                uname = connections.get(conn)
                if(uname in groups.get(group_name).get("members") or group_name in users.get(uname).get("groups")):
                    send_response(conn, "310", f"User already join group {group_name}")
                else:
                    groups.get(group_name).get("members").add(uname)
                    users.get(uname).get("groups").add(group_name)
                    send_response(conn, "311", f"Joined {group_name}")

def leaveGroup(conn, group_name):
    if(authentication(conn)):
        with lock:
            if(group_name not in groups.keys()):
                send_response(conn, "320", "This group does not exist")
            else:
                uname = connections.get(conn)
                if(uname not in groups.get(group_name).get("members") or group_name not in users.get(uname).get("groups")):
                    send_response(conn, "320", f"User didn't join group {group_name}")
                else:
                    groups.get(group_name).get("members").discard(uname)
                    users.get(uname).get("groups").discard(group_name)
                    send_response(conn, "321", f"Left {group_name}")

def groupMessage(conn, group_name, msg):
    if(authentication(conn)):
        with lock:
            if(group_name not in groups):
                send_response(conn, "330", "This group does not exist")
            else:
                uname = connections.get(conn)
                if(uname not in groups.get(group_name).get("members") or group_name not in users.get(uname).get("groups")):
                    send_response(conn, "330", f"User didn't join group {group_name}")
                else:
                    for target_name in groups.get(group_name).get("members"):
                        if(target_name != uname):
                            send_response(users.get(target_name).get("conn"), "331", {"group": group_name, "from": uname, "addr": users.get(uname).get("addr"), "msg": msg})

def handle_client(conn, addr):
    buffer = ""
    print(f"[NEW CONNECTION] Connected from {addr}")
    try:
        run = True
        while run:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                req = json.loads(line)
                action = req.get("action")
                body = req.get("data", {})

                match action:
                    case "login":
                        login(conn, addr, body.get("username"))
                    case "logout":
                        run = False
                        break
                    case "list_users":
                        listingUsers(conn)
                    case "list_groups":
                        listingGroups(conn)
                    case "direct_message":
                        directMessage(conn, body.get("target_name"), body.get("msg"))
                    case "create_group":
                        createGroup(conn, body.get("group"))
                    case "join_group":
                        joinGroup(conn, body.get("group"))
                    case "leave_group":
                        leaveGroup(conn, body.get("group"))
                    case "group_message":
                        groupMessage(conn, body.get("group"), body.get("msg"))

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        with lock:
            if(conn in connections.keys()):
                uname = connections.pop(conn)
                for group_name in users.get(uname).get("groups"):
                    groups.get(group_name).get("members").discard(uname)
                users.pop(uname)
                print(f"[DISCONNECT] {uname} left.")
        conn.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER STARTED] Running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()