import yaml
import pydantic
from typing import Literal


class Rule(pydantic.BaseModel):
    """Email filtering rule."""
    action: Literal["allow", "deny"]
    sender_top_level_domain: str | None = None
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
        sender_domain = sender.split("@")[-1]
        if sender_domain.endswith(rule.sender_top_level_domain):
            return True
        return False
    if rule.subject_contains and rule.subject_contains not in email_data.get("subject", ""):
        return False
    if rule.body_contains:
        # 未実装
        return False
    return True
