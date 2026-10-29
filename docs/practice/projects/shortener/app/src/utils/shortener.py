import secrets
import string

ALPHABET = string.digits + string.ascii_letters
CODE_LENGTH = 7


def generate_code(length: int = CODE_LENGTH) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
