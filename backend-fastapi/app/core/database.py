from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# 拼接 MySQL 连接字符串 (使用 pymysql 驱动)
#格式: mysql+pymysql://user:root@host:123456/database
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

# 如果你现在还没建好 MySQL，可以先临时用 SQLite 跑通逻辑，把上面那行注释掉，用下面这行：
# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # 如果用 SQLite 加上下面这个参数，MySQL 则不需要
    # connect_args={"check_same_thread": False} 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 获取数据库 Session 的依赖函数 (供 FastAPI 路由使用)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()