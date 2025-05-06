import os
import re
from typing import Literal

import pydantic
import yaml


class Rule(pydantic.BaseModel):
    """Email filtering rule."""

    action: Literal["allow", "deny", "move"]
    move_to: str | None = None
    sender_top_level_domain: str | None = None
    sender_name: list[str] | str | None = None
    body_contains: str | None = None
    subject_contains: list[str] | str | None = None

    def validate(self) -> None:
        """Validate the rule."""
        if self.action == "move" and not self.move_to:
            raise ValueError("move_to must be specified when action is 'move'")

    def __str__(self) -> str:
        """String representation of the rule."""
        # Noneのattrは表示しない
        attrs = self.__dict__.copy()
        attrs = {k: v for k, v in attrs.items() if v is not None}
        # class名を取得
        class_name = self.__class__.__name__
        # attrsを文字列に変換
        attrs_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
        # 文字列を返す
        return f"{class_name}({attrs_str})"


def load_rules(setting_dir: str) -> list[Rule]:
    """Load rules from a YAML file."""
    path_template = "settings/{setting_dir}/filtering_rules.yaml"
    path = path_template.format(setting_dir=setting_dir)
    # settings/{setting_dir}/filtering_rules.yamlが存在するか確認
    if not os.path.exists(path):
        # デフォルトの設定を使用
        path = path_template.format(setting_dir="default")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Settings file not found: {path}")

    # settings/{setting_dir}/filtering_rules.yamlを読み込む
    with open(path, "r") as f:
        rules = yaml.safe_load(f)

    # ルールを検証
    for rule in rules:
        Rule(**rule).validate()
    return [Rule(**rule) for rule in rules]


def match_rule(rule: Rule, email_data: dict) -> bool:
    """Check if the email matches the rule."""

    if rule.sender_top_level_domain:
        sender = export_sender(email_data["from"])
        if not sender.endswith(rule.sender_top_level_domain):
            return False

    if rule.sender_name:
        sender_name = export_sender_name(email_data["from"])
        if not contains_all_words(sender_name, rule.sender_name):
            return False

    if rule.subject_contains:
        subject = email_data.get("subject", "")
        if not contains_all_words(subject, rule.subject_contains):
            return False

    if rule.body_contains:
        # 未実装
        return False

    return True


def contains_all_words(base_str: str, words: list[str] | str):
    """The string contains all words."""
    if isinstance(words, str):
        words = [words]

    # 大文字小文字を区別しないようにする
    base_str = base_str.lower()
    words = [word.lower() for word in words]

    return all(word in base_str for word in words)    


def decode_mime_words(s: str) -> str:
    """Decode MIME words in a string."""
    import email.header

    decoded_words = email.header.decode_header(s)
    decoded_string = "".join(
        str(word, encoding if isinstance(word, bytes) else "utf-8")
        for word, encoding in decoded_words
        if isinstance(word, bytes)
    )
    return decoded_string


def export_sender(email: str) -> str:
    """Export sender from email address."""
    # <hoge@fuga.com>の括弧の中を正規表現でマッチさせる
    pattern = re.compile(r"<([^>]+)>")
    # マッチした部分を取得
    match = pattern.search(email)
    if match:
        # マッチした部分を返す
        return match.group(1)
    # マッチしなかった場合はそのまま返す
    return email


def export_sender_name(sender: str) -> str:
    """Export sender name from email address."""
    # =? .... ?= の部分をマッチさせる
    pattern = re.compile(r"(=\?[^?]+\?[BbQq]\?[^?]+\?=)")
    # すべてのマッチを取得
    matches = pattern.findall(sender)
    # デコードされた文字列を格納するリスト
    decoded_strings = []
    # マッチした部分をデコード
    for encoded_text in matches:
        decoded_string = decode_mime_words(encoded_text)
        decoded_strings.append(decoded_string)
    # デコードされた文字列を結合して返す
    decoded_sender = "".join(decoded_strings)

    if not decoded_sender:
        decoded_sender = sender.split(" <")[0].strip()

    return decoded_sender
