"""
测试 M-Team API - 使用 API Key 获取下载历史
"""
import asyncio
import httpx
import json
import time

API_KEY = "c63500a3-0cea-44bf-8967-95178ece1d35"
BASE_URL = "https://api.m-team.cc"

async def test_query_history():
    # 测试种子 ID 列表
    tids = ["1100805", "1100806", "1100804"]
    timestamp = int(time.time() * 1000)
    
    payload = {
        "tids": tids,
        "_timestamp": timestamp,
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("=== 测试 /api/tracker/queryHistory (API Key) ===\n")
        print(f"请求参数: {json.dumps(payload, indent=2)}")
        
        # 使用 x-api-key 而不是 authorization
        headers = {
            "x-api-key": API_KEY,
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
        }
        
        response = await client.post(
            f"{BASE_URL}/api/tracker/queryHistory",
            headers=headers,
            json=payload
        )
        
        print(f"\n状态码: {response.status_code}")
        data = response.json()
        print(f"响应:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(test_query_history())

if __name__ == "__main__":
    asyncio.run(test_query_history())

if __name__ == "__main__":
    asyncio.run(test_query_history())
