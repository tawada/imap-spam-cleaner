import datetime
import email
import imaplib
import poplib
import unicodedata
from email.header import decode_header
from typing import Literal

import pydantic
import yaml
from loguru import logger
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

    def connect_to_server(self): ...

    def get_emails(self): ...

    def get_email_details(self, msg_id): ...

    def move_emails_to_folder(self, message_ids, folder): ...

    def delete_emails(self, message_ids): ...

    def logout(self): ...


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

            logger.debug(f"接続成功: {server}")
            return True
        except Exception as e:
            logger.debug(f"接続エラー: {e}")
            self.email_client = None
            return False

    def get_emails(self):
        """メールを検索してメールIDのリストを取得する"""
        try:
            # メールを検索
            # 24時間以内に受信したメールを取得
            since_date = (
                datetime.datetime.now() - datetime.timedelta(days=1)
            ).strftime("%d-%b-%Y")
            result, data = self.email_client.search(
                None, f'(SINCE "{since_date}")')

            if result != "OK":
                logger.debug("メールの検索に失敗しました。")
                return []

            # メールIDのリストを取得
            email_ids = data[0].split()

            return email_ids
        except Exception as e:
            logger.debug(f"メールの取得エラー: {e}")
            return []

    def get_email_details(self, msg_id):
        """メールの詳細情報を取得する"""
        try:
            status, msg_data = self.email_client.fetch(msg_id, "(BODY.PEEK[])")

            if status != "OK":
                logger.debug(f"メール取得エラー: メッセージID {msg_id}")
                return None

            # メールの内容を解析
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # 件名を取得してデコード
            subject = decode_header(msg["Subject"])
            if subject[0][1] is not None:
                # エンコーディングが指定されている場合はデコード
                subject = subject[0][0].decode(subject[0][1], errors="ignore")
            else:
                # エンコーディングが指定されていない場合はそのまま
                subject = subject[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode("utf-8", errors="ignore")

            # 送信者を取得
            sender = msg.get("From", "")

            # 日付を取得
            date = msg.get("Date", "")

            # 結合文字列を除去
            subject = remove_combining_characters(subject) 
            sender = remove_combining_characters(sender)

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "date": date,
            }
        except Exception as e:
            logger.debug(f"メール解析エラー: {e}")
            return None

    def move_emails_to_folder(self, message_ids, folder) -> list[int]:
        """指定したメールを指定フォルダに移動する"""

        if not message_ids:
            logger.debug("移動するメールがありません")
            return []

        ret = []
        try:
            status, folders = self.email_client.list()
            if status != "OK":
                logger.debug("フォルダの取得に失敗しました。")
                return []

            decoded_folders = [f.decode().split(' "." ')[-1] for f in folders]
            if folder not in decoded_folders:
                logger.debug(f"フォルダ '{folder}' は存在しません。新規作成します。")
                self.email_client.create(folder)

            total = len(message_ids)

            for i, msg_id in enumerate(message_ids):
                # 進捗表示
                if (i + 1) % 10 == 0 or i + 1 == total:
                    logger.debug(f"処理中... {i+1}/{total}")

                # メールを指定フォルダに移動
                if _move_email_to_folder(self.email_client, msg_id, folder):
                    ret.append(msg_id)

            logger.debug(f"{len(ret)}件のメールを '{folder}' に移動しました")
            return ret
        except Exception as e:
            logger.debug(f"メール移動エラー: {e}")
            return ret

    def delete_emails(self, message_ids):
        """指定したメールを削除する"""
        if not message_ids:
            logger.debug("削除するメールがありません")
            return 0

        try:
            for msg_id in message_ids:
                # メールに削除フラグを設定
                self.email_client.store(msg_id, "+FLAGS", "\\Deleted")

            # 削除フラグが設定されたメールを完全に削除
            self.email_client.expunge()
            logger.debug(f"{len(message_ids)}件のメールを削除しました")
            return len(message_ids)
        except Exception as e:
            logger.debug(f"メール削除エラー: {e}")
            return 0

    def logout(self):
        """IMAPサーバーからログアウトする"""
        try:
            if self.email_client:
                self.email_client.logout()
                logger.debug("ログアウト成功")
        except Exception as e:
            logger.debug(f"ログアウトエラー: {e}")


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
            email_ids = [str(i + 1) for i in range(num_messages)]

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
                subject = subject[0][0].decode(subject[0][1], errors="ignore")
            else:
                # エンコーディングが指定されていない場合はそのまま
                subject = subject[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode("utf-8", errors="ignore")

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

    def move_emails_to_folder(self, message_ids, archive_folder="Spam"):
        """指定したメールをスパムフォルダに移動する"""

        if not message_ids:
            print("移動するメールがありません")
            return 0

        moved_count = 0

        try:
            total = len(message_ids)

            for i, msg_id in enumerate(message_ids):
                # 進捗表示
                if (i + 1) % 10 == 0 or i + 1 == total:
                    print(f"処理中... {i+1}/{total}")

                # メールを指定フォルダに移動
                # if _move_email_to_folder(self.email_client, msg_id, archive_folder):
                # moved_count += 1

            print(f"{moved_count}件のメールを '{archive_folder}' に移動しました")
            return moved_count
        except Exception as e:
            print(f"メール移動エラー: {e}")
            return 0

    def delete_emails(self, message_ids):
        """指定したメールを削除する"""
        if not message_ids:
            print("削除するメールがありません")
            return 0

        try:
            for msg_id in message_ids:
                # メールを削除
                self.email_client.dele(msg_id)

            print(f"{len(message_ids)}件のメールを削除しました")
            return len(message_ids)
        except Exception as e:
            print(f"メール削除エラー: {e}")
            return 0

    def logout(self):
        """POP3サーバーからログアウトする"""
        try:
            if self.email_client:
                self.email_client.quit()
                print("ログアウト成功")
        except Exception as e:
            print(f"ログアウトエラー: {e}")


setattr(
    EmailClient,
    "from_email_account",
    lambda ea: EmailClientIMAP(
        ea) if ea.protocol == "IMAP" else EmailClientPOP3(ea),
)


def load_email_account(setting_dir: str) -> EmailAccount:
    path = f"settings/{setting_dir}/email_account.yaml"
    with open(path, "r") as f:
        email_account_dict = yaml.safe_load(f)
    return EmailAccount(**email_account_dict)


def _move_email_to_folder(email_client, msg_id, folder_name):
    """メールを指定したフォルダに移動する"""
    try:
        # メールを指定フォルダにコピー
        status, response = email_client.copy(msg_id, folder_name)

        if status != "OK":
            logger.debug(f"メールコピーエラー: メッセージID {msg_id}, レスポンス: {response}")
            return False

        # 元のメールに削除フラグを設定
        email_client.store(msg_id, "+FLAGS", "\\Deleted")
        return True
    except Exception as e:
        logger.debug(f"メール移動エラー: {e}")
        return False


def remove_combining_characters(text):
    """正規化で結合文字を分解し、結合文字でないものだけを返す"""
    return ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if not unicodedata.combining(char)
    )
