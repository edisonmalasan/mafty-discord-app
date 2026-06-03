import json
import os

from config import USERS_FILE


def load_users() -> set[int]:
    if not os.path.exists(USERS_FILE):
        return set()

    with open(USERS_FILE, "r") as f:
        data = json.load(f)
        return set(data.get("allowed_users", []))


def save_users(users: set[int]) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump({"allowed_users": list(users)}, f, indent=2)


def is_allowed(user_id: int) -> bool:
    return user_id in load_users()
