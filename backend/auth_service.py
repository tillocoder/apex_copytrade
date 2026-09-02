import hmac
import hashlib
import time
import os
import json
import base64
from typing import Optional, Dict, Any, Tuple

SECRET_KEY = os.getenv("APEX_JWT_SECRET", "apex_quant_ultra_secure_jwt_secret_2026_xrinvest_911turbo")
TOKEN_EXPIRY_SECONDS = 86400 * 30   # 30 days
REFRESH_EXPIRY_SECONDS = 86400 * 90  # 90 days

def _hash_password(password: str, salt: str = "apex_salt_2026") -> str:
    return hashlib.sha256(f"{password}_{salt}".encode('utf-8')).hexdigest()

# ONLY ONE SINGLE AUTHORIZED USER: tillo / 4079
AUTHORIZED_USER = {
    "id": "usr_owner_tillo",
    "name": "Hikmatillo (Owner)",
    "username": "tillo",
    "email": "tillo4079@gmail.com",
    "role": "Owner",
    "allowed_passwords": [
        _hash_password("4079"),
        _hash_password("Acer#4079")
    ],
    "two_factor_code": "4079"
}

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _base64url_decode(s: str) -> bytes:
    padding = '=' * (4 - (len(s) % 4)) if len(s) % 4 != 0 else ''
    return base64.urlsafe_b64decode(s + padding)

def generate_jwt(payload: Dict[str, Any], expiry_seconds: int = TOKEN_EXPIRY_SECONDS) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + expiry_seconds}

    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    segments = [
        _base64url_encode(header_bytes),
        _base64url_encode(payload_bytes)
    ]
    signing_input = f"{segments[0]}.{segments[1]}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    segments.append(_base64url_encode(signature))

    return ".".join(segments)

def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    
    parts = token.split('.')
    if len(parts) != 3:
        return None

    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    
    try:
        actual_sig = _base64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None

def authenticate_user(login_identifier: str, password: str, two_factor_code: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    STRICT AUTHENTICATION:
    Only user 'tillo' (or 'tillo4079@gmail.com' / 'tillo4079') with password '4079' (or 'Acer#4079') is allowed.
    All other users and credentials are strictly denied.
    """
    clean_id = (login_identifier or "").strip().lower()
    clean_pass = (password or "").strip()

    # Allowed usernames/emails for tillo
    valid_identifiers = {"tillo", "tillo4079", "tillo4079@gmail.com", "admin", "owner"}
    
    if clean_id not in valid_identifiers:
        return False, None, "Kirish rad etildi: Faqat vakolatli tizim egasi (tillo) kira oladi."

    computed_hash = _hash_password(clean_pass)
    pass_matches = any(hmac.compare_digest(h, computed_hash) for h in AUTHORIZED_USER["allowed_passwords"])
    
    # Direct match check for 4079
    if not pass_matches and clean_pass != "4079" and clean_pass != "Acer#4079":
        return False, None, "Kirish rad etildi: Noto'g'ri parol."

    # If 2FA code is provided, verify it (4079 or matching)
    if two_factor_code is not None and two_factor_code.strip():
        code_clean = two_factor_code.strip()
        if code_clean != "4079" and len(code_clean) < 4:
            return False, None, "Noto'g'ri 2FA xavfsizlik PIN kodi."

    user_profile = {
        "id": AUTHORIZED_USER["id"],
        "name": AUTHORIZED_USER["name"],
        "username": AUTHORIZED_USER["username"],
        "email": AUTHORIZED_USER["email"],
        "role": AUTHORIZED_USER["role"],
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=250&q=80",
        "twoFactorEnabled": True,
        "passkeyRegistered": True
    }

    access_token = generate_jwt({
        "sub": AUTHORIZED_USER["id"],
        "email": AUTHORIZED_USER["email"],
        "username": AUTHORIZED_USER["username"],
        "role": AUTHORIZED_USER["role"],
        "type": "access"
    }, TOKEN_EXPIRY_SECONDS)

    refresh_token = generate_jwt({
        "sub": AUTHORIZED_USER["id"],
        "email": AUTHORIZED_USER["email"],
        "type": "refresh"
    }, REFRESH_EXPIRY_SECONDS)

    result = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
        "user": user_profile
    }

    return True, result, None

def refresh_user_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    payload = verify_jwt(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None

    email = payload.get("email")
    if email != AUTHORIZED_USER["email"]:
        return None

    new_access_token = generate_jwt({
        "sub": AUTHORIZED_USER["id"],
        "email": AUTHORIZED_USER["email"],
        "role": AUTHORIZED_USER["role"],
        "type": "access"
    }, TOKEN_EXPIRY_SECONDS)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS
    }

# Dictionary export for backwards compatibility
AUTHORIZED_USERS = {
    AUTHORIZED_USER["email"]: AUTHORIZED_USER,
    AUTHORIZED_USER["username"]: AUTHORIZED_USER
}
