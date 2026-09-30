from h06_list_trap import expose_list
from pass_polish import half_update

def armed() -> bool:
    return half_update()

def sample():
    return expose_list([{"verdict": "合格", "reason": "ok"}])[0]
