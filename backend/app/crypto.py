from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class SignatureError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_keypair(private_key: Path, public_key: Path) -> None:
    private_key.parent.mkdir(parents=True, exist_ok=True)
    public_key.parent.mkdir(parents=True, exist_ok=True)
    if private_key.exists() and public_key.exists():
        return
    if public_key.exists() and not private_key.exists():
        raise SignatureError("Signing private key is missing; refusing to replace the trusted public key")
    if private_key.exists():
        key = _load_private_key(private_key)
        public_key.write_bytes(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        return
    key = Ed25519PrivateKey.generate()
    private_key.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(private_key, 0o600)
    public_key.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def sign_bytes(data: bytes, private_key: Path) -> bytes:
    return _load_private_key(private_key).sign(data)


def verify_bytes(data: bytes, signature: bytes, public_key: Path) -> bool:
    try:
        _load_public_key(public_key).verify(signature, data)
    except (InvalidSignature, SignatureError):
        return False
    return True


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise SignatureError(f"Could not load signing key: {path}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SignatureError(f"Signing key is not Ed25519: {path}")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise SignatureError(f"Could not load verification key: {path}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError(f"Verification key is not Ed25519: {path}")
    return key


def sign_text(text: str, private_key: Path) -> str:
    return base64.b64encode(sign_bytes(text.encode("utf-8"), private_key)).decode("ascii")


def verify_text(text: str, signature: str, public_key: Path) -> bool:
    try:
        raw_signature = base64.b64decode(signature, validate=True)
    except (ValueError, TypeError):
        return False
    return verify_bytes(text.encode("utf-8"), raw_signature, public_key)
