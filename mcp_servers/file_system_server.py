from pathlib import Path
import datetime
import os
import sys # sysをインポート

# このスクリプト自身のログファイルを設定 (mcp_client.py側のロガーとは独立)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
SERVER_DUMMY_LOG_FILE = LOG_DIR / "dummy_server_startup.log"

# 簡単なファイルロギング
def log_to_file(message):
    timestamp = datetime.datetime.now().isoformat()
    with open(SERVER_DUMMY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {message}\n")

if __name__ == "__main__":
    log_to_file("Dummy server process started.")
    log_to_file(f"Current working directory: {os.getcwd()}")
    log_to_file(f"Python executable: {sys.executable}")
    log_to_file(f"sys.path: {str(sys.path)}") # sys.pathはリストなのでstr()で囲む
    log_to_file(f"Script __file__: {__file__}")
    log_to_file(f"Script absolute path: {str(Path(__file__).resolve())}")

    # 標準出力に何か書く (クライアントがこれを読めるかテストのため)
    print("Dummy server: Standard output message.", flush=True)

    # 標準エラー出力にも何か書く
    sys.stderr.write("Dummy server: Standard error message.\n")
    sys.stderr.flush()

    log_to_file("Dummy server attempting to create a flag file.")

    # 起動した証として別のファイルを作成する
    SERVER_STARTED_FLAG_FILE = LOG_DIR / "dummy_server_flag.txt"
    try:
        with open(SERVER_STARTED_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(f"Dummy FileSystemMCPServer started at: {datetime.datetime.now().isoformat()}\n")
            f.write(f"This file confirms the dummy server process was launched successfully.\n")
        log_to_file(f"Successfully created flag file: {SERVER_STARTED_FLAG_FILE}")
    except Exception as e:
        log_to_file(f"ERROR creating flag file: {e}")

    log_to_file("Dummy server process finished its main execution block.")
    # 通常、MCPサーバーはここでリクエストを待ち受けるループに入るが、
    # このダミースクリプトはすぐ終了する。
    # クライアント側がプロセス終了をどう扱うかによっては、
    # time.sleep(数秒) を入れても良いかもしれない。
