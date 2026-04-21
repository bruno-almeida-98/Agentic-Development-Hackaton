from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://chat:chat@localhost:5432/chatdb"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "dev-secret-key"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB
    MAX_IMAGE_SIZE: int = 3 * 1024 * 1024  # 3 MB
    SESSION_COOKIE: str = "chat_session"
    AFK_TIMEOUT_SECONDS: int = 60  # 1 minute per spec

    class Config:
        env_file = ".env"


settings = Settings()
