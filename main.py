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

        # 移動フォルダとメールIDのdict
        move_folder_dict: dict[str, list[int]] = {}
        delete_email_ids = []
        print(f"{len(emails)}件のメールを取得しました。")
        # フィルタリングルールを適用して削除するメールを特定
        for email_id in emails:
            email_data = email_client.get_email_details(email_id)
            if not email_data:
                print(f"メールの詳細を取得できませんでした: {email_id}")
                continue
            for rule in rules:
                if src.rules.match_rule(rule, email_data):
                    print(f"ルールにマッチしました: {rule}:{email_data['subject']}")
                    if rule.action == "deny":
                        folder = "Spam"
                        move_folder_dict.setdefault(folder, []).append(email_id)
                    elif rule.action == "move":
                        folder = rule.move_to
                        move_folder_dict.setdefault(folder, []).append(email_id)
                    break

        print(f"移動フォルダ: {move_folder_dict}")

        # メールを指定フォルダに移動
        for folder, email_ids in move_folder_dict.items():
            success_email_ids = email_client.move_emails_to_folder(email_ids, folder)
            delete_email_ids.extend(success_email_ids)

        # コピーしたメールを削除
        # メールIDがずれるので、移動後に削除する
        email_client.delete_emails(delete_email_ids)

        email_client.logout()


if __name__ == "__main__":
    main()
