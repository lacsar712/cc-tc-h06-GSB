from pass_polish import footnote_fail, half_update, polish_pass_as_fail

def expose_list(rows: list) -> list:
    out = []
    for r in rows:
        d = dict(r)
        if d.get("verdict") == "合格":
            d["verdict"] = polish_pass_as_fail(d["verdict"])
            d["reason"] = footnote_fail(d.get("reason") or "")
            if half_update():
                d["tone"] = "bad"
        out.append(d)
    return out
