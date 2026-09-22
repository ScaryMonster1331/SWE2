from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, Response, request

from sweagent import REPO_ROOT
from sweagent.utils.config import load_environment_variables


def _signature(token: str, timestamp: str, nonce: str, encrypted: str) -> str:
    values = sorted([token, timestamp, nonce, encrypted])
    return hashlib.sha1("".join(values).encode("utf-8")).hexdigest()


def _pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise ValueError("empty decrypted data")
    padding = data[-1]
    if padding < 1 or padding > 32:
        raise ValueError("invalid PKCS7 padding")
    if data[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid PKCS7 padding bytes")
    return data[:-padding]


def decrypt_message(encrypted: str, encoding_aes_key: str) -> tuple[str, str]:
    key = base64.b64decode(encoding_aes_key + "=")
    if len(key) != 32:
        raise ValueError("EncodingAESKey must decode to 32 bytes")
    encrypted_bytes = base64.b64decode(encrypted)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(key[:16])).decryptor()
    plaintext = _pkcs7_unpad(decryptor.update(encrypted_bytes) + decryptor.finalize())
    if len(plaintext) < 20:
        raise ValueError("decrypted message is too short")
    message_length = struct.unpack("!I", plaintext[16:20])[0]
    message_end = 20 + message_length
    message = plaintext[20:message_end].decode("utf-8")
    receive_id = plaintext[message_end:].decode("utf-8")
    return message, receive_id


def _configured_values() -> tuple[str, str, str]:
    token = os.getenv("WECOM_CALLBACK_TOKEN", "").strip()
    encoding_aes_key = os.getenv("WECOM_ENCODING_AES_KEY", "").strip()
    corp_id = os.getenv("WECOM_CORP_ID", "").strip()
    if not token or not encoding_aes_key:
        raise RuntimeError("缺少 WECOM_CALLBACK_TOKEN 或 WECOM_ENCODING_AES_KEY")
    return token, encoding_aes_key, corp_id


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Response:
        return Response("ok", mimetype="text/plain")

    @app.get("/wecom/callback")
    def verify_callback() -> Response:
        token, encoding_aes_key, corp_id = _configured_values()
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        expected = _signature(token, timestamp, nonce, echostr)
        if msg_signature != expected:
            return Response("invalid signature", status=403, mimetype="text/plain")
        message, receive_id = decrypt_message(echostr, encoding_aes_key)
        if corp_id and receive_id != corp_id:
            return Response("invalid receiveid", status=403, mimetype="text/plain")
        return Response(message, mimetype="text/plain")

    @app.post("/wecom/callback")
    def receive_callback() -> Response:
        token, encoding_aes_key, corp_id = _configured_values()
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        try:
            root = ET.fromstring(request.data)
            encrypted = root.findtext("Encrypt", default="")
        except ET.ParseError:
            encrypted = ""
        if not encrypted:
            return Response("success", mimetype="text/plain")
        expected = _signature(token, timestamp, nonce, encrypted)
        if msg_signature != expected:
            return Response("invalid signature", status=403, mimetype="text/plain")
        message, receive_id = decrypt_message(encrypted, encoding_aes_key)
        if corp_id and receive_id != corp_id:
            return Response("invalid receiveid", status=403, mimetype="text/plain")
        inbox = REPO_ROOT / "requirements" / "wecom_inbox.jsonl"
        inbox.parent.mkdir(parents=True, exist_ok=True)
        item = {
            "received_at": datetime.now().isoformat(),
            "corp_id": receive_id,
            "message": message,
        }
        with inbox.open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")
        return Response("success", mimetype="text/plain")

    return app


def main() -> None:
    load_environment_variables(REPO_ROOT / ".env")
    port = int(os.getenv("WECOM_CALLBACK_PORT", "5000"))
    app = create_app()
    print("企业微信回调服务已启动")
    print(f"本地地址: http://127.0.0.1:{port}/wecom/callback")
    print("请使用公网隧道将该地址暴露给企业微信")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
