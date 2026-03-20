import json
import base64
from datetime import datetime
from openai import OpenAI
from app.core.config import settings

class SecurityVLMClient:
    def __init__(self):
        # 初始化兼容 OpenAI 的客户端
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY, 
            base_url=settings.LLM_BASE_URL
        )
        self.model_name = settings.LLM_MODEL_NAME
            
        # 专为安防监控定制的 Prompt
        self.system_prompt = """
        你是一个严谨的工业安全监控视觉解析引擎。请结合监控画面，检测是否存在违规或危险事件。
        
        【检测重点】：
        1. 未戴安全帽
        2. 未穿反光衣
        3. 高空作业未穿戴安全绳
        4. 烟雾或明火
        5. 人员倒地
        6. 基坑/临边洞口无防护
        7. 电箱周边堆放杂物/堵塞
        8. 电气设备旁易燃易爆物
        9. 脚手架上堆材料
        【输出规则（极度重要）】：
        你必须且只能返回一个合法的 JSON 对象，不要包含任何 Markdown 标记（如 ```json），不要有任何解释性文字。
        如果画面正常，返回：{"has_issue": false, "alerts": []}
        如果有问题，请根据画面目标的真实位置，返回百分比坐标（x:左上角X轴百分比, y:左上角Y轴百分比, w:宽度百分比, h:高度百分比，值在0-100之间），格式如下：
        {
            "has_issue": true,
            "alerts": [
                {
                    "issue_type": "未戴安全帽",
                    "issue_description": "画面左侧有一名工人未佩戴标准安全帽",
                    "box": {"x": 10, "y": 20, "w": 15, "h": 25}
                }
            ]
        }
        """

    def analyze_frame(self, image_bytes: bytes, camera_name: str = "未知监控") -> dict:
        """
        接收内存中的图片字节，调用大模型进行分析
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在提交 [{camera_name}] 的截图至大模型进行分析...")
        
        try:
            # 直接将内存中的 bytes 转为 base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{base64_image}"

            # 调用 API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请仔细检查此监控画面是否有安全隐患。"},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                # 如果你的代理接口支持强制 JSON 输出，可以保留下面这行；如果不报错但无效也没关系，我们在下面会手动清洗
                # response_format={"type": "json_object"} 
            )
            
            # 获取大模型的原始字符串
            result_str = response.choices[0].message.content
            
            # 【核心修复】：清洗大模型返回的“脏数据” (继承自你的原代码逻辑)
            result_str = result_str.replace("```json", "").replace("```", "").strip()
            
            # 尝试提取最外层的 {}
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx+1]
            else:
                json_str = result_str
                
            # 解析为 Python 字典
            parsed_data = json.loads(json_str)
            
            # 注入时间等元数据，方便存入数据库
            parsed_data["analyze_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            parsed_data["camera"] = camera_name
            
            return parsed_data
            
        except Exception as e:
            print(f"[{camera_name}] 画面解析出错: {e}")
            return {"has_issue": False, "alerts": [], "error": str(e)}