"""鉴权路由（docs/07 §2.1）。"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api import deps, schemas
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/registration", response_model=schemas.RegisterStatusResponse)
def registration_status() -> schemas.RegisterStatusResponse:
    """首次打开 Web 时用它决定展示注册还是登录。"""
    return schemas.RegisterStatusResponse(registrationOpen=auth.registration_open())


@router.post("/register", response_model=schemas.LoginResponse)
def register(payload: schemas.RegisterRequest, device: deps.OptionalDevice) -> schemas.LoginResponse:
    """首个账号注册成功后直接返回令牌，客户端不必再登一次。"""
    return auth.register(payload, device)


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, device: deps.OptionalDevice) -> schemas.LoginResponse:
    return auth.login(payload, device)


@router.post("/refresh", response_model=schemas.RefreshResponse)
def refresh(payload: schemas.RefreshRequest, device: deps.OptionalDevice) -> schemas.RefreshResponse:
    """refresh 滚动：返回新的一对令牌，客户端必须覆盖旧值。"""
    return auth.refresh(payload, device)


@router.get("/me", response_model=schemas.MeResponse)
def me(claim: deps.CurrentClaim) -> schemas.MeResponse:
    return auth.me(claim["sub"])


@router.patch("/profile", response_model=schemas.UserView)
def update_profile(
    payload: schemas.ProfileUpdateRequest, claim: deps.CurrentClaim
) -> schemas.UserView:
    """改昵称 / 换头像。头像以 data URL 上传，服务端落盘后返回可访问地址。"""
    return auth.update_profile(claim["sub"], payload)


@router.put("/password", status_code=204, response_class=Response)
def change_password(
    payload: schemas.PasswordUpdateRequest, claim: deps.CurrentClaim
) -> Response:
    """改密成功后其他设备的 refresh 立即失效，当前设备需重新登录。"""
    auth.change_password(claim["sub"], payload)
    return Response(status_code=204)


@router.get("/avatar")
def avatar(u: str) -> Response:
    """头像图片。`u` 是用户 ID；不带鉴权头，便于 <img> 直接引用。"""
    data = auth.read_avatar(u)
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-cache"})


@router.post("/logout", status_code=204, response_class=Response)
def logout(device: deps.CurrentDevice) -> Response:
    auth.logout(device)
    return Response(status_code=204)
