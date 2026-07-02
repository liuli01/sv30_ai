"""SV30 AI 识别服务"""

import os

import dotenv
import loguru
import requests
from fastapi import FastAPI, responses
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

loguru.logger.add(
    "log/app.log",
    rotation="5 MB",
    retention="90 days",
    compression="zip",
    enqueue=True,
)
logger = loguru.logger

# 状态码（对接方依赖，不可随意修改）
OK = "0"
SERVERERR = "500"

app = FastAPI(redoc_url=None)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_request, exc: RuntimeError):
    logger.error("请求异常: {}", exc)
    return responses.JSONResponse(
        status_code=500, content={"detail": SERVERERR, "message": str(exc)}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GET_IMAGE_URL = str(os.getenv("GET_IMAGE_URL"))
WORKFLOW = os.getenv("WORKFLOW", "sv30")
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:9924").strip()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8005").strip()
WORKFLOW_URL = f"{API_URL}/v1/workflow/execute"
CAMERA_API = GET_IMAGE_URL.split("/ipccamera")[0]


def call_workflow(
    image_url: str, server_url: str = ""
) -> tuple[float, float]:
    """调用 workflow 接口进行识别，返回 (sv30, max_conf)。"""
    server_url = server_url or SERVER_URL
    url = WORKFLOW_URL
    payload = {"workflow": WORKFLOW, "image_url": image_url, "server_url": server_url}
    logger.info("调用 workflow, image_url={}", image_url)

    try:
        resp = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as e:
        logger.error("workflow 通讯失败: {}", e)
        raise RuntimeError(f"workflow 通讯失败: {e}")

    if resp.status_code != 200:
        logger.error("workflow 返回异常 {}, body={}", resp.status_code, resp.text)
        raise RuntimeError(f"workflow 返回 {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
    except ValueError as e:
        logger.error("workflow 响应非 JSON: {}", resp.text)
        raise RuntimeError(f"workflow 响应格式错误: {e}")

    try:
        node = data["node_outputs"]["3"]
    except (KeyError, TypeError) as e:
        logger.error("workflow 缺少 node_outputs[3]: body={}", data)
        raise RuntimeError(f"workflow 缺少 node_outputs[3]: {e}")

    try:
        values = node["computed_values"]
    except (KeyError, TypeError) as e:
        logger.error("workflow 缺少 computed_values: node={}", node)
        raise RuntimeError(f"workflow 缺少 computed_values: {e}")

    if not values:
        logger.warning("workflow 未检出结果, value=0, max_conf=0")
        return 0.0, 0.0

    try:
        raw = values[0]
        raw_conf = data["max_conf"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error("workflow 数据字段缺失: values={}, body={}", values, data)
        raise RuntimeError(f"workflow 缺少字段: {e}")

    try:
        value = round(float(raw), 4)
        max_conf = round(float(raw_conf), 4)
    except (ValueError, TypeError) as e:
        logger.error("workflow 值非数值: raw={}, conf={}", raw, raw_conf)
        raise RuntimeError(f"workflow 值格式异常: {e}")

    logger.info("识别成功: value={}, max_conf={}", value, max_conf)
    return value, max_conf


@app.get("/")
def index():
    return {"service": "sv30_ai"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ── 业务端点 ────────────────────────────────────────
# 所有端点共享的逻辑：从摄像头获取截图 → 调用 workflow → 返回结果


class TestBody(BaseModel):
    image_url: str
    server_url: str = ""


def _fetch_image_url() -> str:
    """请求摄像头截图接口，返回可直接访问的图片 URL。"""
    resp = requests.get(GET_IMAGE_URL, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError("视频截图接口网络通讯失败")
    data = resp.json()
    if data.get("state") != "success":
        raise RuntimeError("视频截图接口程序报错")
    return f"{CAMERA_API}{data['url']}"


@app.post("/v1/object-detection/yolov5s/water")
async def detection_water():
    """识别污水中的清水含量。"""
    image_url = _fetch_image_url()
    sv30, conf = call_workflow(image_url=image_url)
    water = round(1 - sv30, 4)
    logger.info("water 检测成功: {}%, conf={}", water * 100, conf)
    return {
        "detail": OK,
        "water_percent": water,
        "water_confidence": conf,
        "sPicFileName": image_url,
    }


@app.post("/v1/object-detection/yolov5s/sewage")
async def detection_sewage():
    """识别污水含量。"""
    image_url = _fetch_image_url()
    sv30, conf = call_workflow(image_url=image_url)
    logger.info("sewage 检测成功: {}%, conf={}", sv30 * 100, conf)
    return {
        "detail": OK,
        "sewage_percent": sv30,
        "sewage_confidence": conf,
        "sPicFileName": image_url,
    }


@app.post("/v1/object-detection/yolov5s/test")
async def detection_test(body: TestBody):
    """测试端点：直接传入图片 URL 进行识别，不走摄像头截图。"""
    if not body.image_url:
        return responses.JSONResponse(
            status_code=400,
            content={"detail": SERVERERR, "message": "缺少 image_url"},
        )
    sv30, conf = call_workflow(image_url=body.image_url, server_url=body.server_url)
    logger.info("test 检测成功: {}%, conf={}", sv30 * 100, conf)
    return {
        "detail": OK,
        "sewage_percent": sv30,
        "sewage_confidence": conf,
        "sPicFileName": body.image_url,
    }
