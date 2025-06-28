import datetime
import os
from tkinter import filedialog, messagebox # messagebox用にtkinterをインポート

class CommunicationLogger:
    _instance = None
    _session_log_filepath = None
    _log_dir = None # 初期値はNoneとし、__new__で決定する

    # 環境変数名
    ENV_VAR_LOG_DIR = 'GLOBAL_LOG_DIR_PATH'
    ENV_VAR_SESSION_LOG = 'GLOBAL_SESSION_LOG_PATH'

    DEFAULT_LOG_DIR = "communication_logs"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CommunicationLogger, cls).__new__(cls)
            cls._instance._initialized = False

            # 1. ログディレクトリ (_log_dir) の決定
            # 優先順位: 環境変数 > コンストラクタ引数 > デフォルト値
            env_log_dir = os.getenv(cls.ENV_VAR_LOG_DIR)
            arg_log_dir = kwargs.get('log_dir', args[0] if len(args) > 0 and args[0] is not None else None)

            if env_log_dir:
                CommunicationLogger._log_dir = os.path.abspath(env_log_dir)
                # print(f"Logger (new): Using log_dir from ENV: {CommunicationLogger._log_dir}")
            elif arg_log_dir:
                CommunicationLogger._log_dir = os.path.abspath(arg_log_dir)
                # print(f"Logger (new): Using log_dir from ARG: {CommunicationLogger._log_dir}")
            else:
                CommunicationLogger._log_dir = os.path.abspath(cls.DEFAULT_LOG_DIR)
                # print(f"Logger (new): Using log_dir DEFAULT: {CommunicationLogger._log_dir}")

            # ログディレクトリの作成 (存在しない場合)
            if not os.path.exists(CommunicationLogger._log_dir):
                try:
                    os.makedirs(CommunicationLogger._log_dir)
                    print(f"Logger (new): Log directory created: {CommunicationLogger._log_dir}")
                except Exception as e:
                    print(f"Logger (new): Error creating log directory {CommunicationLogger._log_dir}: {e}")
                    # フォールバック (カレントディレクトリのcommunication_logs)
                    CommunicationLogger._log_dir = os.path.abspath(cls.DEFAULT_LOG_DIR)
                    if not os.path.exists(CommunicationLogger._log_dir):
                        try: os.makedirs(CommunicationLogger._log_dir)
                        except: pass # さらに失敗する場合は仕方ない
                    print(f"Logger (new): Falling back to log_dir: {CommunicationLogger._log_dir}")

            # 2. セッションログファイルパス (_session_log_filepath) の決定
            # 優先順位: 環境変数 > （環境変数がなければ）新規生成
            env_session_log = os.getenv(cls.ENV_VAR_SESSION_LOG)
            if env_session_log:
                CommunicationLogger._session_log_filepath = os.path.abspath(env_session_log)
                # print(f"Logger (new): Using session_log from ENV: {CommunicationLogger._session_log_filepath}")
                # 環境変数で指定された場合、それが属するディレクトリが _log_dir と一致するか確認（任意）
                # ここでは、環境変数で指定されたパスをそのまま信頼する
                # ただし、そのディレクトリが存在しない場合は作成を試みる
                _s_log_dir = os.path.dirname(CommunicationLogger._session_log_filepath)
                if not os.path.exists(_s_log_dir) :
                    try: os.makedirs(_s_log_dir); print(f"Logger (new): Created directory for ENV session_log: {_s_log_dir}")
                    except Exception as e_mkdir: print(f"Logger (new): Failed to create dir for ENV session_log {_s_log_dir}: {e_mkdir}")

            else: # 環境変数がない場合、新規生成
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"session_log_{timestamp}.txt"
                CommunicationLogger._session_log_filepath = os.path.join(CommunicationLogger._log_dir, filename)
                # print(f"Logger (new): Generated new session_log: {CommunicationLogger._session_log_filepath}")
                # 新規生成時はヘッダーを書き込む
                try:
                    with open(CommunicationLogger._session_log_filepath, "a", encoding="utf-8") as f:
                        f.write(f"--- Session Log Started (New): {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")
                except Exception as e:
                    print(f"Logger (new): Error initializing new session log file '{CommunicationLogger._session_log_filepath}': {e}")

        return cls._instance

    def __init__(self, log_dir=None): # log_dir引数は__new__で処理されるため、ここではほぼ参照不要
        if self._initialized:
            return
        self.log_entries = []

        # __new__でパスが決定され、ディレクトリも作成されているはず
        # もし_session_log_filepathがNoneのままなら、何かがおかしい（基本的には起こらない想定）
        if CommunicationLogger._session_log_filepath is None:
            print("Logger (init): CRITICAL - _session_log_filepath is None after __new__.")
            # 緊急避難的にデフォルトパスを再生成するなどの処理も考えられるが、設計上は__new__で解決するべき
            # ここでは、エラーのままとする

        # 環境変数でパスが指定され、かつファイルがまだ存在しない場合にヘッダーを書き込む
        # (新規生成の場合は__new__で既に書き込まれている)
        if os.getenv(self.ENV_VAR_SESSION_LOG) and \
           CommunicationLogger._session_log_filepath and \
           not os.path.exists(CommunicationLogger._session_log_filepath):
            # print(f"Logger (init): Session log from ENV does not exist, creating: {CommunicationLogger._session_log_filepath}")
            try:
                with open(CommunicationLogger._session_log_filepath, "a", encoding="utf-8") as f:
                    f.write(f"--- Session Log Started (ENV, Created): {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")
            except Exception as e:
                print(f"Logger (init): Error creating session log file from ENV '{CommunicationLogger._session_log_filepath}': {e}")

        self._initialized = True


    def add_log(self, direction, function_type, text_body):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "direction": direction,
            "function_type": function_type,
            "text_body": text_body
        }
        self.log_entries.append(log_entry)

        if CommunicationLogger._session_log_filepath:
            try:
                with open(CommunicationLogger._session_log_filepath, "a", encoding="utf-8") as f:
                    f.write(f"Timestamp: {log_entry['timestamp']}\n")
                    f.write(f"Direction: {log_entry['direction']}\n")
                    f.write(f"Function Type: {log_entry['function_type']}\n")
                    f.write(f"Body:\n{log_entry['text_body']}\n")
                    f.write("-" * 40 + "\n\n")
            except Exception as e:
                print(f"Error writing to session log file '{CommunicationLogger._session_log_filepath}': {e}")
        else:
            print("Logger (add_log): Error - _session_log_filepath is not set. Cannot write to file.")


    def get_logs(self):
        return self.log_entries

    def get_session_log_filepath(self):
        return CommunicationLogger._session_log_filepath

    def get_log_dir(self): # ログディレクトリ取得用メソッド
        return CommunicationLogger._log_dir

    def clear_logs(self):
        self.log_entries = []

    def save_logs_to_file(self, parent_window=None):
        if not self.log_entries:
            messagebox.showinfo("保存情報", "メモリ内に保存するログがありません。", parent=parent_window)
            return

        initial_dir = CommunicationLogger._log_dir \
            if CommunicationLogger._log_dir and os.path.isdir(CommunicationLogger._log_dir) \
            else os.path.abspath(".")

        initial_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_filename = f"communication_snapshot_{initial_timestamp}.txt"

        filepath = filedialog.asksaveasfilename(
            parent=parent_window,
            title="ログスナップショットを名前を付けて保存",
            initialdir=initial_dir,
            initialfile=initial_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"--- Log Snapshot Taken: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"--- Based on in-memory logs at the time of saving. ---\n\n")
                for entry in self.log_entries:
                    f.write(f"Timestamp: {entry['timestamp']}\n")
                    f.write(f"Direction: {entry['direction']}\n")
                    f.write(f"Function Type: {entry['function_type']}\n")
                    f.write(f"Body:\n{entry['text_body']}\n")
                    f.write("-" * 40 + "\n\n")
            messagebox.showinfo("保存完了", f"ログスナップショットを {os.path.abspath(filepath)} に保存しました。", parent=parent_window)
        except Exception as e:
            messagebox.showerror("保存エラー", f"ログスナップショットの保存中にエラーが発生しました: {e}", parent=parent_window)

if __name__ == "__main__":
    import shutil

    def reset_env_vars():
        if CommunicationLogger.ENV_VAR_LOG_DIR in os.environ: del os.environ[CommunicationLogger.ENV_VAR_LOG_DIR]
        if CommunicationLogger.ENV_VAR_SESSION_LOG in os.environ: del os.environ[CommunicationLogger.ENV_VAR_SESSION_LOG]
        CommunicationLogger._instance = None # シングルトンリセット
        CommunicationLogger._log_dir = None
        CommunicationLogger._session_log_filepath = None


    print("--- Test Suite for CommunicationLogger ---")

    # Test Case 1: No ENV VARS, no args (defaults)
    reset_env_vars()
    test_dir_1 = os.path.abspath(CommunicationLogger.DEFAULT_LOG_DIR)
    if os.path.exists(test_dir_1): shutil.rmtree(test_dir_1)
    print("\n[Test 1] Defaults (no ENV, no Args)")
    logger1 = CommunicationLogger()
    assert logger1.get_log_dir() == test_dir_1, f"Test 1 LogDir: Expected {test_dir_1}, Got {logger1.get_log_dir()}"
    assert logger1.get_session_log_filepath().startswith(test_dir_1), "Test 1 SessionFile path mismatch"
    assert os.path.exists(logger1.get_session_log_filepath()), "Test 1 Session file not created"
    logger1.add_log("t1", "default", "Test 1")
    if os.path.exists(test_dir_1): shutil.rmtree(test_dir_1)


    # Test Case 2: log_dir from argument
    reset_env_vars()
    test_dir_2_arg = "test_logs_arg"
    test_dir_2 = os.path.abspath(test_dir_2_arg)
    if os.path.exists(test_dir_2): shutil.rmtree(test_dir_2)
    print(f"\n[Test 2] Log dir from argument ('{test_dir_2_arg}')")
    logger2 = CommunicationLogger(log_dir=test_dir_2_arg)
    assert logger2.get_log_dir() == test_dir_2, f"Test 2 LogDir: Expected {test_dir_2}, Got {logger2.get_log_dir()}"
    assert logger2.get_session_log_filepath().startswith(test_dir_2), "Test 2 SessionFile path mismatch"
    logger2.add_log("t2", "arg", "Test 2")
    if os.path.exists(test_dir_2): shutil.rmtree(test_dir_2)


    # Test Case 3: log_dir from ENV VAR
    reset_env_vars()
    test_dir_3_env = "test_logs_env_dir"
    os.environ[CommunicationLogger.ENV_VAR_LOG_DIR] = test_dir_3_env
    test_dir_3 = os.path.abspath(test_dir_3_env)
    if os.path.exists(test_dir_3): shutil.rmtree(test_dir_3)
    print(f"\n[Test 3] Log dir from ENV ('{test_dir_3_env}')")
    logger3 = CommunicationLogger() # No arg, should pick up ENV
    assert logger3.get_log_dir() == test_dir_3, f"Test 3 LogDir: Expected {test_dir_3}, Got {logger3.get_log_dir()}"
    assert logger3.get_session_log_filepath().startswith(test_dir_3), "Test 3 SessionFile path mismatch"
    logger3.add_log("t3", "env_dir", "Test 3")
    if os.path.exists(test_dir_3): shutil.rmtree(test_dir_3)


    # Test Case 4: session_log_filepath from ENV VAR
    reset_env_vars()
    test_dir_4_env = "test_logs_env_session_dir" # Separate dir for this test's session file
    test_session_file_env = os.path.join(test_dir_4_env, "session_from_env.log")
    os.environ[CommunicationLogger.ENV_VAR_SESSION_LOG] = test_session_file_env
    # For this test, also set ENV_VAR_LOG_DIR to ensure _log_dir is also derived from ENV if needed, or is consistent
    os.environ[CommunicationLogger.ENV_VAR_LOG_DIR] = test_dir_4_env

    test_dir_4 = os.path.abspath(test_dir_4_env)
    if os.path.exists(test_dir_4): shutil.rmtree(test_dir_4) # Clean before test
    # os.makedirs(test_dir_4, exist_ok=True) # Ensure dir exists for the session file

    print(f"\n[Test 4] Session log from ENV ('{test_session_file_env}')")
    logger4 = CommunicationLogger()
    abs_test_session_file_env = os.path.abspath(test_session_file_env)
    assert logger4.get_session_log_filepath() == abs_test_session_file_env, f"Test 4 SessionFile: Expected {abs_test_session_file_env}, Got {logger4.get_session_log_filepath()}"
    assert logger4.get_log_dir() == test_dir_4, f"Test 4 LogDir with session ENV: Expected {test_dir_4}, Got {logger4.get_log_dir()}"
    assert os.path.exists(logger4.get_session_log_filepath()), "Test 4 Session file (from ENV) not created/found"
    logger4.add_log("t4", "env_session", "Test 4")
    if os.path.exists(test_dir_4): shutil.rmtree(test_dir_4)


    # Test Case 5: ENV VAR for log_dir takes precedence over argument
    reset_env_vars()
    test_dir_5_env = "test_logs_env_priority_dir"
    test_dir_5_arg = "test_logs_arg_ignored_dir"
    os.environ[CommunicationLogger.ENV_VAR_LOG_DIR] = test_dir_5_env
    test_dir_5 = os.path.abspath(test_dir_5_env)
    if os.path.exists(test_dir_5): shutil.rmtree(test_dir_5)
    if os.path.exists(os.path.abspath(test_dir_5_arg)) : shutil.rmtree(os.path.abspath(test_dir_5_arg))

    print(f"\n[Test 5] ENV log_dir ('{test_dir_5_env}') takes precedence over arg ('{test_dir_5_arg}')")
    logger5 = CommunicationLogger(log_dir=test_dir_5_arg)
    assert logger5.get_log_dir() == test_dir_5, f"Test 5 LogDir: Expected ENV {test_dir_5}, Got {logger5.get_log_dir()}"
    logger5.add_log("t5", "env_priority", "Test 5")
    if os.path.exists(test_dir_5): shutil.rmtree(test_dir_5)
    if os.path.exists(os.path.abspath(test_dir_5_arg)) : shutil.rmtree(os.path.abspath(test_dir_5_arg))


    # Test Case 6: Singleton behavior (logs accumulate in memory and file)
    reset_env_vars()
    test_dir_6 = os.path.abspath("test_singleton_dir")
    if os.path.exists(test_dir_6): shutil.rmtree(test_dir_6)
    print("\n[Test 6] Singleton Behavior")
    logger6a = CommunicationLogger(log_dir="test_singleton_dir")
    logger6a.add_log("s6", "part1", "Singleton part 1")
    logger6b = CommunicationLogger() # Should be same instance
    assert logger6a is logger6b, "Test 6: Not a singleton"
    logger6b.add_log("s6", "part2", "Singleton part 2")
    assert len(logger6a.get_logs()) == 2, f"Test 6: Expected 2 logs in memory, got {len(logger6a.get_logs())}"

    # Check file content (simple check for number of entries)
    if logger6a.get_session_log_filepath() and os.path.exists(logger6a.get_session_log_filepath()):
        with open(logger6a.get_session_log_filepath(), "r", encoding="utf-8") as f:
            content = f.read()
            assert content.count("Timestamp:") == 2 + 1, f"Test 6: Expected 2 log entries in file (+1 for header), found {content.count('Timestamp:')-1}" # +1 for header
    else:
        assert False, "Test 6: Session log file not found for content check"
    if os.path.exists(test_dir_6): shutil.rmtree(test_dir_6)

    reset_env_vars() # Clean up env vars for subsequent runs if any
    print("\n--- All tests finished ---")
