from typing import Optional, List, Dict, Any
import qbittorrentapi
from transmission_rpc import Client as TransmissionClient


def _get_qb_client(downloader):
    """获取 qBittorrent 客户端"""
    protocol = "https" if getattr(downloader, 'use_ssl', False) else "http"
    host = f"{protocol}://{downloader.host}"
    
    client = qbittorrentapi.Client(
        host=host,
        port=downloader.port,
        username=downloader.username,
        password=downloader.password,
        VERIFY_WEBUI_CERTIFICATE=False
    )
    client.auth_log_in()
    return client


def _get_tr_client(downloader):
    """获取 Transmission 客户端"""
    protocol = "https" if getattr(downloader, 'use_ssl', False) else "http"
    return TransmissionClient(
        host=downloader.host,
        port=downloader.port,
        username=downloader.username,
        password=downloader.password,
        protocol=protocol
    )


async def test_downloader_connection(downloader) -> dict:
    """测试下载器连接"""
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            version = client.app.version
            return {"success": True, "message": f"连接成功，版本: {version}"}
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            session = client.get_session()
            return {"success": True, "message": f"连接成功，版本: {session.version}"}
        
        else:
            return {"success": False, "message": "不支持的下载器类型"}
    
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}

async def add_torrent(downloader, torrent_path: str, save_path: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[str]:
    """添加种子到下载器
    
    Args:
        downloader: 下载器配置对象
        torrent_path: 种子文件路径
        save_path: 保存路径
        tags: 要添加的标签列表
    
    Returns:
        成功返回种子的 info_hash，失败返回 None
    """
    try:
        # 读取种子文件
        with open(torrent_path, "rb") as f:
            torrent_content = f.read()
        
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            
            # 如果有标签，先确保标签存在
            if tags:
                existing_tags = set(client.torrents_tags() or [])
                new_tags = [t for t in tags if t not in existing_tags]
                if new_tags:
                    client.torrents_create_tags(tags=new_tags)
                    print(f"[Downloader] 创建新标签: {new_tags}")
            
            kwargs = {"torrent_files": torrent_content}
            if save_path:
                kwargs["save_path"] = save_path
            if tags:
                kwargs["tags"] = ",".join(tags)
            
            # 添加种子
            client.torrents_add(**kwargs)
            
            # 尝试获取刚添加的种子的 hash
            # qBittorrent 添加后需要等待一下才能获取
            import time
            time.sleep(1)
            
            # 从种子文件解析 info_hash
            import hashlib
            try:
                import bencodepy
                torrent_data = bencodepy.decode(torrent_content)
                info = torrent_data[b'info']
                info_hash = hashlib.sha1(bencodepy.encode(info)).hexdigest()
                return info_hash
            except:
                # 如果解析失败，返回 True 表示添加成功但无法获取 hash
                return "unknown"
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            
            import base64
            torrent_b64 = base64.b64encode(torrent_content).decode()
            
            kwargs = {"torrent": torrent_b64}
            if save_path:
                kwargs["download_dir"] = save_path
            # Transmission 不支持标签
            
            result = client.add_torrent(**kwargs)
            return result.hashString if result else None
        
        return None
    
    except Exception as e:
        print(f"[Downloader] 添加种子失败: {e}")
        return None


async def get_torrent_info(downloader, info_hash: str) -> Optional[Dict[str, Any]]:
    """获取种子信息
    
    Args:
        downloader: 下载器配置对象
        info_hash: 种子哈希
    
    Returns:
        种子信息字典，包含 progress（进度 0-100）、state（状态）等
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            torrents = client.torrents_info(torrent_hashes=info_hash)
            
            if torrents:
                t = torrents[0]
                return {
                    "hash": t.hash,
                    "name": t.name,
                    "progress": t.progress * 100,  # 转为百分比
                    "state": t.state,
                    "size": t.size,
                    "downloaded": t.downloaded,
                    "is_completed": t.progress >= 1.0
                }
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            torrents = client.get_torrents(ids=[info_hash])
            
            if torrents:
                t = torrents[0]
                return {
                    "hash": t.hashString,
                    "name": t.name,
                    "progress": t.progress,
                    "state": t.status,
                    "size": t.total_size,
                    "downloaded": t.downloaded_ever,
                    "is_completed": t.progress >= 100
                }
        
        return None
    
    except Exception as e:
        print(f"[Downloader] 获取种子信息失败: {e}")
        return None


async def delete_torrent(downloader, info_hash: str, delete_files: bool = True) -> bool:
    """删除种子
    
    Args:
        downloader: 下载器配置对象
        info_hash: 种子哈希
        delete_files: 是否同时删除文件
    
    Returns:
        是否成功
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            client.torrents_delete(
                torrent_hashes=info_hash,
                delete_files=delete_files
            )
            print(f"[Downloader] 已删除种子: {info_hash}")
            return True
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            client.remove_torrent(
                ids=[info_hash],
                delete_data=delete_files
            )
            print(f"[Downloader] 已删除种子: {info_hash}")
            return True
        
        return False
    
    except Exception as e:
        print(f"[Downloader] 删除种子失败: {e}")
        return False


async def get_incomplete_torrents(downloader) -> List[Dict[str, Any]]:
    """获取所有未完成的种子列表
    
    Returns:
        未完成种子列表
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            # 获取所有下载中的种子
            torrents = client.torrents_info(status_filter="downloading")
            
            return [{
                "hash": t.hash,
                "name": t.name,
                "progress": t.progress * 100,
                "state": t.state,
                "size": t.size
            } for t in torrents]
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            torrents = client.get_torrents()
            
            return [{
                "hash": t.hashString,
                "name": t.name,
                "progress": t.progress,
                "state": t.status,
                "size": t.total_size
            } for t in torrents if t.progress < 100]
        
        return []
    
    except Exception as e:
        print(f"[Downloader] 获取未完成种子列表失败: {e}")
        return []


async def get_tags(downloader) -> List[str]:
    """获取下载器中的所有标签
    
    Returns:
        标签列表
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            tags = client.torrents_tags()
            return list(tags) if tags else []
        
        elif downloader.type == "transmission":
            # Transmission 不支持标签功能
            return []
        
        return []
    
    except Exception as e:
        print(f"[Downloader] 获取标签列表失败: {e}")
        return []


async def create_tags(downloader, tags: List[str]) -> bool:
    """在下载器中创建标签
    
    Args:
        downloader: 下载器配置对象
        tags: 要创建的标签列表
    
    Returns:
        是否成功
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            # 获取现有标签
            existing_tags = set(client.torrents_tags() or [])
            # 创建不存在的标签
            new_tags = [t for t in tags if t not in existing_tags]
            if new_tags:
                client.torrents_create_tags(tags=new_tags)
                print(f"[Downloader] 创建标签: {new_tags}")
            return True
        
        elif downloader.type == "transmission":
            # Transmission 不支持标签功能
            return True
        
        return False
    
    except Exception as e:
        print(f"[Downloader] 创建标签失败: {e}")
        return False


async def get_downloading_count(downloader) -> int:
    """获取正在下载的种子数量
    
    Returns:
        下载中的种子数量
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            # 获取所有下载中的种子（包括暂停的下载任务）
            torrents = client.torrents_info(status_filter="downloading")
            return len(torrents)
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            torrents = client.get_torrents()
            return len([t for t in torrents if t.progress < 100])
        
        return 0
    
    except Exception as e:
        print(f"[Downloader] 获取下载中种子数量失败: {e}")
        return 0


async def get_torrent_info_with_tags(downloader, info_hash: str) -> Optional[Dict[str, Any]]:
    """获取种子信息（包含标签）
    
    Args:
        downloader: 下载器配置对象
        info_hash: 种子哈希
    
    Returns:
        种子信息字典，包含 tags 列表
    """
    try:
        if downloader.type == "qbittorrent":
            client = _get_qb_client(downloader)
            torrents = client.torrents_info(torrent_hashes=info_hash)
            
            if torrents:
                t = torrents[0]
                # 获取标签列表
                tags = t.tags.split(',') if t.tags else []
                tags = [tag.strip() for tag in tags if tag.strip()]
                
                return {
                    "hash": t.hash,
                    "name": t.name,
                    "progress": t.progress * 100,
                    "state": t.state,
                    "size": t.size,
                    "downloaded": t.downloaded,
                    "is_completed": t.progress >= 1.0,
                    "tags": tags
                }
        
        elif downloader.type == "transmission":
            client = _get_tr_client(downloader)
            torrents = client.get_torrents(ids=[info_hash])
            
            if torrents:
                t = torrents[0]
                return {
                    "hash": t.hashString,
                    "name": t.name,
                    "progress": t.progress,
                    "state": t.status,
                    "size": t.total_size,
                    "downloaded": t.downloaded_ever,
                    "is_completed": t.progress >= 100,
                    "tags": []  # Transmission 不支持标签
                }
        
        return None
    
    except Exception as e:
        print(f"[Downloader] 获取种子信息失败: {e}")
        return None
