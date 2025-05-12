
"""
Prepare tasks for the master server.
"""

from formatters import FORMATTERS
from utils.master_utils import split_range


def prepare_tasks(format_name: str, minions: list[str]) -> list[dict]:
    """
    Prepare tasks for the master server.
    """
    fmt = FORMATTERS[format_name]
    # split the numeric range according to this formatter
    numeric_slices = split_range(fmt.min_value, fmt.max_value, len(minions))

    tasks_ls = []
    # zip the minions with the numeric slices
    for minion_id, (start, end) in zip(minions, numeric_slices):
        tasks_ls.append({
            "minion":    minion_id,
            "start":     start,
            "end":       end,
            "start_str": fmt.number_to_string(start),
            "end_str":   fmt.number_to_string(end),
        })
    return tasks_ls


if __name__ == "__main__":
    # simulate registered minions
    minions = ["minion-1", "minion-2", "minion-3"]
    tasks = prepare_tasks("israel_phone", minions)

    for t in tasks:
        print(f"{t['minion']}:")
        print(f"  • numeric → {t['start']}  –  {t['end']}")
        print(f"  • formatted → {t['start_str']}  –  {t['end_str']}\n")
