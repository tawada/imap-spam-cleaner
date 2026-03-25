import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from loguru import logger

import src.emails
import src.rules
import src.settings


def create_filter_decision_logger() -> logging.Logger | None:
    log_path = Path("logs/filter_decisions.log")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        decision_logger = logging.getLogger("filter_decisions")
        if decision_logger.handlers:
            return decision_logger

        handler = RotatingFileHandler(
            log_path,
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s | setting=%(setting_dir)s | email_id=%(email_id)s | action=%(action)s | to=%(to_folder)s | from=%(sender)s | reason=%(reason)s | subject=%(subject)s"
        )
        handler.setFormatter(formatter)
        decision_logger.addHandler(handler)
        decision_logger.setLevel(logging.INFO)
        decision_logger.propagate = False
        return decision_logger
    except Exception as e:
        logger.warning(f"振り分けログの初期化に失敗しました: {e}")
        return None


def to_one_line(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    return str(value).replace("\n", " ").replace("\r", " ")


def log_filter_decision(
    decision_logger: logging.Logger | None,
    setting_dir: str,
    email_id,
    action: str,
    folder: str,
    rule,
    email_data: dict,
) -> None:
    if not decision_logger:
        return
    try:
        decision_logger.info(
            "matched",
            extra={
                "setting_dir": to_one_line(setting_dir),
                "email_id": to_one_line(email_id),
                "action": action,
                "to_folder": to_one_line(folder),
                "sender": to_one_line(email_data.get("from", "")),
                "reason": to_one_line(rule) if rule else "",
                "subject": to_one_line(email_data.get("subject", "")),
            },
        )
    except Exception as e:
        logger.warning(f"振り分けログの書き込みに失敗しました: {e}")


def main():
    setting_dirs = src.settings.get_setting_dirs()
    decision_logger = create_filter_decision_logger()

    for setting_dir in setting_dirs:
        email_account = src.emails.load_email_account(setting_dir)
        rules = src.rules.load_rules(setting_dir)

        logger.info(f"{email_account.email}に接続します。")
        email_client = src.emails.EmailClient.from_email_account(email_account)
        ret = email_client.connect_to_server()
        if not ret:
            logger.error("メールサーバーに接続できませんでした。")
            continue

        emails = email_client.get_emails()
        logger.info(f"{len(emails)}件のメールを取得しました。")

        # 移動フォルダとメールIDのdict
        move_folder_dict: dict[str, list[int]] = {}
        delete_email_ids = []
        action_counts: dict[str, int] = {}
        # フィルタリングルールを適用して削除するメールを特定
        for email_id in emails:
            email_data = email_client.get_email_details(email_id)
            if not email_data:
                logger.error(f"メールの詳細を取得できませんでした: {email_id}")
                continue
            for rule in rules:
                if src.rules.match_rule(rule, email_data):
                    logger.info(f"ルールにマッチしました: {rule}:{email_data['subject']}")
                    if rule.action == "deny":
                        folder = "Spam"
                        move_folder_dict.setdefault(
                            folder, []).append(email_id)
                        log_filter_decision(
                            decision_logger, setting_dir, email_id, "deny", folder, rule, email_data
                        )
                    elif rule.action == "move":
                        folder = rule.move_to
                        move_folder_dict.setdefault(
                            folder, []).append(email_id)
                        log_filter_decision(
                            decision_logger, setting_dir, email_id, "move", folder, rule, email_data
                        )
                    action_counts[rule.action] = action_counts.get(rule.action, 0) + 1
                    break

        logger.info(f"移動フォルダ: {move_folder_dict}")
        logger.info(f"振り分け結果: {action_counts}")

        # メールを指定フォルダに移動
        for folder, email_ids in move_folder_dict.items():
            success_email_ids = email_client.move_emails_to_folder(
                email_ids, folder)
            delete_email_ids.extend(success_email_ids)

        # コピーしたメールを削除
        # メールIDがずれるので、移動後に削除する
        email_client.delete_emails(delete_email_ids)

        email_client.logout()


if __name__ == "__main__":
    main()
