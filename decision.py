
def make_decision(score):
    if score >= 0.7:
        return "HIGH RISK"
    elif score >= 0.4:
        return "SUSPICIOUS"
    else:
        return "NORMAL"


def get_action(score):
    if score >= 0.7:
        return "BACKUP + ALERT"
    elif score >= 0.4:
        return "SHOW WARNING"
    else:
        return "ALLOW OPERATION"