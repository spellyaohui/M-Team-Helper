import httpx
from typing import Optional, Dict, Any, List
from config import settings

class MTeamAPI:
    """M-Team API 客户端，使用 API Token 认证"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"{settings.MTEAM_BASE_URL}/api"
        self.headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _request(self, endpoint: str, data: dict = None, use_form: bool = False) -> Dict[str, Any]:
        """发送 API 请求
        
        注意：M-Team API 要求用 data 参数传 JSON 字符串，而不是用 json 参数
        """
        import json
        if data is None:
            data = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if use_form:
                headers = {**self.headers, "Content-Type": "application/x-www-form-urlencoded"}
                response = await client.post(
                    f"{self.base_url}/{endpoint}",
                    headers=headers,
                    data=data
                )
            else:
                # M-Team API 要求用 data 传 JSON 字符串
                headers = {**self.headers}
                headers.pop("Content-Type", None)  # 让 httpx 自动处理
                response = await client.post(
                    f"{self.base_url}/{endpoint}",
                    headers=headers,
                    content=json.dumps(data)
                )
            
            result = response.json()
            if result.get("code") == "0":
                return {"success": True, "data": result.get("data")}
            else:
                return {"success": False, "error": result.get("message", "API请求失败")}
    
    async def get_profile(self) -> Dict[str, Any]:
        """获取用户信息"""
        return await self._request("member/profile")
    
    async def search_torrents(
        self,
        page: int = 1,
        page_size: int = 100,
        mode: str = "normal",
        categories: List[str] = None,
        keyword: str = None,
        discount: str = None,  # FREE, PERCENT_50, _2X_FREE, _2X_PERCENT_50, _2X
        sort_field: str = "CREATED_DATE",
        sort_direction: str = "DESC"
    ) -> Dict[str, Any]:
        """搜索种子列表"""
        data = {
            "pageNumber": page,
            "pageSize": page_size,
            "mode": mode,
            "sortField": sort_field,
            "sortDirection": sort_direction
        }
        
        if categories:
            data["categories"] = categories
        
        if keyword:
            data["keyword"] = keyword
        
        if discount:
            data["discount"] = discount
        
        return await self._request("torrent/search", data)
    
    async def get_torrent_detail(self, torrent_id: str) -> Dict[str, Any]:
        """获取种子详情"""
        return await self._request("torrent/detail", {"id": torrent_id}, use_form=True)
    
    async def gen_download_token(self, torrent_id: str) -> Dict[str, Any]:
        """生成种子下载链接"""
        return await self._request("torrent/genDlToken", {"id": torrent_id}, use_form=True)
    
    async def download_torrent(self, torrent_id: str) -> Optional[bytes]:
        """下载种子文件"""
        result = await self.gen_download_token(torrent_id)
        if not result["success"]:
            return None
        
        download_url = result["data"]
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(download_url)
            if response.status_code == 200:
                return response.content
        return None


# 折扣类型映射
DISCOUNT_MAP = {
    "FREE": "免费",
    "PERCENT_50": "50%",
    "_2X_FREE": "2x免费",
    "_2X_PERCENT_50": "2x50%",
    "_2X": "2x上传",
    "NORMAL": "无优惠"
}

def parse_torrent(torrent: dict) -> dict:
    """解析种子数据为统一格式"""
    status = torrent.get("status", {})
    discount = status.get("discount", "NORMAL")
    
    # 解析促销到期时间
    discount_end_time = status.get("discountEndTime")
    
    return {
        "id": torrent.get("id"),
        "name": torrent.get("name"),
        "small_descr": torrent.get("smallDescr"),
        "category": torrent.get("category"),
        "size": int(torrent.get("size", 0)),
        "size_gb": round(int(torrent.get("size", 0)) / (1024**3), 2),
        "seeders": int(status.get("seeders", 0)),
        "leechers": int(status.get("leechers", 0)),
        "completed": int(status.get("timesCompleted", 0)),
        "discount": discount,
        "discount_text": DISCOUNT_MAP.get(discount, discount),
        "discount_end_time": discount_end_time,  # 促销到期时间（ISO格式字符串或时间戳）
        "is_free": discount in ["FREE", "_2X_FREE"],
        "is_2x": discount in ["_2X", "_2X_FREE", "_2X_PERCENT_50"],
        "created_date": torrent.get("createdDate"),
        "imdb": torrent.get("imdb"),
        "imdb_rating": torrent.get("imdbRating"),
        "douban": torrent.get("douban"),
        "douban_rating": torrent.get("doubanRating"),
        "labels": torrent.get("labelsNew", []),
        "images": torrent.get("imageList", [])
    }

def parse_user_profile(data: dict) -> dict:
    """解析用户信息"""
    member_count = data.get("memberCount", {})
    member_status = data.get("memberStatus", {})
    
    return {
        "uid": data.get("id"),
        "username": data.get("username"),
        "email": data.get("email"),
        "uploaded": int(member_count.get("uploaded", 0)),
        "downloaded": int(member_count.get("downloaded", 0)),
        "ratio": float(member_count.get("shareRate", 0)),
        "bonus": float(member_count.get("bonus", 0)),
        "vip": member_status.get("vip", False),
        "last_login": member_status.get("lastLogin"),
        "last_browse": member_status.get("lastBrowse")
    }
