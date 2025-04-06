import imaplib
from pydantic import ConfigDict, SecretStr
from pydantic_settings import BaseSettings
import email
from email.header import decode_header


class Settings(BaseSettings):
    imap_server: str
    email: str
    password: SecretStr
 
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
    )


def load_email_account():
    return Settings()


def connect_to_imap_server(server, username, password, folder="INBOX"):
    """IMAPサーバーに接続してログインする"""
    try:
        # IMAPサーバーに接続
        mail = imaplib.IMAP4_SSL(server)
        
        # ログイン
        mail.login(username, password)
        
        # メールボックスを選択（デフォルトはINBOX）
        mail.select(folder)
        
        print(f"接続成功: {server}, フォルダ: {folder}")
        return mail
    except Exception as e:
        print(f"接続エラー: {e}")
        return None


def get_emails(mail_client):
    try:
        # メールを検索
        result, data = mail_client.search(None, "ALL")
        
        if result != 'OK':
            print("メールの検索に失敗しました。")
            return []
        
        # メールIDのリストを取得
        email_ids = data[0].split()
        
        return email_ids
    except Exception as e:
        print(f"メールの取得エラー: {e}")
        return []


def get_email_details(email_client, msg_id):
    """メールの詳細情報を取得する"""
    try:
        status, msg_data = email_client.fetch(msg_id, "(RFC822)")
        
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
            subject = subject[0][0].decode(subject[0][1])
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


def delete_emails(mail_client, email_ids):
    """指定したメールIDのメールを削除する"""
    try:
        for email_id in email_ids:
            mail_client.store(email_id, '+FLAGS', '\\Deleted')
        mail_client.expunge()
        print(f"{len(email_ids)}件のメールを削除しました。")
    except Exception as e:
        print(f"メール削除エラー: {e}")


def move_emails_to_spam(mail_client, message_ids, archive_folder="Spam"):
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
            if _move_email_to_folder(mail_client, msg_id, archive_folder):
                moved_count += 1

        mail_client.expunge()
        print(f"{moved_count}件のメールを '{archive_folder}' に移動しました")
        return moved_count
    except Exception as e:
        print(f"メール移動エラー: {e}")
        return 0


def _move_email_to_folder(mail_client, msg_id, folder_name):
    """メールを指定したフォルダに移動する"""
    try:
        # メールを指定フォルダにコピー
        status, response = mail_client.copy(msg_id, folder_name)
        
        if status != "OK":
            print(f"メールコピーエラー: メッセージID {msg_id}, レスポンス: {response}")
            return False
        
        # 元のメールに削除フラグを設定
        mail_client.store(msg_id, '+FLAGS', '\\Deleted')
        return True
    except Exception as e:
        print(f"メール移動エラー: {e}")
        return False
