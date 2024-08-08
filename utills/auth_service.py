from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from functools import wraps
import jwt

app = FastAPI()

# 配置JWT的密钥、算法和过期时间（30分钟）
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 定义了一个字典存储用户名和密码的哈希
USERS = {
    "john": "$2b$12$9D8LgjzZJ4lF1oKqJZyvqe...",  # 哈希后的密码
}

# 创建一个密码上下文实例，这里使用了bcrypt加密方案，并设置自动处理过时的加密方式
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建一个OAuth2PasswordBearer实例，指定了获取token的URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 定义了一个Pydantic模型Token，用于表示JWT的响应结构
class Token(BaseModel):
    access_token: str
    token_type: str

# 定义了一个 Pydantic 模型 TokenData，用于存储 JWT 中可能携带的用户名
class TokenData(BaseModel):
    username: Optional[str] = None

# 定义一个函数verify_password，用于验证明文密码与哈希后的密码是否匹配
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 定义一个函数 authenticate_user，用于验证用户的用户名和密码。如果用户名不存在或者密码
# 错误，则返回False；否则返回用户名
def authenticate_user(username: str, password: str):
    user_hashed_password = USERS.get(username)
    if not user_hashed_password:
        return False
    if not verify_password(password, user_hashed_password):
        return False
    return username

# JWT 生成函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 解码函数
def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# JWT 验证装饰器
def jwt_required():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token = kwargs.get("request").headers.get("Authorization")
            if not token or not token.startswith("Bearer "):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
            token = token.split(" ")[1]
            username = decode_jwt(token)
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            kwargs["current_user"] = username
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 获取当前用户
def get_jwt_identity(token: str = Depends(oauth2_scheme)):
    username = decode_jwt(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username

# 定义了一个POST路由/ token，用于处理用户登录并生成JWT。它接收OAuth2PasswordRequestForm
# 类型的数据，调用authenticate_user函数验证用户，如果验证失败则抛出 HTTPException异常。
# 如果验证成功，则调用 create_access_token 生成JWT，并返回JWT的响应
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 保护路由
@app.get("/users/me")
@jwt_required()
async def read_users_me(current_user: str = Depends(get_jwt_identity)):
    return {"current_user": current_user}