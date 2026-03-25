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
            base_url=settings.LLM_BASE_URL, 
            timeout=15.0
        )
        self.model_name = settings.LLM_MODEL_NAME
            
        # 【优化1】：加入“否定出口”和“思维链”的全新 Prompt
        self.system_prompt = """
        你是一个极其严谨的工业安全监控视觉解析引擎。请结合监控画面，检测是否存在明确的违规或危险事件。
        
        【核心原则：宁缺毋滥，拒绝脑补】
        1. "没有违规"是画面的常态。如果没有 100% 的把握看清，或者画面模糊，必须认为“正常”。
        2. 绝不猜测画面外的内容，绝不将正常作业动作误判为违规。
        3. 仅限检测以下9种违规：未戴安全帽、未穿反光衣、高空作业未穿戴安全绳、烟雾或明火、人员倒地、基坑/临边洞口无防护、电箱周边堆放杂物/堵塞、电气设备旁易燃易爆物、脚手架上堆材料。

        【输出规则（极度重要）】
        你必须且只能返回一个合法的 JSON 对象，不要包含 ```json 标记。
        
        你必须先在 `scene_description` 中客观描述画面里的人和物，然后再判断是否有违规！

        如果画面正常（无明确违规），严格按此格式返回：
        {
            "scene_description": "画面中有一名工人正在行走，头部佩戴了黄色安全帽...",
            "has_issue": false,
            "alerts": []
        }

        如果有上述9种明确违规之一，返回百分比坐标（x:左上角X百分比, y:左上角Y百分比, w:宽度百分比, h:高度百分比，值在0-100之间）：
        {
            "scene_description": "画面左侧有一名工人正在操作，但他头上没有佩戴安全帽...",
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
                            {"type": "text", "text": "请仔细检查此监控画面是否有安全隐患。先描述画面，再给出结论。"},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                # # 【优化2】：在这里设置 temperature 和 top_p 降低幻觉
                # temperature=0.1,  # 极低温度：让模型变得极其保守和确定，不再发散思维
                # top_p=0.5         # 核心采样：进一步限制它产生“意外”词汇的概率
            )
            
            print("====== 大模型返回结果 ======")
            print(response.choices[0].message.content)
            print("==========================")

            result_str = response.choices[0].message.content
            
            # 清洗大模型返回的“脏数据”
            result_str = result_str.replace("```json", "").replace("```", "").strip()
            
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx+1]
            else:
                json_str = result_str
                
            parsed_data = json.loads(json_str)
            
            parsed_data["analyze_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            parsed_data["camera"] = camera_name
            
            return parsed_data
            
        except Exception as e:
            print(f"[{camera_name}] 画面解析出错: {e}")
            return {"has_issue": False, "alerts": [], "error": str(e)}