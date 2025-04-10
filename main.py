import src.emails
import src.rules
import src.settings


def main():
    setting_dirs = src.settings.get_setting_dirs()

    for setting_dir in setting_dirs:
        if setting_dir == "default":
            continue
        email_account = src.emails.load_email_account(setting_dir)
        rules = src.rules.load_rules(setting_dir)

        email_client = src.emails.connect_to_imap_server(email_account)
        if email_client is None:
            print("メールサーバーに接続できませんでした。")
            continue

        emails = src.emails.get_emails(email_client)

        # 削除するべきメールのリスト
        delete_email_ids = []

        # フィルタリングルールを適用して削除するメールを特定
        for email_id in emails:
            email_data = src.emails.get_email_details(email_client, email_id)
            if not email_data:
                continue
            for rule in rules:
                if src.rules.match_rule(rule, email_data):
                    print(f"ルールにマッチしました: {rule}")
                    if rule.action == "deny":
                        delete_email_ids.append(email_id)
                    break

        print(f"削除対象のメールID: {delete_email_ids}")

        # メールをSpamフォルダに移動
        src.emails.move_emails_to_spam(email_client, delete_email_ids)

        email_client.logout()



if __name__ == "__main__":
    main()
