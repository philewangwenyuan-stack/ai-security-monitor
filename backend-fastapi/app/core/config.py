import os

class Settings:
    # --- LLM 模型配置 ---
    LLM_API_KEY = "0fdd0bfcc78113400f51761527886029"
    # LLM_BASE_URL = "https://jcpt-open.cscec.com/aijsxmywyapi/0510250001/v1.0/qwen_vl_max_public"
    LLM_BASE_URL = "https://jcpt.cscec.com/aijsxmywyapi/0510220001/v1.0/qwen_vl_max_public"
                    
    LLM_MODEL_NAME = "qwen-vl-max"

    # --- 数据库配置 
    MYSQL_HOST = "172.20.22.115"
    MYSQL_PORT = 3306
    MYSQL_USER = "zxpSQL"
    MYSQL_PASSWORD = "zxpSQL1234"
    MYSQL_DATABASE = "jianbing_db" 


    #对象存储配置
    MINIO_ENDPOINT: str = "172.20.22.115:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "adminA123456"
    MINIO_BUCKET_NAME: str = "jianbing-io"
    MINIO_SECURE: bool = False # 默认使用 HTTP

    class Config:
        env_file = ".env"

settings = Settings()