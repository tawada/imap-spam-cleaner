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

        email_client = src.emails.EmailClient.from_email_account(email_account)
        ret = email_client.connect_to_server()
        if not ret:
            print("メールサーバーに接続できませんでした。")
            continue

        emails = email_client.get_emails()

        # 削除するべきメールのリスト
        delete_email_ids = []

        # フィルタリングルールを適用して削除するメールを特定
        for email_id in emails:
            email_data = email_client.get_email_details(email_id)
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
        email_client.move_emails_to_spam(delete_email_ids)

        email_client.logout()



if __name__ == "__main__":
    main()
