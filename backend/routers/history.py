from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from database import get_db
from models import DownloadHistory, Account, Downloader, FilterRule, beijing_now
from services.scheduler import check_expired_torrents
from services.downloader import get_torrent_info_with_tags, add_torrent, get_tags, create_tags
from config import TORRENT_DIR

router = APIRouter(prefix="/history", tags=["下载历史"])

class HistoryResponse(BaseModel):
    id: int
    account_id: Optional[int]
    torrent_id: str
    torrent_name: str
    torrent_size: float
    rule_id: Optional[int]
    downloader_id: Optional[int]
    status: str
    info_hash: Optional[str]
    discount_type: Optional[str]
    discount_end_time: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class HistoryListResponse(BaseModel):
    total: int
    data: List[HistoryResponse]

class TorrentStatusResponse(BaseModel):
    """种子状态响应"""
    id: int
    torrent_name: str
    status: str
    discount_type: Optional[str]
    discount_end_time: Optional[datetime]
    is_expired: bool
    torrent_info: Optional[dict]  # 下载器中的种子信息
    rule_tags: List[str]
    torrent_tags: List[str]
    should_delete: bool

@router.get("/", response_model=HistoryListResponse)
async def list_history(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取下载历史"""
    query = db.query(DownloadHistory)
    
    if account_id:
        query = query.filter(DownloadHistory.account_id == account_id)
    if status:
        query = query.filter(DownloadHistory.status == status)
    
    total = query.count()
    items = query.order_by(DownloadHistory.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return HistoryListResponse(total=total, data=items)

@router.get("/check-expired")
async def check_expired_status(db: Session = Depends(get_db)):
    """检查所有种子的过期状态（调试用）"""
    now = beijing_now()
    
    # 获取所有有促销信息的记录
    records = db.query(DownloadHistory).filter(
        DownloadHistory.discount_end_time != None,
        DownloadHistory.info_hash != None,
        DownloadHistory.rule_id != None
    ).all()
    
    result = []
    
    for record in records:
        is_expired = record.discount_end_time < now if record.discount_end_time else False
        
        # 获取规则标签
        rule = db.query(FilterRule).filter(FilterRule.id == record.rule_id).first()
        rule_tags = rule.tags if rule and rule.tags else []
        
        # 获取下载器中的种子信息
        torrent_info = None
        torrent_tags = []
        should_delete = False
        
        if record.downloader_id:
            downloader = db.query(Downloader).filter(Downloader.id == record.downloader_id).first()
            if downloader:
                try:
                    torrent_info = await get_torrent_info_with_tags(downloader, record.info_hash)
                    if torrent_info:
                        torrent_tags = torrent_info.get("tags", [])
                        
                        # 判断是否应该删除
                        if (is_expired and 
                            not torrent_info.get("is_completed", False) and
                            record.status not in ["completed", "expired_deleted", "failed"]):
                            
                            # 检查标签匹配
                            rule_tags_set = set(rule_tags)
                            torrent_tags_set = set(torrent_tags)
                            
                            if not rule_tags_set or rule_tags_set.intersection(torrent_tags_set):
                                should_delete = True
                                
                except Exception as e:
                    torrent_info = {"error": str(e)}
        
        result.append(TorrentStatusResponse(
            id=record.id,
            torrent_name=record.torrent_name,
            status=record.status,
            discount_type=record.discount_type,
            discount_end_time=record.discount_end_time,
            is_expired=is_expired,
            torrent_info=torrent_info,
            rule_tags=rule_tags,
            torrent_tags=torrent_tags,
            should_delete=should_delete
        ))
    
    return {
        "total": len(result),
        "current_time": now,
        "torrents": result
    }

@router.post("/upload-torrent")
async def upload_torrent_file(
    file: UploadFile = File(...),
    downloader_id: int = Form(...),
    account_id: Optional[int] = Form(None),
    save_path: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """上传种子文件并添加到下载器"""
    
    # 验证文件类型
    if not file.filename.endswith('.torrent'):
        raise HTTPException(status_code=400, detail="只支持.torrent文件")
    
    # 获取下载器
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 从种子文件中提取种子ID和促销信息
        torrent_id = None
        torrent_internal_name = None
        discount_type = None
        discount_end_time = None
        torrent_size = 0.0
        
        try:
            # 解析种子文件
            import bencodepy
            torrent_data = bencodepy.decode(content)
            
            # M-Team种子的ID在comment字段中
            comment = torrent_data.get(b'comment', b'')
            if isinstance(comment, bytes):
                comment = comment.decode('utf-8')
            
            # comment字段直接就是种子ID（纯数字）
            if comment and comment.isdigit():
                torrent_id = comment
                print(f"[Upload] 从comment字段提取到种子ID: {torrent_id}")
            
            # 获取种子内部名称（下载器使用的名称）
            info = torrent_data.get(b'info', {})
            internal_name = info.get(b'name', b'')
            if isinstance(internal_name, bytes):
                torrent_internal_name = internal_name.decode('utf-8')
                print(f"[Upload] 种子内部名称: {torrent_internal_name}")
            
            # 获取种子大小
            if b'length' in info:
                torrent_size = float(info[b'length'])
            elif b'files' in info:
                # 多文件种子
                torrent_size = sum(f.get(b'length', 0) for f in info[b'files'])
            
            # 如果有关联账号和种子ID，通过API查询促销信息
            if account_id and torrent_id:
                account = db.query(Account).filter(Account.id == account_id).first()
                if account and account.api_key:
                    try:
                        from services.scraper import MTeamAPI
                        api = MTeamAPI(account.api_key)
                        detail_result = await api.get_torrent_detail(torrent_id)
                        
                        if detail_result["success"]:
                            torrent_detail = detail_result["data"]
                            status = torrent_detail.get("status", {})
                            discount_type = status.get("discount", "NORMAL")
                            discount_end_time_raw = status.get("discountEndTime")
                            
                            # 解析促销到期时间
                            if discount_end_time_raw:
                                try:
                                    if isinstance(discount_end_time_raw, (int, float)):
                                        # 时间戳格式（毫秒）
                                        discount_end_time = datetime.fromtimestamp(
                                            discount_end_time_raw / 1000 if discount_end_time_raw > 1e10 else discount_end_time_raw
                                        )
                                    elif isinstance(discount_end_time_raw, str):
                                        # ISO格式字符串
                                        discount_end_time = datetime.fromisoformat(discount_end_time_raw.replace("Z", "+00:00"))
                                except Exception as e:
                                    print(f"[Upload] 解析促销到期时间失败: {e}")
                            
                            print(f"[Upload] 查询到促销信息: {discount_type}, 到期时间: {discount_end_time}")
                        else:
                            print(f"[Upload] 查询种子详情失败: {detail_result.get('error')}")
                    except Exception as e:
                        print(f"[Upload] 查询促销信息失败: {e}")
                        
        except Exception as e:
            print(f"[Upload] 解析种子文件失败: {e}")
        
        # 保存种子文件
        torrent_filename = f"upload_{beijing_now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        torrent_path = TORRENT_DIR / torrent_filename
        
        with open(torrent_path, "wb") as f:
            f.write(content)
        
        # 处理标签
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # 确保标签在下载器中存在
            existing_tags = await get_tags(downloader)
            new_tags = [tag for tag in tag_list if tag not in existing_tags]
            if new_tags:
                await create_tags(downloader, new_tags)
        
        # 添加到下载器
        info_hash = await add_torrent(downloader, str(torrent_path), save_path, tag_list)
        
        if not info_hash:
            raise HTTPException(status_code=500, detail="添加种子到下载器失败")
        
        # 使用种子内部名称（与下载器一致），如果没有则使用文件名
        display_name = torrent_internal_name or file.filename.replace('.torrent', '').replace('[M-TEAM]', '')
        
        # 创建下载历史记录
        history_record = DownloadHistory(
            account_id=account_id,
            torrent_id=torrent_id or f"upload_{info_hash[:8]}",
            torrent_name=display_name,
            torrent_size=torrent_size,
            rule_id=None,
            downloader_id=downloader_id,
            status="downloading",
            info_hash=info_hash if info_hash != "unknown" else None,
            discount_type=discount_type,
            discount_end_time=discount_end_time,
            created_at=beijing_now()
        )
        
        db.add(history_record)
        db.commit()
        
        return {
            "success": True,
            "message": "种子文件上传成功",
            "data": {
                "filename": file.filename,
                "torrent_name": display_name,
                "info_hash": info_hash,
                "downloader": downloader.name,
                "tags": tag_list,
                "history_id": history_record.id,
                "torrent_id": torrent_id,
                "discount_type": discount_type,
                "discount_end_time": discount_end_time.isoformat() if discount_end_time else None
            }
        }
        
    except Exception as e:
        db.rollback()
        # 清理已保存的文件
        if 'torrent_path' in locals() and torrent_path.exists():
            os.remove(torrent_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"上传失败: {str(e)}"
        )


@router.get("/downloader-tags/{downloader_id}")
async def get_downloader_tags(downloader_id: int, db: Session = Depends(get_db)):
    """获取下载器的所有标签"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    try:
        tags = await get_tags(downloader)
        return {
            "success": True,
            "tags": tags
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取标签失败: {str(e)}"
        )


@router.post("/sync-status")
async def sync_download_status(
    import_first: bool = Query(False, description="是否先从下载器导入新种子"),
    db: Session = Depends(get_db)
):
    """同步所有下载历史的状态
    
    Args:
        import_first: 如果为 True，先从下载器导入新种子再同步状态
    """
    from services.downloader import get_all_torrents_with_details
    
    imported_count = 0
    
    # 如果需要先导入种子
    if import_first:
        downloaders = db.query(Downloader).filter(Downloader.is_active == True).all()
        
        # 获取数据库中已有的 info_hash
        existing_hashes = set(
            h[0].lower() for h in db.query(DownloadHistory.info_hash).filter(
                DownloadHistory.info_hash != None
            ).all()
        )
        
        for downloader in downloaders:
            try:
                torrents = await get_all_torrents_with_details(downloader)
                print(f"[Import] 下载器 {downloader.name} 中有 {len(torrents)} 个种子")
                
                for torrent in torrents:
                    info_hash = torrent.get("hash", "").lower()
                    
                    if info_hash in existing_hashes:
                        continue
                    
                    # 根据种子状态确定记录状态
                    progress = torrent.get("progress", 0)
                    state = torrent.get("state", "")
                    
                    if progress >= 100:
                        if state in ["uploading", "stalledUP", "queuedUP", "seeding", "seed_wait"]:
                            status = "seeding"
                        else:
                            status = "completed"
                    elif state in ["pausedDL", "pausedUP"]:
                        status = "paused"
                    elif state in ["queuedDL", "allocating"]:
                        status = "queued"
                    else:
                        status = "downloading"
                    
                    history_record = DownloadHistory(
                        account_id=None,
                        torrent_id=f"import_{info_hash[:8]}",
                        torrent_name=torrent.get("name", "未知"),
                        torrent_size=float(torrent.get("size", 0)),
                        rule_id=None,
                        downloader_id=downloader.id,
                        status=status,
                        info_hash=info_hash,
                        discount_type=None,
                        discount_end_time=None,
                        created_at=beijing_now()
                    )
                    
                    db.add(history_record)
                    existing_hashes.add(info_hash)
                    imported_count += 1
                    
            except Exception as e:
                print(f"[Import] 从下载器 {downloader.name} 导入失败: {e}")
                continue
        
        if imported_count > 0:
            db.commit()
            print(f"[Import] 导入完成，新增 {imported_count} 条记录")
    
    # 同步状态
    records = db.query(DownloadHistory).filter(
        DownloadHistory.info_hash != None,
        DownloadHistory.downloader_id != None,
        DownloadHistory.status.notin_(["failed", "expired_deleted"])
    ).all()
    
    updated_count = 0
    
    for record in records:
        downloader = db.query(Downloader).filter(Downloader.id == record.downloader_id).first()
        if not downloader:
            continue
            
        try:
            torrent_info = await get_torrent_info_with_tags(downloader, record.info_hash)
            
            if torrent_info is None:
                if record.status != "deleted":
                    record.status = "deleted"
                    updated_count += 1
            else:
                progress = torrent_info.get("progress", 0)
                qb_state = torrent_info.get("state", "")
                
                new_status = None
                
                if progress >= 100 or torrent_info.get("is_completed", False):
                    if qb_state in ["uploading", "stalledUP", "queuedUP"]:
                        new_status = "seeding"
                    else:
                        new_status = "completed"
                elif progress > 0:
                    if qb_state in ["downloading", "stalledDL", "queuedDL", "metaDL"]:
                        new_status = "downloading"
                    elif qb_state == "pausedDL":
                        new_status = "paused"
                    else:
                        new_status = "downloading"
                else:
                    if qb_state == "pausedDL":
                        new_status = "paused"
                    elif qb_state in ["queuedDL", "allocating"]:
                        new_status = "queued"
                    else:
                        new_status = "downloading"
                
                if new_status and record.status != new_status:
                    record.status = new_status
                    updated_count += 1
                    
        except Exception as e:
            print(f"[History] 同步种子状态失败 {record.torrent_name}: {e}")
            continue
    
    db.commit()
    
    message = f"状态同步完成，更新了 {updated_count} 条记录"
    if import_first and imported_count > 0:
        message = f"导入 {imported_count} 条新记录，更新了 {updated_count} 条状态"
    
    return {
        "success": True,
        "message": message,
        "imported_count": imported_count,
        "updated_count": updated_count,
        "total_checked": len(records)
    }


@router.post("/import-from-downloader")
async def import_from_downloader(
    downloader_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """从下载器导入种子到下载历史
    
    如果指定 downloader_id，只导入该下载器的种子；否则导入所有下载器的种子。
    只导入数据库中不存在的种子（根据 info_hash 判断）。
    """
    from services.downloader import get_all_torrents_with_details
    
    # 获取要导入的下载器列表
    if downloader_id:
        downloaders = db.query(Downloader).filter(
            Downloader.id == downloader_id,
            Downloader.is_active == True
        ).all()
    else:
        downloaders = db.query(Downloader).filter(Downloader.is_active == True).all()
    
    if not downloaders:
        return {
            "success": False,
            "message": "没有找到可用的下载器",
            "imported_count": 0
        }
    
    # 获取数据库中已有的 info_hash
    existing_hashes = set(
        h[0].lower() for h in db.query(DownloadHistory.info_hash).filter(
            DownloadHistory.info_hash != None
        ).all()
    )
    
    imported_count = 0
    error_count = 0
    
    for downloader in downloaders:
        try:
            # 获取下载器中的所有种子
            torrents = await get_all_torrents_with_details(downloader)
            print(f"[Import] 下载器 {downloader.name} 中有 {len(torrents)} 个种子")
            
            for torrent in torrents:
                info_hash = torrent.get("hash", "").lower()
                
                # 跳过已存在的种子
                if info_hash in existing_hashes:
                    continue
                
                # 根据种子状态确定记录状态
                progress = torrent.get("progress", 0)
                state = torrent.get("state", "")
                
                if progress >= 100:
                    if state in ["uploading", "stalledUP", "queuedUP", "seeding", "seed_wait"]:
                        status = "seeding"
                    else:
                        status = "completed"
                elif state in ["pausedDL", "pausedUP"]:
                    status = "paused"
                elif state in ["queuedDL", "allocating"]:
                    status = "queued"
                else:
                    status = "downloading"
                
                # 创建下载历史记录
                history_record = DownloadHistory(
                    account_id=None,  # 导入的种子没有关联账号
                    torrent_id=f"import_{info_hash[:8]}",
                    torrent_name=torrent.get("name", "未知"),
                    torrent_size=float(torrent.get("size", 0)),
                    rule_id=None,
                    downloader_id=downloader.id,
                    status=status,
                    info_hash=info_hash,
                    discount_type=None,
                    discount_end_time=None,
                    created_at=beijing_now()
                )
                
                db.add(history_record)
                existing_hashes.add(info_hash)  # 防止重复导入
                imported_count += 1
                
        except Exception as e:
            print(f"[Import] 从下载器 {downloader.name} 导入失败: {e}")
            error_count += 1
            continue
    
    db.commit()
    
    return {
        "success": True,
        "message": f"导入完成，新增 {imported_count} 条记录" + (f"，{error_count} 个下载器导入失败" if error_count > 0 else ""),
        "imported_count": imported_count,
        "error_count": error_count
    }


@router.get("/status-mapping")
async def get_status_mapping():
    """获取状态映射说明"""
    return {
        "status_mapping": {
            "pending": "等待中",
            "downloading": "下载中", 
            "paused": "已暂停",
            "queued": "队列中",
            "completed": "已完成",
            "seeding": "做种中",
            "deleted": "已删除",
            "failed": "失败",
            "expired_deleted": "过期已删"
        },
        "qbittorrent_states": {
            "downloading": "下载中",
            "stalledDL": "下载停滞",
            "queuedDL": "下载队列",
            "pausedDL": "下载暂停",
            "uploading": "上传中",
            "stalledUP": "上传停滞", 
            "queuedUP": "上传队列",
            "pausedUP": "上传暂停",
            "metaDL": "获取元数据",
            "allocating": "分配空间",
            "error": "错误",
            "missingFiles": "文件丢失",
            "unknown": "未知状态"
        }
    }

@router.delete("/deleted")
async def clear_deleted_history(db: Session = Depends(get_db)):
    """清空已删除状态的历史记录（下载器中已不存在的种子）"""
    # 查询所有已删除状态的记录
    records = db.query(DownloadHistory).filter(
        DownloadHistory.status == "deleted"
    ).all()
    
    count = len(records)
    for record in records:
        db.delete(record)
    db.commit()
    
    return {
        "success": True,
        "message": f"已清空 {count} 条已删除记录",
        "deleted_count": count
    }


@router.delete("/{history_id}")
async def delete_history(history_id: int, db: Session = Depends(get_db)):
    """删除下载历史记录，同时删除下载器中的种子"""
    from services.downloader import delete_torrent
    
    history = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    print(f"[History] 删除记录: id={history_id}, status={history.status}, info_hash={history.info_hash}, downloader_id={history.downloader_id}")
    
    # 如果有关联的下载器和 info_hash，尝试删除下载器中的种子
    torrent_deleted = False
    if history.info_hash and history.downloader_id:
        downloader = db.query(Downloader).filter(Downloader.id == history.downloader_id).first()
        if downloader:
            try:
                torrent_deleted = await delete_torrent(downloader, history.info_hash, delete_files=True)
                if torrent_deleted:
                    print(f"[History] 已从下载器删除种子: {history.torrent_name}")
            except Exception as e:
                # 下载器中种子可能已被删除，忽略错误
                print(f"[History] 删除下载器种子时出错（可能已不存在）: {e}")
    
    # 无论下载器删除是否成功，都删除数据库记录
    try:
        db.delete(history)
        db.commit()
        print(f"[History] 数据库记录删除成功: {history.torrent_name}")
    except Exception as e:
        db.rollback()
        print(f"[History] 数据库记录删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除数据库记录失败: {str(e)}")
    
    message = "删除成功"
    if history.info_hash and history.downloader_id:
        message = "删除成功，种子已从下载器移除" if torrent_deleted else "删除成功，种子在下载器中不存在"
    
    return {"success": True, "message": message, "torrent_deleted": torrent_deleted}

@router.delete("/")
async def clear_history(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """清空下载历史，同时删除下载器中的种子"""
    from services.downloader import delete_torrent
    
    query = db.query(DownloadHistory)
    if account_id:
        query = query.filter(DownloadHistory.account_id == account_id)
    
    # 获取所有要删除的记录
    records = query.all()
    
    # 先尝试删除下载器中的种子
    torrent_deleted_count = 0
    for record in records:
        if record.info_hash and record.downloader_id:
            downloader = db.query(Downloader).filter(Downloader.id == record.downloader_id).first()
            if downloader:
                try:
                    deleted = await delete_torrent(downloader, record.info_hash, delete_files=True)
                    if deleted:
                        torrent_deleted_count += 1
                        print(f"[History] 已从下载器删除种子: {record.torrent_name}")
                except Exception as e:
                    # 下载器中种子可能已被删除，忽略错误
                    print(f"[History] 删除下载器种子时出错（可能已不存在）: {e}")
    
    # 删除数据库记录
    count = len(records)
    for record in records:
        db.delete(record)
    db.commit()
    
    return {
        "success": True, 
        "message": f"已删除 {count} 条记录，{torrent_deleted_count} 个种子已从下载器移除",
        "deleted_count": count,
        "torrent_deleted_count": torrent_deleted_count
    }
