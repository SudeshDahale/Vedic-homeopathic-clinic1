from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# ─────────────────────────────────────────────────────
# Password Hashing
# WHY:
# Even if DB leaks, passwords remain protected
# ─────────────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Convert plain password into secure bcrypt hash
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify entered password matches stored hash
    """
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ─────────────────────────────────────────────────────
# JWT Access Token Creation
# WHY JWT:
# Stores user_id, clinic_id, role
# No DB hit required every request
# Faster + scalable SaaS architecture
# ─────────────────────────────────────────────────────
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:

    payload = data.copy()

    # Token expiry
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )

    payload.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


# ─────────────────────────────────────────────────────
# Decode JWT Token
# WHY:
# Reads token safely
# Returns payload if valid
# Returns None if invalid/expired
# ─────────────────────────────────────────────────────
def decode_token(
    token: str
) -> Optional[dict]:

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        return payload

    except JWTError:
        return None