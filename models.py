"""数据模型定义"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

LEAVE_TYPES = ["事假", "病假", "公假"]
SOURCES = ["微信", "短信", "书面", "电话", "其他"]


@dataclass
class LeaveRecord:
    """请假记录模型"""
    student_name: str
    leave_type: str
    reason: str
    start_date: date
    end_date: date
    source: str
    days: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.days is None:
            self.days = (self.end_date - self.start_date).days + 1

    def to_dict(self):
        return {
            "id": self.id,
            "student_name": self.student_name,
            "leave_type": self.leave_type,
            "reason": self.reason,
            "start_date": self.start_date.isoformat() if isinstance(self.start_date, date) else self.start_date,
            "end_date": self.end_date.isoformat() if isinstance(self.end_date, date) else self.end_date,
            "days": self.days,
            "source": self.source,
            "created_at": self.created_at
        }
