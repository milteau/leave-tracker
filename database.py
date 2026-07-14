"""SQLite 数据库操作封装"""
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "leave_records.db"


def get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            reason TEXT,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            days INTEGER NOT NULL,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_record(
    student_name: str,
    leave_type: str,
    reason: str,
    start_date: date,
    end_date: date,
    source: str
) -> int:
    """新增请假记录"""
    conn = get_conn()
    cursor = conn.cursor()
    # 计算天数
    days = (end_date - start_date).days + 1
    cursor.execute("""
        INSERT INTO leave_records (student_name, leave_type, reason, start_date, end_date, days, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_name, leave_type, reason, start_date, end_date, days, source))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_all_records() -> list:
    """获取所有记录"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leave_records ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_records_by_student(student_name: str) -> list:
    """按学生姓名筛选"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM leave_records WHERE student_name LIKE ? ORDER BY created_at DESC",
        (f"%{student_name}%",)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_records_by_month(year: int, month: int) -> list:
    """按年月筛选"""
    conn = get_conn()
    cursor = conn.cursor()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    cursor.execute(
        "SELECT * FROM leave_records WHERE start_date >= ? AND start_date < ? ORDER BY start_date DESC",
        (start, end)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_current_leaves() -> list:
    """获取当前正在请假的学生（今日在假）"""
    conn = get_conn()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT * FROM leave_records
        WHERE start_date <= ? AND end_date >= ?
        ORDER BY end_date ASC
    """, (today, today))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_record(record_id: int) -> bool:
    """删除记录"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leave_records WHERE id = ?", (record_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_students() -> list:
    """获取所有学生名单（去重）"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT student_name FROM leave_records ORDER BY student_name")
    rows = cursor.fetchall()
    conn.close()
    return [row["student_name"] for row in rows]


def get_stats_by_type(year: Optional[int] = None, month: Optional[int] = None) -> dict:
    """按请假类型统计"""
    conn = get_conn()
    cursor = conn.cursor()
    if year and month:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        cursor.execute("""
            SELECT leave_type, COUNT(*) as count, SUM(days) as total_days
            FROM leave_records
            WHERE start_date >= ? AND start_date < ?
            GROUP BY leave_type
        """, (start, end))
    else:
        cursor.execute("""
            SELECT leave_type, COUNT(*) as count, SUM(days) as total_days
            FROM leave_records
            GROUP BY leave_type
        """)
    rows = cursor.fetchall()
    conn.close()
    return {row["leave_type"]: {"count": row["count"], "days": row["total_days"]} for row in rows}


def get_stats_by_student(year: Optional[int] = None, month: Optional[int] = None) -> dict:
    """按学生统计请假次数"""
    conn = get_conn()
    cursor = conn.cursor()
    if year and month:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        cursor.execute("""
            SELECT student_name, COUNT(*) as count, SUM(days) as total_days
            FROM leave_records
            WHERE start_date >= ? AND start_date < ?
            GROUP BY student_name
            ORDER BY count DESC
        """, (start, end))
    else:
        cursor.execute("""
            SELECT student_name, COUNT(*) as count, SUM(days) as total_days
            FROM leave_records
            GROUP BY student_name
            ORDER BY count DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return {row["student_name"]: {"count": row["count"], "days": row["total_days"]} for row in rows}


def get_monthly_stats(year: int) -> dict:
    """按月统计请假情况"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%m', start_date) as month,
               COUNT(*) as count,
               SUM(days) as total_days
        FROM leave_records
        WHERE strftime('%Y', start_date) = ?
        GROUP BY month
        ORDER BY month
    """, (str(year),))
    rows = cursor.fetchall()
    conn.close()
    return {row["month"]: {"count": row["count"], "days": row["total_days"]} for row in rows}


def get_total_stats(year: Optional[int] = None, month: Optional[int] = None) -> dict:
    """获取总体统计"""
    conn = get_conn()
    cursor = conn.cursor()
    if year and month:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(days) as total_days
            FROM leave_records
            WHERE start_date >= ? AND start_date < ?
        """, (start, end))
    else:
        cursor.execute("SELECT COUNT(*) as count, SUM(days) as total_days FROM leave_records")
    row = cursor.fetchone()
    conn.close()
    return {"count": row["count"] or 0, "days": row["total_days"] or 0}


# 初始化数据库
init_db()
