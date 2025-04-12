import email
import imaplib
import poplib
import pydantic
import yaml

from typing import Literal
from email.header import decode_header
from pydantic import SecretStr


class EmailAccount(pydantic.BaseModel):
    imap_server: str
    email: str
    password: SecretStr
    protocol: Literal["IMAP", "POP3"] = "IMAP"


class EmailClient:
    def __init__(self, email_account: EmailAccount):
        self.email_account = email_account
        self.email_client = None

    def connect_to_server(self):
        ...

    def get_emails(self):
        ...

    def get_email_details(self, msg_id):
        ...

    def move_emails_to_spam(self, message_ids, archive_folder="Spam"):
        ...

    def logout(self):
        ...


class EmailClientIMAP(EmailClient):
    def connect_to_server(self):
        """IMAPサーバーに接続してログインする"""
        try:
            server = self.email_account.imap_server
            username = self.email_account.email
            password = self.email_account.password.get_secret_value()

            # IMAPサーバーに接続
            self.email_client = imaplib.IMAP4_SSL(server)

            # ログイン
            self.email_client.login(username, password)

            # メールボックスを選択（デフォルトはINBOX）
            self.email_client.select("INBOX")

            print(f"接続成功: {server}")
            return True
        except Exception as e:
            print(f"接続エラー: {e}")
            self.email_client = None
            return False

    def get_emails(self):
        """メールを検索してメールIDのリストを取得する"""
        try:
            # メールを検索
            result, data = self.email_client.search(None, "ALL")
            
            if result != 'OK':
                print("メールの検索に失敗しました。")
                return []
            
            # メールIDのリストを取得
            email_ids = data[0].split()
            
            return email_ids
        except Exception as e:
            print(f"メールの取得エラー: {e}")
            return []

    def get_email_details(self, msg_id):
        """メールの詳細情報を取得する"""
        try:
            status, msg_data = self.email_client.fetch(msg_id, "(RFC822)")
            
            if status != "OK":
                print(f"メール取得エラー: メッセージID {msg_id}")
                return None
            
            # メールの内容を解析
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # 件名を取得してデコード
            subject = decode_header(msg["Subject"])
            if subject[0][1] is not None:
                # エンコーディングが指定されている場合はデコード
                subject = subject[0][0].decode(subject[0][1], errors='ignore')
            else:
                # エンコーディングが指定されていない場合はそのまま
                subject = subject[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
            
            # 送信者を取得
            sender = msg.get("From", "")
            
            # 日付を取得
            date = msg.get("Date", "")

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "date": date,
            }
        except Exception as e:
            print(f"メール解析エラー: {e}")
            return None

    def move_emails_to_spam(self, message_ids, archive_folder="Spam"):
        """指定したメールをスパムフォルダに移動する"""
        
        if not message_ids:
            print("移動するメールがありません")
            return 0
        
        moved_count = 0
        
        try:
            total = len(message_ids)
            
            for i, msg_id in enumerate(message_ids):
                # 進捗表示
                if (i+1) % 10 == 0 or i+1 == total:
                    print(f"処理中... {i+1}/{total}")
                
                # メールを指定フォルダに移動
                if _move_email_to_folder(self.email_client, msg_id, archive_folder):
                    moved_count += 1

            self.email_client.expunge()
            print(f"{moved_count}件のメールを '{archive_folder}' に移動しました")
            return moved_count
        except Exception as e:
            print(f"メール移動エラー: {e}")
            return 0

    def logout(self):
        """IMAPサーバーからログアウトする"""
        try:
            if self.email_client:
                self.email_client.logout()
                print("ログアウト成功")
        except Exception as e:
            print(f"ログアウトエラー: {e}")


class EmailClientPOP3(EmailClient):
    def connect_to_server(self):
        """POP3サーバーに接続してログインする"""
        try:
            server = self.email_account.imap_server
            username = self.email_account.email
            password = self.email_account.password.get_secret_value()

            # POP3サーバーに接続
            self.email_client = poplib.POP3_SSL(server)

            # ログイン
            self.email_client.user(username)
            self.email_client.pass_(password)

            print(f"接続成功: {server}")
            return True
        except Exception as e:
            print(f"接続エラー: {e}")
            self.email_client = None
            return False

    def get_emails(self):
        """メールを取得する"""
        try:
            # メールのリストを取得
            num_messages = len(self.email_client.list()[1])
            
            # メールIDのリストを生成
            email_ids = [str(i+1) for i in range(num_messages)]
            
            return email_ids
        except Exception as e:
            print(f"メールの取得エラー: {e}")
            return []

    def get_email_details(self, msg_id):
        """メールの詳細情報を取得する"""
        try:
            # メールを取得
            msg_data = self.email_client.retr(msg_id)[1]
            
            # メールの内容を解析
            raw_email = b"\n".join(msg_data)
            msg = email.message_from_bytes(raw_email)

            # 件名を取得してデコード
            subject = decode_header(msg["Subject"])
            if subject[0][1] is not None:
                # エンコーディングが指定されている場合はデコード
                subject = subject[0][0].decode(subject[0][1], errors='ignore')
            else:
                # エンコーディングが指定されていない場合はそのまま
                subject = subject[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
            
            # 送信者を取得
            sender = msg.get("From", "")
            
            # 日付を取得
            date = msg.get("Date", "")

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "date": date,
            }
        except Exception as e:
            print(f"メール解析エラー: {e}")
            return None

    def move_emails_to_spam(self, message_ids, archive_folder="Spam"):
        """指定したメールをスパムフォルダに移動する"""
        
        if not message_ids:
            print("移動するメールがありません")
            return 0
        
        moved_count = 0
        
        try:
            total = len(message_ids)
            
            for i, msg_id in enumerate(message_ids):
                # 進捗表示
                if (i+1) % 10 == 0 or i+1 == total:
                    print(f"処理中... {i+1}/{total}")
                
                # メールを指定フォルダに移動
                # if _move_email_to_folder(self.email_client, msg_id, archive_folder):
                    # moved_count += 1

            print(f"{moved_count}件のメールを '{archive_folder}' に移動しました")
            return moved_count
        except Exception as e:
            print(f"メール移動エラー: {e}")
            return 0

    def logout(self):
        """POP3サーバーからログアウトする"""
        try:
            if self.email_client:
                self.email_client.quit()
                print("ログアウト成功")
        except Exception as e:
            print(f"ログアウトエラー: {e}")

setattr(EmailClient, "from_email_account", lambda ea: EmailClientIMAP(ea) if ea.protocol == "IMAP" else EmailClientPOP3(ea))


def load_email_account(setting_dir: str) -> EmailAccount:
    path = f"settings/{setting_dir}/email_account.yaml"
    with open(path, "r") as f:
        email_account_dict = yaml.safe_load(f)
    print(f"メールアカウント設定: {email_account_dict}")
    return EmailAccount(**email_account_dict)


def _move_email_to_folder(email_client, msg_id, folder_name):
    """メールを指定したフォルダに移動する"""
    try:
        # メールを指定フォルダにコピー
        status, response = email_client.copy(msg_id, folder_name)
        
        if status != "OK":
            print(f"メールコピーエラー: メッセージID {msg_id}, レスポンス: {response}")
            return False
        
        # 元のメールに削除フラグを設定
        email_client.store(msg_id, '+FLAGS', '\\Deleted')
        return True
    except Exception as e:
        print(f"メール移動エラー: {e}")
        return False
