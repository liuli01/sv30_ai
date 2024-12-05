#%%
from fastapi import FastAPI,File, UploadFile
import loguru
import os
import shutil
from utils.infer import plot_result,noplot_result
from utils.sv30 import calculate_sv30
import requests
import os
import dotenv
dotenv.load_dotenv()

loguru.logger.add(
    "log/app.log",
    rotation="5 MB",
    retention="90 days",
    compression="zip",
    # serialize=True, 	# serializes log messages to JSON.  Turn off for log files.
     enqueue=True
)
logger=loguru.logger

app = FastAPI(redoc_url=None)

GET_IMAGE_URL=str(os.getenv("GET_IMAGE_URL"))
CAMERA_API=GET_IMAGE_URL.split("/ipccamera")[0]
DETECTION_URL = "/v1/object-detection/yolov5s"
class_name_dict={0:"0",1:"1",2:"10",3:"point",4:"sewage"}

# 报错状态码信息
class RET():
    OK                  = "0"
    DBERR               = "4001"
    NODATA              = "4002"
    DATAEXIST           = "4003"
    DATAERR             = "4004"
    SESSIONERR          = "4101"
    LOGINERR            = "4102"
    PARAMERR            = "4103"
    USERERR             = "4104"
    ROLEERR             = "4105"
    PWDERR              = "4106"
    REQERR              = "4201"
    IPERR               = "4202"
    THIRDERR            = "4301"
    IOERR               = "4302"
    SERVERERR           = "4500"
    UNKOWNERR           = "4501"


@app.get('/',summary="YoloV5FastDeploy")
def index():
    return {"YoloV5FastDeployAPi": "to /docs"}

# 根据上传照片识别
@app.post('/img_upload',summary='图片上传upload,可返回识别后图片url,速度慢')
async  def img_upload(image : UploadFile= File(...)):

    if os.path.exists("upload") or os.path.exists("predict"):
        shutil.rmtree("upload")
        shutil.rmtree("predict")
        os.mkdir("upload")
        os.mkdir("predict")
    else:
        os.mkdir("upload")
        os.mkdir("predict")

    filename =image.filename
    save_path=f"upload/{filename}"
    predict_path=f"predict/{filename}"
    with open(save_path, "wb") as f:
        content = await image.read()
        f.write(content)
    
    results=plot_result(save_path,predict_path)
    sv30=calculate_sv30(results["predictions"]) # type: ignore
    return {"detail":RET.OK,"water_percent":sv30,"water_confidence":0.9,"sPicFileName":save_path}


@app.post(f"{DETECTION_URL}/water",summary='根据图片url，不保存上传文件，不返回识别后图片url，速度识别快')
async def detection_water():
    response = requests.get(GET_IMAGE_URL,timeout=20)

    if response.status_code == 200:
        data = response.json()
        if data["state"] == "success":
            image_url = f"{CAMERA_API}{data['url']}"
            logger.info(image_url)
            results=noplot_result(image_url)
            sv30=calculate_sv30(results["predictions"]) # type: ignore
            water=1-sv30
            logger.info(f"检测成功,water_percent:{water},water_confidence:0.9,sPicFileName:{image_url}")
            return {"detail":RET.OK,"water_percent":water,"water_confidence":0.9,"sPicFileName":image_url}

        else:
            logger.error("视频截图接口程序报错")
            return {"detail": RET.SERVERERR, "message": "视频截图接口程序报错"}

    else:
        logger.error("截图接口通讯失败")
        return {"detail": RET.SERVERERR, "message": "视频截图接口网络通讯失败"}

@app.post(f"{DETECTION_URL}/sewage",summary='根据图片url.不保存上传文件,不返回识别后图片url,速度识别快')
async def detection_sewage():
    response = requests.get(GET_IMAGE_URL,timeout=20)

    if response.status_code == 200:
        data = response.json()
        if data["state"] == "success":
            image_url = f"{CAMERA_API}{data['url']}"
            logger.info(image_url)
            results=noplot_result(image_url)
            sv30=calculate_sv30(results["predictions"]) # type: ignore
            logger.info(f"检测成功,sewage_percent:{sv30},sewage_confidence:0.9,sPicFileName:{image_url}")
            return {"detail":RET.OK,"sewage_percent":sv30,"sewage_confidence":0.9,"sPicFileName":image_url}

        else:
            logger.error("视频截图接口程序报错")
            return {"detail": RET.SERVERERR, "message": "视频截图接口程序报错"}

    else:
        logger.error("截图接口通讯失败")
        return {"detail": RET.SERVERERR, "message": "视频截图接口网络通讯失败"}



# 1.配置 CORSMiddleware
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许访问的源
    allow_credentials=True,  # 支持 cookie
    allow_methods=["*"],  # 允许使用的请求方法
    allow_headers=["*"]  # 允许携带的 Headers
)

# # 2.配置 Swagger UI CDN
# from fastapi.openapi.docs import get_swagger_ui_html
# @app.get("/docs", include_in_schema=False)
# async def custom_swagger_ui_html():
#     return get_swagger_ui_html(
#         openapi_url=app.openapi_url,
#         title=f"{app.title} - Swagger UI",
#         oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
#         swagger_js_url="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js",
#         swagger_css_url="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css",
#     )

