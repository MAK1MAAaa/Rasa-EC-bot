from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from .models import User, UserCreate, UserRead, Token
from .auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .database import get_session, init_db

app = FastAPI(title="Rasa-EC-bot Backend", version="0.1.0")

# 配置 CORS
origins = [
    "http://localhost:5173",    # Vite 默认开发端口
    "http://127.0.0.1:5173",
    "http://localhost:3000",    # 其他常用前端端口
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # 启动时初始化数据库表
    # await init_db()
    pass

@app.get("/")
async def root():
    return {"message": "Welcome to Rasa-EC-bot API"}

@app.post("/api/v1/auth/register", response_model=UserRead)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # 检查邮箱是否已注册
    statement = select(User).where(User.email == user.email)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: AsyncSession = Depends(get_session)
):
    # 这里 form_data.username 对应邮箱
    statement = select(User).where(User.email == form_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
