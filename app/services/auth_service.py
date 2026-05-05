from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.security import hash_password, verify_password, create_access_token

def register_user(db: Session, data: RegisterRequest) -> User:
    """
    Create new Doctor or Receptionist account.
    WHY check duplicate: one phone = one account, prevents confusion.
    """
    # Check if phone already exists
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    user = User(
        clinic_id = data.clinic_id,
        name      = data.name,
        phone     = data.phone,
        email     = data.email,
        password  = hash_password(data.password),
        role      = UserRole.DOCTOR if data.role == "DOCTOR" else UserRole.RECEPTIONIST
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, data: LoginRequest) -> dict:
    """
    Verify credentials and return JWT token.
    WHY: Token contains role — frontend shows different UI based on this.
    Doctor sees analytics. Receptionist sees queue only.
    """
    user = db.query(User).filter(User.phone == data.phone).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your doctor."
        )

    # Create token with user info embedded
    token = create_access_token({
        "user_id":   user.id,
        "clinic_id": user.clinic_id,
        "role":      user.role.value,
        "name":      user.name
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user.role.value,
        "name":         user.name,
        "clinic_id":    user.clinic_id,
        "user_id":      user.id
    }

def get_user_by_id(db: Session, user_id: str) -> User:
    """Get current user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user