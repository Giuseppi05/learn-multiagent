from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_user
from app.db import get_db
from app.orchestrator import latest_profile
from app.schemas import PasswordChange
from app.serializers import classroom_view, user_view
from app.supabase_admin import AuthAdmin, get_auth_admin

router = APIRouter(prefix="/me", tags=["cuenta"])


@router.get("")
def me(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    out = {"user": user_view(user.user)}
    if user.student:
        st = user.student
        out["student"] = {"id": st.id, "code": st.code, "classroom": classroom_view(st.classroom), "has_profile": latest_profile(db, st.id) is not None}
    return out


@router.post("/password", status_code=204)
def change_password(body: PasswordChange, user: CurrentUser = Depends(current_user), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    """Primer ingreso del personal: reemplaza la contraseña temporal. Los estudiantes usan el PIN que les da su docente."""
    admin.set_password(user.id, body.password)
    user.user.must_change_password = False
    db.commit()
