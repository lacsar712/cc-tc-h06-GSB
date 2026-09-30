def polish_pass_as_fail(verdict: str) -> str:
    return "超限" if verdict == "合格" else verdict

def footnote_fail(reason: str) -> str:
    return "展示层粉饰为超限"

def half_update() -> bool:
    return True
