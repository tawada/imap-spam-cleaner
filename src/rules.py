import yaml
import pydantic
from typing import Literal


class Rule(pydantic.BaseModel):
    """Email filtering rule."""
    action: Literal["allow", "deny"]
    sender_top_level_domain: str | None = None
    sender_name: str | None = None
    body_contains: str | None = None
    subject_contains: str | None = None


def load_rules(path: str) -> list[Rule]:
    """Load rules from a YAML file."""
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
        sender_name = email_data["from"].split(" ")[0]
        if sender_name[0] == "=":
            sender_name = decode_mime_words(sender_name)
        if rule.sender_name not in sender_name:
            return False

    if rule.subject_contains and rule.subject_contains not in email_data.get("subject", ""):
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
