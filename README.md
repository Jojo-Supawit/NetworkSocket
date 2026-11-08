# NetworkSocket — Client-Side Command Guide

## What is NetworkSocket?

**NetworkSocket** is a lightweight, threaded TCP chat / file‑sharing server for **localhost:9999**. It lets multiple users:
- Log in with a username and password.
- List users, groups, direct files, and group files.
- Send / retrieve / reject files between users.
- Direct message another user.
- Manage groups (create, join, leave, group messages).
- Generate images and summarize PDFs via Google Gemini AI.

The most recent commit adds **AI features** (Gemini ask‑model, image generation, PDF summarization).

---

## Quick start

```bash
# 1. Clone the repo (or copy the three files)
git clone https://github.com/Jojo-Supawit/NetworkSocket.git
cd NetworkSocket

# 2. Create .env.example and edit it:
cat > .env.example <<'EOF'
HOST=localhost
PORT=9999
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
EOF
# then run:
python server.py
```

The server starts with:

```
[SERVER STARTED] Running on localhost:9999

Enter your username: <your_user>
Logging in successfully
```

After login the terminal prompt changes to `> `. From there you type **client‑side commands** (see below) and send them over the TCP socket the server is listening on.

---

## Clients

### 1. Graphical User Interface (GUI) Client — Fulfills R5 & R6
Run the GUI client:
```bash
python gui_client.py
# or
python client.py --gui
```
Features:
- **R5 (Chat Rooms)**: Every private chat and group chat opens in its own dedicated room tab or floating pop-out window.
- **R6 (Chat Box & Chat Window)**: Every room includes:
  - **Chat Window**: A scrollable log showing formatted sent messages, incoming messages, and file notices.
  - **Chat Box**: An input entry box with a Send button (and Enter key shortcut) for sending messages directly to that room.
- **R4 (Online Users)**: Real-time list of online users with one-click direct message room launcher.
- **R8–R11 (Groups)**: Create group (R8), see groups with member lists (R9), join groups (R10), and chat inside group rooms (R11).
- **AI Tools**: One-click Ask Gemini, Image Generation, and PDF Summarization.

### 2. Command Line Interface (CLI) Client
Run the CLI client:
```bash
python client.py
```
Room navigation in CLI:
- `/chat <username>` — Enters a private chat room with `<username>`. The prompt updates to `[Room 💬 <username>] > `. Typing any message automatically sends it to this private room.
- `/group <group_name>` — Enters a group chat room. The prompt updates to `[Room 👥 <group_name>] > `. Typing any message automatically sends it to the group.
- `/leave` — Leaves the current room back to the main lobby `> `.

### Raw client → server request shape

Each message is a **single JSON object**:

```json
{
  "action": "<command>",
  "data": { ... }   # optional, only for actions that need it (e.g. send_file data, direct_message msg)
}
```

Examples:

- Login: `login {"username":"alice"}`
- List users: `/list_users` → `{"action":"list_users","data":null}`
- Direct message: `direct_message {"target_name":"bob","msg":"hello"}` or `"/dm bob hello"`
- Create group: `/create_group "mygroup"` → `{"action":"create_group","group":"mygroup"}`

---

## Supported commands

### Authentication
| Command | What it does |
|---|---|
| `/login <username>` | Sends login request; server replies with status **011** + `"Logging in successfully"`. First time only. Returns 010 if username already taken. |
| `/logout` | Sends logout, closes the connection (resets `is_connected`). |

### Listing users
- `/list_users` → all users and their addresses.
- `/list_groups` → group names.
- `/list_files` → files belonging to each user.
- `/list_direct_files` → files you can send directly without joining a group.
- `/list_group_files <group>` → files in a specific group.

### Direct messaging
- `/direct_message <target_name> "<msg>"`  
  or shorthand `"/dm target_name msg"`
- Sends a private message to the user identified by `<target_name>@<addr>`. Returns **200** (target not found) / **201** (sent).

### Groups
- `/create_group <group_name>` → creates new group.
- `/join_group <group_name>` → joins an existing group. Returns **310** if already a member.
- `/leave_group <group_name>` → leaves a group. Returns **320** if doesn't exist or not a member.
- `/group_message <group_name> "<msg>"` / `"/gm <group_name> msg"`
  - Sends a message to every member of the group.

### File operations
| Action | Syntax (client side) | Server action |
|---|---|---|
| Send file | `/send_file <target_name> <file_name> <data>` | writes `data` into `users[<target>].files[<file_name>]`; returns **401** if not yet sent, **400** if target unknown or file already exists. |
| Retrieve file (your own) | `/retrieve_file <file_name>` / `direct_retrieve_file` | returns content; **410** if missing, **411** on first read, **421** once removed. |
| Reject file | `/reject_file <file_name>` | removes from user's files list; returns **420/421**. |
| Create group + send its file | `/create_group <g>` → then `/send_file <tgt> f.txt <data>` | creates group, tracks members/files. |

### AI / Image & PDF
- `/generate_image <file_name> "<prompt>"` — asks Gemini to create an image.
- `/pdf_sumarize <base64_pdf_data>` — sends a base64‑encoded PDF and text "Summarize this document"; returns the summary.

### Ask Google Gemini
- `/ask_gemini "<prompt>"` → calls `client.interactions.create(model="gemini-3.5-flash-lite", input=prompt)`. Returns **501** on failure or the interaction output.

---

## Example session

```bash
$ python server.py
[SERVER STARTED] Running on localhost:9999

Enter your username: alice
Logging in successfully
> /list_users
alice@localhost:9999, bob@localhost:9999
...

> /direct_message bob "Hey, are you free?"
→ [Server]: [alice] Sent direct message to bob...
```

After login the `>` prompt lets you type any of the commands above. Each command is a JSON line that the server decodes and dispatches.

---

## How authentication works

1. **First connection without a valid login** → server replies with status **000** "Not authenticated" and sets `is_logged_in = False`.
2. Sending `/login <username>`:
   - If username exists in `users` → **010** "Username already used".
   - Otherwise → adds entry, sends **011** "Logging in successfully", sets `is_logged_in = True`.
3. All commands after login require `is_logged_in == True`. Trying to log in again or use a non‑existent user yields error codes.

---

## File I/O details

- Files are transferred as raw bytes.
- `openFileToString(path)` reads the file in binary and returns its hex representation.
- `stringToFile(data, path)` writes `data` (base64‑decoded) as binary to disk.
- The server keeps a per‑user `files` dict; retrieval pops the entry from that dict after returning.

---

## Help & where to find more

- **Repository history:** 4 commits on `main`, latest `80d2180 — feat: add AI features`.
- **Branches / tags:** none listed for this repo.
- The code lives in three files:
  - `.env.example` (environment template)
  - `.gitignore`
  - `server.py` and `client.py` (shared server logic, see the previous overview).
