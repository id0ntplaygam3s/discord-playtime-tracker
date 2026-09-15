from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class AccountLoginRequest(BaseModel):
    user_id: int
    password: str


class RegisterOptionsUser(BaseModel):
    id: int
    username: str
    display_name: str


class RegisterRequest(BaseModel):
    user_id: int
    password: str
    confirm_password: str


class RegisterResponse(BaseModel):
    status: str


class PasswordResetRequestPayload(BaseModel):
    user_id: int


class PasswordResetCompleteRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str


class MeResponse(BaseModel):
    username: str
    role: str
    role_name: str
    is_guest: bool
    account_status: str | None = None
    tracked_user_id: int | None = None
    permissions: list[str] = []
