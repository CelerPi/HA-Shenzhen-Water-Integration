from __future__ import annotations

import base64
import json
import random
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_CHARS = "abacdefghjklmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ0123456789"


def random_header(length: int = 32) -> str:
    value = []
    for index in range(length):
        char_index = random.randrange(len(_CHARS))
        if index == 0 and char_index >= len(_CHARS) - 10:
            char_index = random.randrange(len(_CHARS) - 10)
        value.append(_CHARS[char_index])
    return "".join(value)


def encrypt_payload(payload: dict[str, Any], header_value: str) -> str:
    plain = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    cipher = AES.new(_key_from_header(header_value), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(plain, AES.block_size))).decode("ascii")


def decrypt_response(response_body: str, header_value: str) -> dict[str, Any]:
    encrypted = response_body.strip()
    if encrypted.startswith('"') and encrypted.endswith('"'):
        encrypted = json.loads(encrypted)
    encrypted = encrypted[:7] + encrypted[20:] + encrypted[7:20]
    cipher = AES.new(_key_from_header(header_value), AES.MODE_ECB)
    plain = unpad(cipher.decrypt(base64.b64decode(encrypted)), AES.block_size)
    return json.loads(plain.decode("utf-8"))


def _key_from_header(header_value: str) -> bytes:
    return f"33F4A3D6{header_value[8:24]}A9E19798".encode("utf-8")
