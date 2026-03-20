import os

class Settings:
    # --- LLM 模型配置 (参考自你的 settings.py) ---
    LLM_API_KEY = "0fdd0bfcc78113400f51761527886029"
    LLM_BASE_URL = "https://jcpt-open.cscec.com/aijsxmywyapi/0510250001/v1.0/qwen_vl_max_public"
    LLM_MODEL_NAME = "qwen-vl-max"

    # --- 数据库配置 (后续集成 SQLAlchemy 会用到) ---
    MYSQL_HOST = "127.0.0.1"
    MYSQL_PORT = 3306
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "123456"
    MYSQL_DATABASE = "jianbing_db" # 建议换个针对此项目的新库名

settings = Settings()