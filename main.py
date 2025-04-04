import src.rules
import src.emails


def main():
    # filtering rules
    rules = src.rules.load_rules("filtering_rules.yaml")

    # email
    email_account = src.emails.load_email_account()

    email_client = src.emails.connect_to_imap_server(
        email_account.imap_server,
        email_account.email,
        email_account.password.get_secret_value(),
    )
    if email_client is None:
        print("メールサーバーに接続できませんでした。")
        return

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

    # メールを削除
    src.emails.delete_emails(email_client, delete_email_ids)

    email_client.logout()



if __name__ == "__main__":
    main()
