import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, scrolledtext
import socket
import threading
import json
import base64
import os
import queue
import time
from dotenv import load_dotenv

load_dotenv()

DEFAULT_HOST = os.getenv('HOST', 'localhost')
if DEFAULT_HOST == '0.0.0.0':
    DEFAULT_HOST = 'localhost'
DEFAULT_PORT = int(os.getenv('PORT', 9999))


def openFileToString(path):
    with open(path, "rb") as file:
        return file.read().hex()


def stringToFile(data, path):
    with open(path, "wb") as file:
        file.write(bytes.fromhex(data))


def base64StringToFile(data, path):
    with open(path, "wb") as file:
        file.write(base64.b64decode(data))


class ChatRoomView(ttk.Frame):
    """
    Fulfills R6:
    Each chat room (both Private and Group message) must include:
    - a chat window for displaying sent messages and new incoming messages
    - a chat box for sending text messages
    """
    def __init__(self, parent, client_app, room_type, room_name, on_close=None):
        super().__init__(parent)
        self.client_app = client_app
        self.room_type = room_type  # 'private' or 'group'
        self.room_name = room_name  # username or group_name
        self.on_close = on_close
        self.is_popped_out = False
        self.popout_window = None

        self._build_ui()

    def _build_ui(self):
        # 1. Header Frame
        header = ttk.Frame(self, padding=(8, 4))
        header.pack(fill=tk.X, side=tk.TOP)

        icon = "💬" if self.room_type == "private" else "👥"
        title_text = f"{icon} Private Chat: {self.room_name}" if self.room_type == "private" else f"{icon} Group: {self.room_name}"
        self.title_label = ttk.Label(header, text=title_text, font=("Helvetica", 11, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=4)

        self.info_label = ttk.Label(header, text="", font=("Helvetica", 9), foreground="#666666")
        self.info_label.pack(side=tk.LEFT, padx=8)

        if self.on_close:
            btn_close = ttk.Button(header, text="Close Room", width=11, command=self._handle_close)
            btn_close.pack(side=tk.RIGHT, padx=2)

        btn_popout = ttk.Button(header, text="Pop Out ↗", width=10, command=self.toggle_popout)
        btn_popout.pack(side=tk.RIGHT, padx=2)

        # 2. Chat Window (R6: Displaying sent & incoming messages)
        self.chat_window = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 10),
            background="#FFFFFF",
            padx=8,
            pady=8
        )
        self.chat_window.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Styling tags
        self.chat_window.tag_configure("time", foreground="#888888", font=("Segoe UI", 8))
        self.chat_window.tag_configure("you_tag", foreground="#0D47A1", font=("Segoe UI", 10, "bold"))
        self.chat_window.tag_configure("you_text", foreground="#0D47A1")
        self.chat_window.tag_configure("other_tag", foreground="#1B5E20", font=("Segoe UI", 10, "bold"))
        self.chat_window.tag_configure("other_text", foreground="#212121")
        self.chat_window.tag_configure("system", foreground="#616161", font=("Segoe UI", 9, "italic"))
        self.chat_window.tag_configure("file_notice", foreground="#E65100", font=("Segoe UI", 9, "bold"))

        # 3. Chat Box (R6: Sending text messages)
        box_frame = ttk.Frame(self, padding=(6, 6))
        box_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.chat_box = ttk.Entry(box_frame, font=("Segoe UI", 10))
        self.chat_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.chat_box.bind("<Return>", lambda e: self.send_message())

        btn_send = ttk.Button(box_frame, text="Send ✉", width=9, command=self.send_message)
        btn_send.pack(side=tk.LEFT, padx=2)

        btn_attach = ttk.Button(box_frame, text="📎 File", width=8, command=self.send_file)
        btn_attach.pack(side=tk.LEFT, padx=2)

        self.append_system_message(f"Welcome to chat room [{self.room_name}]. Type your message below.")

    def _handle_close(self):
        if self.on_close:
            self.on_close(self)

    def toggle_popout(self):
        if not self.is_popped_out:
            # Create a separate popout window
            self.popout_window = tk.Toplevel(self)
            self.popout_window.title(f"Chat Room - {self.room_name}")
            self.popout_window.geometry("520x450")
            self.popout_window.protocol("WM_DELETE_WINDOW", self.toggle_popout)

            # Move UI into popout window
            self.pack_forget()
            self.reparent_to(self.popout_window)
            self.pack(fill=tk.BOTH, expand=True)
            self.is_popped_out = True
        else:
            if self.popout_window:
                self.pack_forget()
                self.reparent_to(self.master)
                self.pack(fill=tk.BOTH, expand=True)
                self.popout_window.destroy()
                self.popout_window = None
            self.is_popped_out = False

    def reparent_to(self, new_parent):
        # In Tkinter widgets stay inside their master, but packing inside new_parent works when widget is recreated or packed
        pass

    def append_message(self, sender, text, is_you=False, timestamp=None):
        ts = timestamp or time.strftime("%H:%M:%S")
        self.chat_window.configure(state=tk.NORMAL)
        self.chat_window.insert(tk.END, f"[{ts}] ", "time")
        if is_you:
            self.chat_window.insert(tk.END, "You: ", "you_tag")
            self.chat_window.insert(tk.END, f"{text}\n", "you_text")
        else:
            self.chat_window.insert(tk.END, f"{sender}: ", "other_tag")
            self.chat_window.insert(tk.END, f"{text}\n", "other_text")
        self.chat_window.configure(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    def append_system_message(self, text):
        ts = time.strftime("%H:%M:%S")
        self.chat_window.configure(state=tk.NORMAL)
        self.chat_window.insert(tk.END, f"[{ts}] * {text}\n", "system")
        self.chat_window.configure(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    def append_file_notice(self, sender, file_name, is_you=False):
        ts = time.strftime("%H:%M:%S")
        self.chat_window.configure(state=tk.NORMAL)
        self.chat_window.insert(tk.END, f"[{ts}] ", "time")
        who = "You" if is_you else sender
        self.chat_window.insert(tk.END, f"📁 {who} shared file: {file_name}\n", "file_notice")
        self.chat_window.configure(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    def send_message(self):
        text = self.chat_box.get().strip()
        if not text:
            return
        self.chat_box.delete(0, tk.END)

        if self.room_type == "private":
            self.client_app.send_request("direct_message", {
                "target_name": self.room_name,
                "msg": text
            })
            self.append_message("You", text, is_you=True)
        elif self.room_type == "group":
            self.client_app.send_request("group_message", {
                "group": self.room_name,
                "msg": text
            })
            self.append_message("You", text, is_you=True)

    def send_file(self):
        filepath = filedialog.askopenfilename(title="Select File to Send")
        if not filepath:
            return
        file_name = os.path.basename(filepath)
        try:
            file_data = openFileToString(filepath)
            if self.room_type == "private":
                self.client_app.send_request("direct_send_file", {
                    "target_name": self.room_name,
                    "file_name": file_name,
                    "data": file_data
                })
                self.append_file_notice("You", file_name, is_you=True)
            elif self.room_type == "group":
                self.client_app.send_request("group_send_file", {
                    "group": self.room_name,
                    "file_name": file_name,
                    "data": file_data
                })
                self.append_file_notice("You", file_name, is_you=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file: {e}")


class NetworkSocketGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetworkSocket Chat Application")
        self.root.geometry("1000x680")
        self.root.minsize(800, 500)

        self.sock = None
        self.is_connected = False
        self.username = None
        self.msg_queue = queue.Queue()
        self.retrive_file_queue = {}

        # Tracking rooms: key -> ChatRoomView
        # key format: "private:<username>" or "group:<group_name>"
        self.chat_rooms = {}

        # Set styling
        self._init_styles()

        # Build Main Frames
        self.login_frame = ttk.Frame(self.root, padding=30)
        self.main_frame = ttk.Frame(self.root)

        self._build_login_screen()
        self._build_main_dashboard()

        self.login_frame.pack(fill=tk.BOTH, expand=True)

        # Polling message queue
        self.root.after(50, self.process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _init_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10, "bold"), foreground="#333333")

    # ==========================================
    # LOGIN SCREEN
    # ==========================================
    def _build_login_screen(self):
        container = ttk.Frame(self.login_frame, padding=20)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        lbl_title = ttk.Label(container, text="🌐 NetworkSocket Chat", font=("Segoe UI", 18, "bold"), foreground="#1565C0")
        lbl_title.pack(pady=(0, 20))

        form_frame = ttk.Frame(container)
        form_frame.pack(fill=tk.X, pady=10)

        ttk.Label(form_frame, text="Server Host:").grid(row=0, column=0, sticky=tk.W, pady=6, padx=4)
        self.entry_host = ttk.Entry(form_frame, width=28)
        self.entry_host.insert(0, DEFAULT_HOST)
        self.entry_host.grid(row=0, column=1, pady=6, padx=4)

        ttk.Label(form_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=6, padx=4)
        self.entry_port = ttk.Entry(form_frame, width=28)
        self.entry_port.insert(0, str(DEFAULT_PORT))
        self.entry_port.grid(row=1, column=1, pady=6, padx=4)

        ttk.Label(form_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=6, padx=4)
        self.entry_username = ttk.Entry(form_frame, width=28)
        self.entry_username.grid(row=2, column=1, pady=6, padx=4)
        self.entry_username.bind("<Return>", lambda e: self.perform_login())

        self.lbl_login_status = ttk.Label(container, text="", foreground="red")
        self.lbl_login_status.pack(pady=4)

        self.btn_connect = ttk.Button(container, text="Connect & Login", command=self.perform_login, width=24)
        self.btn_connect.pack(pady=12)

    def perform_login(self):
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()
        username = self.entry_username.get().strip()

        if not host or not port_str or not username:
            self.lbl_login_status.config(text="Please fill in all fields.")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.lbl_login_status.config(text="Port must be a valid number.")
            return

        self.lbl_login_status.config(text="Connecting to server...", foreground="blue")
        self.btn_connect.config(state=tk.DISABLED)

        # Connect socket in thread or quick connect
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
        except Exception as e:
            self.lbl_login_status.config(text=f"Connection failed: {e}", foreground="red")
            self.btn_connect.config(state=tk.NORMAL)
            return

        # Start background receive thread
        threading.Thread(target=self.receive_handler, daemon=True).start()

        # Send login request
        self.username = username
        self.send_request("login", {"username": username})

    # ==========================================
    # MAIN DASHBOARD SCREEN
    # ==========================================
    def _build_main_dashboard(self):
        # Top Bar
        top_bar = ttk.Frame(self.main_frame, padding=(10, 6), relief=tk.RIDGE)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        self.lbl_user_info = ttk.Label(top_bar, text="User: -", font=("Segoe UI", 10, "bold"), foreground="#1565C0")
        self.lbl_user_info.pack(side=tk.LEFT, padx=6)

        btn_logout = ttk.Button(top_bar, text="Disconnect / Logout", width=18, command=self.on_logout)
        btn_logout.pack(side=tk.RIGHT, padx=6)

        btn_refresh = ttk.Button(top_bar, text="🔄 Refresh All", width=14, command=self.refresh_all)
        btn_refresh.pack(side=tk.RIGHT, padx=6)

        # Main Workspace PanedWindow
        paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Left Sidebar (Users & Groups)
        sidebar = ttk.Frame(paned, width=320, padding=4)
        paned.add(sidebar, weight=1)

        # --- Sidebar Section 1: Online Users (R4) ---
        user_sec = ttk.LabelFrame(sidebar, text="👥 Online Users (R4)", padding=6)
        user_sec.pack(fill=tk.BOTH, expand=True, pady=4)

        user_list_frame = ttk.Frame(user_sec)
        user_list_frame.pack(fill=tk.BOTH, expand=True)

        user_scroll = ttk.Scrollbar(user_list_frame)
        user_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.users_listbox = tk.Listbox(
            user_list_frame,
            yscrollcommand=user_scroll.set,
            font=("Segoe UI", 9),
            selectmode=tk.SINGLE,
            exportselection=False
        )
        self.users_listbox.pack(fill=tk.BOTH, expand=True)
        user_scroll.config(command=self.users_listbox.yview)
        self.users_listbox.bind("<Double-Button-1>", lambda e: self.open_selected_user_chat())

        user_btn_frame = ttk.Frame(user_sec)
        user_btn_frame.pack(fill=tk.X, pady=(4, 0))

        btn_dm = ttk.Button(user_btn_frame, text="💬 Start Private Chat (R5)", command=self.open_selected_user_chat)
        btn_dm.pack(fill=tk.X, pady=2)

        # --- Sidebar Section 2: Groups (R8, R9, R10) ---
        group_sec = ttk.LabelFrame(sidebar, text="🏛 Groups (R8-R11)", padding=6)
        group_sec.pack(fill=tk.BOTH, expand=True, pady=4)

        group_list_frame = ttk.Frame(group_sec)
        group_list_frame.pack(fill=tk.BOTH, expand=True)

        group_scroll = ttk.Scrollbar(group_list_frame)
        group_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.groups_listbox = tk.Listbox(
            group_list_frame,
            yscrollcommand=group_scroll.set,
            font=("Segoe UI", 9),
            selectmode=tk.SINGLE,
            exportselection=False
        )
        self.groups_listbox.pack(fill=tk.BOTH, expand=True)
        group_scroll.config(command=self.groups_listbox.yview)
        self.groups_listbox.bind("<Double-Button-1>", lambda e: self.open_selected_group_chat())

        grp_btn_frame = ttk.Frame(group_sec)
        grp_btn_frame.pack(fill=tk.X, pady=(4, 0))

        row1 = ttk.Frame(grp_btn_frame)
        row1.pack(fill=tk.X, pady=1)
        btn_create_grp = ttk.Button(row1, text="➕ Create (R8)", command=self.prompt_create_group)
        btn_create_grp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        btn_join_grp = ttk.Button(row1, text="🚪 Join (R10)", command=self.join_selected_group)
        btn_join_grp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        row2 = ttk.Frame(grp_btn_frame)
        row2.pack(fill=tk.X, pady=1)
        btn_open_grp = ttk.Button(row2, text="👥 Open Room (R5)", command=self.open_selected_group_chat)
        btn_open_grp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        btn_leave_grp = ttk.Button(row2, text="Leave", command=self.leave_selected_group)
        btn_leave_grp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        # --- Sidebar Section 3: AI & File Tools ---
        ai_sec = ttk.LabelFrame(sidebar, text="⚡ AI & Utilities", padding=6)
        ai_sec.pack(fill=tk.X, pady=4)

        ai_row = ttk.Frame(ai_sec)
        ai_row.pack(fill=tk.X)
        btn_ask_ai = ttk.Button(ai_row, text="🤖 Ask Gemini", command=self.prompt_ask_gemini)
        btn_ask_ai.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        btn_gen_img = ttk.Button(ai_row, text="🎨 Image Gen", command=self.prompt_generate_image)
        btn_gen_img.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        btn_sum_pdf = ttk.Button(ai_row, text="📄 PDF Summary", command=self.prompt_summarize_pdf)
        btn_sum_pdf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        # Right Area: Chat Rooms Notebook (R5: Each chat has its own chat room)
        chat_container = ttk.Frame(paned, padding=4)
        paned.add(chat_container, weight=3)

        self.notebook = ttk.Notebook(chat_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Default Lobby / System Tab
        self.lobby_frame = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.lobby_frame, text="🏠 Lobby & Notifications")

        self.lobby_log = scrolledtext.ScrolledText(
            self.lobby_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 10),
            background="#FBFBFB",
            padx=8,
            pady=8
        )
        self.lobby_log.pack(fill=tk.BOTH, expand=True)
        self.lobby_log.tag_configure("info", foreground="#1565C0")
        self.lobby_log.tag_configure("warn", foreground="#C62828", font=("Segoe UI", 10, "bold"))
        self.lobby_log.tag_configure("success", foreground="#2E7D32", font=("Segoe UI", 10, "bold"))
        self.log_lobby("Welcome to NetworkSocket Chat! Use the sidebar to start a private chat or join a group.")

    def log_lobby(self, message, tag="info"):
        ts = time.strftime("%H:%M:%S")
        self.lobby_log.configure(state=tk.NORMAL)
        self.lobby_log.insert(tk.END, f"[{ts}] {message}\n", tag)
        self.lobby_log.configure(state=tk.DISABLED)
        self.lobby_log.see(tk.END)

    # ==========================================
    # ROOM MANAGEMENT (R5 & R6)
    # ==========================================
    def get_or_create_room(self, room_type, room_name):
        """
        R5: Each chat between clients (both Private and Group message) must have its own chat room.
        R6: Each chat room must include a chat box and chat window.
        """
        key = f"{room_type}:{room_name}"
        if key in self.chat_rooms:
            room_view = self.chat_rooms[key]
            # Switch notebook tab to this room
            try:
                self.notebook.select(room_view)
            except Exception:
                pass
            return room_view

        # Create new ChatRoomView
        room_view = ChatRoomView(
            self.notebook,
            client_app=self,
            room_type=room_type,
            room_name=room_name,
            on_close=lambda r: self.close_room(key)
        )
        self.chat_rooms[key] = room_view

        tab_title = f"💬 {room_name}" if room_type == "private" else f"👥 {room_name}"
        self.notebook.add(room_view, text=tab_title)
        self.notebook.select(room_view)
        return room_view

    def close_room(self, key):
        if key in self.chat_rooms:
            room_view = self.chat_rooms.pop(key)
            self.notebook.forget(room_view)
            room_view.destroy()

    def open_selected_user_chat(self):
        sel = self.users_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select User", "Please select a user from the Online Users list.")
            return
        entry = self.users_listbox.get(sel[0])
        # Entry format: username@ip:port
        target_name = entry.split("@")[0].strip()
        if target_name == self.username:
            messagebox.showinfo("Private Chat", "You cannot open a private chat with yourself.")
            return

        room = self.get_or_create_room("private", target_name)
        room.chat_box.focus_set()

    def open_selected_group_chat(self):
        sel = self.groups_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Group", "Please select a group from the Groups list.")
            return
        entry = self.groups_listbox.get(sel[0])
        group_name = entry.split(" ")[0].strip()
        room = self.get_or_create_room("group", group_name)
        room.chat_box.focus_set()

    # ==========================================
    # SIDEBAR ACTIONS
    # ==========================================
    def refresh_all(self):
        self.send_request("list_users", None)
        self.send_request("list_groups", None)

    def prompt_create_group(self):
        group_name = simpledialog.askstring("Create Group (R8)", "Enter new group name:", parent=self.root)
        if group_name and group_name.strip():
            self.send_request("create_group", {"group": group_name.strip()})

    def join_selected_group(self):
        sel = self.groups_listbox.curselection()
        if not sel:
            messagebox.showinfo("Join Group", "Please select a group to join.")
            return
        entry = self.groups_listbox.get(sel[0])
        group_name = entry.split(" ")[0].strip()
        self.send_request("join_group", {"group": group_name})

    def leave_selected_group(self):
        sel = self.groups_listbox.curselection()
        if not sel:
            messagebox.showinfo("Leave Group", "Please select a group to leave.")
            return
        entry = self.groups_listbox.get(sel[0])
        group_name = entry.split(" ")[0].strip()
        self.send_request("leave_group", {"group": group_name})

    def prompt_ask_gemini(self):
        prompt = simpledialog.askstring("Ask Gemini AI", "Enter question or prompt for Gemini:", parent=self.root)
        if prompt and prompt.strip():
            self.log_lobby(f"🤖 [Gemini Query]: {prompt.strip()}")
            self.send_request("ask_gemini", {"prompt": prompt.strip()})

    def prompt_generate_image(self):
        prompt = simpledialog.askstring("Generate Image", "Enter image prompt for Gemini:", parent=self.root)
        if not prompt or not prompt.strip():
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            title="Save Generated Image As"
        )
        if not save_path:
            return
        file_name = os.path.basename(save_path)
        self.retrive_file_queue[file_name] = save_path
        self.log_lobby(f"🎨 Requesting image generation: '{prompt.strip()}' -> saving to {file_name}")
        self.send_request("generate_image", {"file_name": file_name, "prompt": prompt.strip()})

    def prompt_summarize_pdf(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("PDF Document", "*.pdf"), ("All Files", "*.*")],
            title="Select PDF Document to Summarize"
        )
        if not filepath:
            return
        try:
            file_data = openFileToString(filepath)
            self.log_lobby(f"📄 Sending '{os.path.basename(filepath)}' for AI summarization...")
            self.send_request("pdf_sumarize", {"data": file_data})
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read PDF: {e}")

    # ==========================================
    # NETWORK SOCKET & DISPATCH
    # ==========================================
    def send_request(self, action, data):
        if not self.sock or not self.is_connected:
            return
        payload = {"action": action, "data": data}
        try:
            raw = (json.dumps(payload) + "\n").encode('utf-8')
            self.sock.sendall(raw)
        except Exception as e:
            self.log_lobby(f"Send error: {e}", tag="warn")

    def receive_handler(self):
        buffer = ""
        while self.is_connected:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    self.msg_queue.put({"status": "DISCONNECTED", "data": "Server closed connection."})
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    res = json.loads(line)
                    self.msg_queue.put(res)
            except Exception as e:
                self.msg_queue.put({"status": "DISCONNECTED", "data": str(e)})
                break

    def process_queue(self):
        while not self.msg_queue.empty():
            try:
                res = self.msg_queue.get_nowait()
                self.handle_server_message(res)
            except queue.Empty:
                break
        self.root.after(50, self.process_queue)

    def handle_server_message(self, res):
        status = str(res.get("status"))
        data = res.get("data")

        if status == "DISCONNECTED":
            self.is_connected = False
            self.log_lobby("Server disconnected.", tag="warn")
            messagebox.showwarning("Disconnected", "Disconnected from server.")
            return

        match status:
            case "010":  # Login failed - username taken
                self.lbl_login_status.config(text=f"Login failed: {data}", foreground="red")
                self.btn_connect.config(state=tk.NORMAL)
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                self.is_connected = False

            case "011":  # Login successful
                self.login_frame.pack_forget()
                self.main_frame.pack(fill=tk.BOTH, expand=True)
                self.lbl_user_info.config(text=f"Logged in as: {self.username} (Connected)")
                self.log_lobby(f"Successfully logged in as '{self.username}'.", tag="success")
                self.refresh_all()

            case "101":  # Online Users list (R4)
                self.users_listbox.delete(0, tk.END)
                raw_users = data or []
                for item in raw_users:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        uname = item[0]
                        addr = item[1]
                        self.users_listbox.insert(tk.END, f"{uname}@{addr[0]}:{addr[1]}")
                    else:
                        self.users_listbox.insert(tk.END, str(item))

            case "111":  # Groups list (R9)
                self.groups_listbox.delete(0, tk.END)
                raw_groups = data or []
                for item in raw_groups:
                    if isinstance(item, dict):
                        g_name = item.get("group")
                        members = ", ".join(item.get("members", []))
                        self.groups_listbox.insert(tk.END, f"{g_name} (Members: {members})")
                    else:
                        self.groups_listbox.insert(tk.END, str(item))

            case "200":  # Direct message error
                self.log_lobby(f"Private message error: {data}", tag="warn")

            case "201":  # Incoming Direct Message (R5, R6, R7)
                # data: {"from": ..., "addr": ..., "msg": ...}
                sender = data.get("from")
                msg = data.get("msg")
                room = self.get_or_create_room("private", sender)
                room.append_message(sender, msg, is_you=False)

            case "300":  # Group creation error
                messagebox.showerror("Group Error", str(data))

            case "301":  # Group created (R8)
                self.log_lobby(f"Group created: {data}", tag="success")
                self.send_request("list_groups", None)

            case "310":  # Group join error
                messagebox.showwarning("Join Group", str(data))

            case "311":  # Group joined (R10)
                self.log_lobby(f"Joined group: {data}", tag="success")
                self.send_request("list_groups", None)

            case "320":  # Group leave error
                messagebox.showwarning("Leave Group", str(data))

            case "321":  # Group left
                self.log_lobby(f"Left group: {data}", tag="info")
                self.send_request("list_groups", None)

            case "330":  # Group message error
                self.log_lobby(f"Group message error: {data}", tag="warn")

            case "331":  # Incoming Group Message (R5, R6, R11)
                # data: {"group": ..., "from": ..., "addr": ..., "msg": ...}
                group_name = data.get("group")
                sender = data.get("from")
                msg = data.get("msg")
                room = self.get_or_create_room("group", group_name)
                room.append_message(sender, msg, is_you=False)

            case "401":  # Incoming direct file notification
                sender = data.get("from")
                file_name = data.get("file_name")
                self.log_lobby(f"📁 {sender} sent file '{file_name}'. Use Retrieve to save it.", tag="info")
                if f"private:{sender}" in self.chat_rooms:
                    self.chat_rooms[f"private:{sender}"].append_file_notice(sender, file_name, is_you=False)
                # Ask user if they wish to download
                if messagebox.askyesno("File Received", f"User {sender} sent file '{file_name}'. Do you want to download it now?"):
                    save_path = filedialog.asksaveasfilename(initialfile=file_name)
                    if save_path:
                        self.retrive_file_queue[file_name] = save_path
                        self.send_request("direct_retrieve_file", {"file_name": file_name})

            case "411" | "441":  # File downloaded content
                file_name = data.get("file_name")
                hex_data = data.get("data")
                if file_name in self.retrive_file_queue:
                    target_path = self.retrive_file_queue.pop(file_name)
                    stringToFile(hex_data, target_path)
                    self.log_lobby(f"✅ Saved file to '{target_path}'", tag="success")
                    messagebox.showinfo("File Saved", f"File '{file_name}' saved successfully!")

            case "431":  # Incoming group file notification
                group = data.get("group")
                sender = data.get("from")
                file_name = data.get("file_name")
                self.log_lobby(f"📁 [Group {group}] {sender} sent file '{file_name}'.", tag="info")
                if f"group:{group}" in self.chat_rooms:
                    self.chat_rooms[f"group:{group}"].append_file_notice(sender, file_name, is_you=False)

            case "501":  # Gemini Text Response
                self.log_lobby(f"🤖 [Gemini Answer]:\n{data}", tag="success")
                messagebox.showinfo("Gemini Response", str(data))

            case "511":  # Gemini Image Response
                file_name = data.get("file_name")
                b64_data = data.get("data")
                if file_name in self.retrive_file_queue:
                    target_path = self.retrive_file_queue.pop(file_name)
                    base64StringToFile(b64_data, target_path)
                    self.log_lobby(f"🎨 Gemini image saved to '{target_path}'", tag="success")
                    messagebox.showinfo("Image Generated", f"Image generated and saved to {target_path}!")

            case "521":  # Gemini PDF Summary Response
                self.log_lobby(f"📄 [Gemini PDF Summary]:\n{data}", tag="success")
                messagebox.showinfo("PDF Summary", str(data))

            case _:
                self.log_lobby(f"[Server]: {data}")

    def on_logout(self):
        if self.is_connected:
            self.send_request("logout", None)
            try:
                self.sock.close()
            except Exception:
                pass
        self.is_connected = False
        self.main_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.btn_connect.config(state=tk.NORMAL)
        self.lbl_login_status.config(text="")

    def on_exit(self):
        if self.is_connected:
            try:
                self.send_request("logout", None)
                self.sock.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NetworkSocketGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
