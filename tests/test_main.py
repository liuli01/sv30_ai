"""测试 SV30 AI 服务"""

from unittest.mock import ANY, patch

import pytest
import requests
from httpx import AsyncClient, ASGITransport

from main import app, call_workflow, _fetch_image_url

# ── call_workflow ────────────────────────────────────


def sample_response() -> dict:
    return {"node_outputs": {"3": {"computed_values": [0.6543]}}, "max_conf": 0.9214}


@patch("main.requests.post")
def test_call_workflow_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = sample_response()

    value, max_conf = call_workflow("http://example.com/img.jpg")

    assert value == 0.6543
    assert max_conf == 0.9214
    mock_post.assert_called_once_with(
        "http://127.0.0.1:8005/v1/workflow/execute",
        json={
            "workflow": "sv30",
            "image_url": "http://example.com/img.jpg",
            "server_url": "http://127.0.0.1:9924",
        },
        timeout=30,
    )


@patch("main.requests.post")
def test_call_workflow_rounds_to_4_decimals(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "node_outputs": {"3": {"computed_values": [0.123456]}},
        "max_conf": 0.987654,
    }

    value, max_conf = call_workflow("x.jpg")
    assert value == 0.1235
    assert max_conf == 0.9877


@patch("main.requests.post")
def test_call_workflow_network_error(mock_post):
    mock_post.side_effect = requests.RequestException("连接超时")

    with pytest.raises(RuntimeError, match="workflow 通讯失败"):
        call_workflow("x.jpg")


@patch("main.requests.post")
def test_call_workflow_non_200(mock_post):
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Error"

    with pytest.raises(RuntimeError, match="workflow 返回 500"):
        call_workflow("x.jpg")


@patch("main.requests.post")
def test_call_workflow_invalid_json(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = ValueError("bad json")

    with pytest.raises(RuntimeError, match="响应格式错误"):
        call_workflow("x.jpg")


@patch("main.requests.post")
def test_call_workflow_missing_fields(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"node_outputs": {}}

    with pytest.raises(RuntimeError, match="缺少字段"):
        call_workflow("x.jpg")


@patch("main.requests.post")
def test_call_workflow_non_numeric(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "node_outputs": {"3": {"computed_values": ["abc"]}},
        "max_conf": 0.9,
    }

    with pytest.raises(RuntimeError, match="值格式异常"):
        call_workflow("x.jpg")


# ── FastAPI endpoints ────────────────────────────────


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"service": "sv30_ai"}


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── 业务端点 ─────────────────────────────────────────


def mock_camera_snapshot(mock_get, state="success"):
    """辅助：mock 摄像头截图接口返回"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "state": state,
        "url": "/snapshots/img001.jpg",
    }


@patch("main.call_workflow", return_value=(0.35, 0.92))
@patch("main.requests.get")
@pytest.mark.asyncio
async def test_detection_water(mock_get, _mock_cw):
    mock_camera_snapshot(mock_get)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    resp = await client.post("/v1/object-detection/yolov5s/water")
    assert resp.status_code == 200
    body = resp.json()
    assert body["detail"] == "0"
    assert body["water_percent"] == 0.65  # 1 - 0.35
    assert body["water_confidence"] == 0.92
    assert "sPicFileName" in body


@patch("main.call_workflow", return_value=(0.35, 0.92))
@patch("main.requests.get")
@pytest.mark.asyncio
async def test_detection_sewage(mock_get, _mock_cw):
    mock_camera_snapshot(mock_get)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    resp = await client.post("/v1/object-detection/yolov5s/sewage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["detail"] == "0"
    assert body["sewage_percent"] == 0.35
    assert body["sewage_confidence"] == 0.92
    assert "sPicFileName" in body


@patch("main.requests.get")
@pytest.mark.asyncio
async def test_detection_camera_snapshot_fails(mock_get):
    mock_get.return_value.status_code = 500
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    resp = await client.post("/v1/object-detection/yolov5s/water")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "500"
    assert "message" in body

