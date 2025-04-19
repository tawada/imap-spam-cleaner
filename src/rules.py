import re
from typing import Literal

import pydantic
import yaml


class Rule(pydantic.BaseModel):
    """Email filtering rule."""

    action: Literal["allow", "deny", "move"]
    move_to: str | None = None
    sender_top_level_domain: str | None = None
    sender_name: str | None = None
    body_contains: str | None = None
    subject_contains: str | None = None

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
    try:
        with open(path, "r") as f:
            rules = yaml.safe_load(f)
    except FileNotFoundError:
        # デフォルトの設定を使用
        path = path_template.format(setting_dir="default")
        with open(path, "r") as f:
            rules = yaml.safe_load(f)
    return [Rule(**rule) for rule in rules]


def match_rule(rule: Rule, email_data: dict) -> bool:
    """Check if the email matches the rule."""

    if rule.sender_top_level_domain:
        # <hoge@fuga.com>の括弧の中を正規表現でマッチさせる
        sender = email_data["from"].split("<")[-1].split(">")[0]
        if not sender.endswith(rule.sender_top_level_domain):
            return False

    if rule.sender_name:
        sender_name = export_sender_name(email_data["from"])
        if rule.sender_name not in sender_name:
            return False

    if rule.subject_contains and rule.subject_contains not in email_data.get(
        "subject", ""
    ):
        return False

    if rule.body_contains:
        # 未実装
        return False

    return True


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
