import datetime
import os
from tkinter import filedialog, messagebox # messagebox用にtkinterをインポート

class CommunicationLogger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CommunicationLogger, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir="communication_logs"):
        if self._initialized:
            return
        self.log_entries = []
        self.log_dir = log_dir
        # ログディレクトリの存在確認と作成
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                print(f"Log directory created: {os.path.abspath(self.log_dir)}")
            except Exception as e:
                print(f"Error creating log directory {self.log_dir}: {e}")
                # カレントディレクトリをフォールバックとして使用
                self.log_dir = "."
                print(f"Falling back to current directory for logs: {os.path.abspath(self.log_dir)}")

        self._initialized = True

    def add_log(self, direction, function_type, text_body):
        """
        Adds a new log entry.
        :param direction: "sent" or "received"
        :param function_type: "text_generation" or "voice_synthesis"
        :param text_body: The plain text body of the communication.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "direction": direction,
            "function_type": function_type,
            "text_body": text_body
        }
        self.log_entries.append(log_entry)
        # print(f"Log added: {direction}, {function_type}, {len(text_body)} chars") # Optional: for debugging

    def get_logs(self):
        """
        Returns all recorded log entries.
        """
        return self.log_entries

    def clear_logs(self):
        """
        Clears all recorded log entries from memory.
        """
        self.log_entries = []
        # print("Logs cleared from memory.") # Optional: for debugging

    def save_logs_to_file(self, parent_window=None):
        """
        Saves all recorded log entries to a file.
        The filename includes the current timestamp.
        :param parent_window: Parent window for messagebox (optional).
        """
        if not self.log_entries:
            messagebox.showinfo("保存情報", "保存するログがありません。", parent=parent_window)
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"communication_log_{timestamp}.txt"

        # ログディレクトリが絶対パスでない場合は、カレントディレクトリからの相対パスと解釈される
        # ここでは __init__ で設定された self.log_dir をそのまま使う
        filepath = os.path.join(self.log_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for entry in self.log_entries:
                    f.write(f"Timestamp: {entry['timestamp']}\n")
                    f.write(f"Direction: {entry['direction']}\n")
                    f.write(f"Function Type: {entry['function_type']}\n")
                    f.write(f"Body:\n{entry['text_body']}\n")
                    f.write("-" * 40 + "\n")
            messagebox.showinfo("保存完了", f"ログを {os.path.abspath(filepath)} に保存しました。", parent=parent_window)
            # print(f"Logs saved to: {os.path.abspath(filepath)}") # Optional: for debugging
        except Exception as e:
            messagebox.showerror("保存エラー", f"ログの保存中にエラーが発生しました: {e}", parent=parent_window)
            # print(f"Error saving logs: {e}") # Optional: for debugging

if __name__ == "__main__":
    # テスト用のコード
    logger = CommunicationLogger() # 初回インスタンス化
    logger_same = CommunicationLogger() # 同じインスタンスのはず

    print(f"Is logger the same instance as logger_same? {logger is logger_same}")

    logger.add_log("sent", "text_generation", "ユーザーからのプロンプトです。")
    logger.add_log("received", "text_generation", "AIからのレスポンスです。")
    logger.add_log("sent", "voice_synthesis", "読み上げるテキストです。")

    all_logs = logger.get_logs()
    print(f"\n--- Recorded Logs ({len(all_logs)}) ---")
    for log_item in all_logs:
        print(f"  Timestamp: {log_item['timestamp']}")
        print(f"  Direction: {log_item['direction']}")
        print(f"  Type: {log_item['function_type']}")
        print(f"  Body: {log_item['text_body'][:50]}...") # Displaying first 50 chars
        print("-" * 20)

    # messageboxのテストのためにtkinterのルートウィンドウを一時的に作成
    # import tkinter
    # test_root = tkinter.Tk()
    # test_root.withdraw() # 表示はしない

    # logger.save_logs_to_file(parent_window=test_root)

    # # ファイルが実際に作成されたか確認 (手動)
    # print(f"\nCheck for log file in: {os.path.abspath(logger.log_dir)}")

    # logger.clear_logs()
    # print(f"\nLogs after clearing: {logger.get_logs()}")

    # logger.add_log("sent", "text_generation", "クリア後の新しいログ。")
    # logger.save_logs_to_file(parent_window=test_root)
    # print(f"\nCheck for another log file in: {os.path.abspath(logger.log_dir)}")

    # test_root.destroy() # テストウィンドウを閉じる
    print("\nCommunicationLogger test finished.")
