from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from database import get_db
from models import SystemSettings

router = APIRouter(prefix="/settings", tags=["系统设置"])

class SettingResponse(BaseModel):
    key: str
    value: Any
    description: Optional[str]
    
    class Config:
        from_attributes = True

class AutoDeleteSettings(BaseModel):
    """自动删种设置"""
    enabled: bool = True  # 是否启用自动删种
    delete_scope: str = "all"  # 删种范围：all(全部), normal(仅正常), adult(仅成人)
    check_tags: bool = True  # 是否检查标签匹配

class RefreshIntervalSettings(BaseModel):
    """刷新间隔设置"""
    account_refresh_interval: int = 300  # 账号信息刷新间隔（秒），默认5分钟
    torrent_check_interval: int = 180   # 种子检查间隔（秒），默认3分钟
    expired_check_interval: int = 60    # 过期检查间隔（秒），默认1分钟

class TimeRange(BaseModel):
    """时间段"""
    start: str  # 开始时间，格式 HH:MM
    end: str    # 结束时间，格式 HH:MM

class ScheduleSettings(BaseModel):
    """定时运行设置"""
    enabled: bool = False  # 是否启用定时控制
    time_ranges: list = []  # 时间段列表，每个元素包含 start, end, auto_download, expired_check
    
class UpdateSettingRequest(BaseModel):
    value: Any
    description: Optional[str] = None

@router.get("/auto-delete")
async def get_auto_delete_settings(db: Session = Depends(get_db)):
    """获取自动删种设置"""
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "auto_delete_expired"
    ).first()
    
    if not setting:
        # 返回默认设置
        default_settings = AutoDeleteSettings()
        return {
            "key": "auto_delete_expired",
            "value": default_settings.dict(),
            "description": "自动删除过期促销种子的设置"
        }
    
    try:
        value = json.loads(setting.value)
        return {
            "key": setting.key,
            "value": value,
            "description": setting.description
        }
    except json.JSONDecodeError:
        # 如果解析失败，返回默认设置
        default_settings = AutoDeleteSettings()
        return {
            "key": "auto_delete_expired",
            "value": default_settings.dict(),
            "description": "自动删除过期促销种子的设置"
        }

@router.put("/auto-delete")
async def update_auto_delete_settings(
    settings: AutoDeleteSettings,
    db: Session = Depends(get_db)
):
    """更新自动删种设置"""
    
    # 验证删种范围参数
    if settings.delete_scope not in ["all", "normal", "adult"]:
        raise HTTPException(
            status_code=400, 
            detail="删种范围必须是 'all'(全部)、'normal'(仅正常) 或 'adult'(仅成人) 之一"
        )
    
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "auto_delete_expired"
    ).first()
    
    if setting:
        # 更新现有设置
        setting.value = json.dumps(settings.dict(), ensure_ascii=False)
        setting.description = "自动删除过期促销种子的设置"
    else:
        # 创建新设置
        setting = SystemSettings(
            key="auto_delete_expired",
            value=json.dumps(settings.dict(), ensure_ascii=False),
            description="自动删除过期促销种子的设置"
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    return {
        "success": True,
        "message": "自动删种设置已更新",
        "data": {
            "key": setting.key,
            "value": json.loads(setting.value),
            "description": setting.description
        }
    }

@router.get("/refresh-intervals")
async def get_refresh_intervals(db: Session = Depends(get_db)):
    """获取刷新间隔设置"""
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "refresh_intervals"
    ).first()
    
    if not setting:
        # 返回默认设置
        default_settings = RefreshIntervalSettings()
        return {
            "key": "refresh_intervals",
            "value": default_settings.dict(),
            "description": "系统各项任务的刷新间隔设置"
        }
    
    try:
        value = json.loads(setting.value)
        return {
            "key": setting.key,
            "value": value,
            "description": setting.description
        }
    except json.JSONDecodeError:
        # 如果解析失败，返回默认设置
        default_settings = RefreshIntervalSettings()
        return {
            "key": "refresh_intervals",
            "value": default_settings.dict(),
            "description": "系统各项任务的刷新间隔设置"
        }


@router.put("/refresh-intervals")
async def update_refresh_intervals(
    settings: RefreshIntervalSettings,
    db: Session = Depends(get_db)
):
    """更新刷新间隔设置"""
    
    # 验证间隔参数（最小30秒，最大24小时）
    if not (30 <= settings.account_refresh_interval <= 86400):
        raise HTTPException(
            status_code=400, 
            detail="账号刷新间隔必须在30秒到24小时之间"
        )
    
    if not (30 <= settings.torrent_check_interval <= 86400):
        raise HTTPException(
            status_code=400, 
            detail="种子检查间隔必须在30秒到24小时之间"
        )
    
    if not (30 <= settings.expired_check_interval <= 3600):
        raise HTTPException(
            status_code=400, 
            detail="过期检查间隔必须在30秒到1小时之间"
        )
    
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "refresh_intervals"
    ).first()
    
    if setting:
        # 更新现有设置
        setting.value = json.dumps(settings.dict(), ensure_ascii=False)
        setting.description = "系统各项任务的刷新间隔设置"
    else:
        # 创建新设置
        setting = SystemSettings(
            key="refresh_intervals",
            value=json.dumps(settings.dict(), ensure_ascii=False),
            description="系统各项任务的刷新间隔设置"
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    # 重新启动调度器以应用新的间隔设置
    from services.scheduler import restart_scheduler_with_new_intervals
    try:
        await restart_scheduler_with_new_intervals(settings.dict())
    except Exception as e:
        print(f"[Settings] 重启调度器失败: {e}")
    
    return {
        "success": True,
        "message": "刷新间隔设置已更新，调度器已重启",
        "data": {
            "key": setting.key,
            "value": json.loads(setting.value),
            "description": setting.description
        }
    }


@router.get("/scheduler-status")
async def get_scheduler_status_api():
    """获取调度器状态"""
    from services.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.get("/schedule-control")
async def get_schedule_control(db: Session = Depends(get_db)):
    """获取定时运行控制设置"""
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "schedule_control"
    ).first()
    
    if not setting:
        # 返回默认设置
        default_settings = {
            "enabled": False,
            "time_ranges": []
        }
        return {
            "key": "schedule_control",
            "value": default_settings,
            "description": "定时运行控制设置"
        }
    
    try:
        value = json.loads(setting.value)
        return {
            "key": setting.key,
            "value": value,
            "description": setting.description
        }
    except json.JSONDecodeError:
        default_settings = {
            "enabled": False,
            "time_ranges": []
        }
        return {
            "key": "schedule_control",
            "value": default_settings,
            "description": "定时运行控制设置"
        }


@router.put("/schedule-control")
async def update_schedule_control(
    settings: ScheduleSettings,
    db: Session = Depends(get_db)
):
    """更新定时运行控制设置
    
    time_ranges 格式示例：
    [
        {
            "start": "00:00",
            "end": "08:00",
            "auto_download": false,
            "expired_check": true,
            "account_refresh": true
        },
        {
            "start": "08:00",
            "end": "24:00",
            "auto_download": true,
            "expired_check": true,
            "account_refresh": true
        }
    ]
    """
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "schedule_control"
    ).first()
    
    settings_dict = {
        "enabled": settings.enabled,
        "time_ranges": settings.time_ranges
    }
    
    if setting:
        setting.value = json.dumps(settings_dict, ensure_ascii=False)
        setting.description = "定时运行控制设置"
    else:
        setting = SystemSettings(
            key="schedule_control",
            value=json.dumps(settings_dict, ensure_ascii=False),
            description="定时运行控制设置"
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    return {
        "success": True,
        "message": "定时运行控制设置已更新",
        "data": {
            "key": setting.key,
            "value": json.loads(setting.value),
            "description": setting.description
        }
    }


@router.post("/restart-scheduler")
async def restart_scheduler():
    """重启调度器（应用当前设置）"""
    from services.scheduler import restart_scheduler_with_new_intervals, get_refresh_intervals
    
    try:
        current_intervals = get_refresh_intervals()
        await restart_scheduler_with_new_intervals(current_intervals)
        return {
            "success": True,
            "message": "调度器已重启",
            "intervals": current_intervals
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重启调度器失败: {str(e)}"
        )

@router.get("/")
async def list_all_settings(db: Session = Depends(get_db)):
    """获取所有系统设置"""
    settings = db.query(SystemSettings).all()
    
    result = {}
    for setting in settings:
        try:
            value = json.loads(setting.value)
        except json.JSONDecodeError:
            value = setting.value
        
        result[setting.key] = {
            "value": value,
            "description": setting.description
        }
    
    return result

@router.get("/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    """获取指定设置"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    
    try:
        value = json.loads(setting.value)
    except json.JSONDecodeError:
        value = setting.value
    
    return {
        "key": setting.key,
        "value": value,
        "description": setting.description
    }

@router.put("/{key}")
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    db: Session = Depends(get_db)
):
    """更新指定设置"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    
    # 将值转换为 JSON 字符串
    if isinstance(request.value, (dict, list)):
        value_str = json.dumps(request.value, ensure_ascii=False)
    else:
        value_str = str(request.value)
    
    if setting:
        # 更新现有设置
        setting.value = value_str
        if request.description is not None:
            setting.description = request.description
    else:
        # 创建新设置
        setting = SystemSettings(
            key=key,
            value=value_str,
            description=request.description or f"系统设置: {key}"
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    try:
        parsed_value = json.loads(setting.value)
    except json.JSONDecodeError:
        parsed_value = setting.value
    
    return {
        "success": True,
        "message": f"设置 {key} 已更新",
        "data": {
            "key": setting.key,
            "value": parsed_value,
            "description": setting.description
        }
    }

@router.delete("/{key}")
async def delete_setting(key: str, db: Session = Depends(get_db)):
    """删除指定设置"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    
    db.delete(setting)
    db.commit()
    
    return {"success": True, "message": f"设置 {key} 已删除"}