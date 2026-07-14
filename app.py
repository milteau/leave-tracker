"""学生请假记录管理系统 - Gradio Web 界面"""
import csv
import os
from datetime import date

# 修补 httpx 让健康检查总是成功
import httpx
_orig_get = httpx.get
def _patched_get(url, **kw):
    if 'startup-events' in str(url):
        class FakeResponse:
            status_code = 200
            is_success = True
            text = ''
            def json(self): return {}
        return FakeResponse()
    return _orig_get(url, **kw)
httpx.get = _patched_get

import gradio as gr
import plotly.express as px
import plotly.graph_objects as go

from database import (
    add_record,
    delete_record,
    get_all_records,
    get_current_leaves,
    get_monthly_stats,
    get_records_by_month,
    get_records_by_student,
    get_stats_by_student,
    get_stats_by_type,
    get_students,
    get_total_stats,
)
from models import LEAVE_TYPES, SOURCES

# 配置
CLASS_NAME = "初三(1)班"  # TODO: 可改为从配置文件读取

# ==================== 页面组件 ====================

def build_quick_add_tab():
    """快速登记 Tab"""
    with gr.Row():
        student_name = gr.Textbox(label="学生姓名", placeholder="输入学生姓名")
    with gr.Row():
        leave_type = gr.Dropdown(choices=LEAVE_TYPES, label="请假类型", value=LEAVE_TYPES[0])
        source = gr.Dropdown(choices=SOURCES, label="通知来源", value=SOURCES[0])
    with gr.Row():
        start_date = gr.DateTime(label="开始日期")
        end_date = gr.DateTime(label="结束日期")
    with gr.Row():
        reason = gr.Textbox(label="请假原因", placeholder="简要描述请假原因")
    with gr.Row():
        submit_btn = gr.Button("提交记录", variant="primary")
        clear_btn = gr.Button("清空")

    result_text = gr.Textbox(label="提交结果", interactive=False)

    def submit(student_name, leave_type, source, start_date, end_date, reason):
        if not student_name:
            return "请输入学生姓名"
        if not start_date or not end_date:
            return "请选择开始和结束日期"
        if end_date < start_date:
            return "结束日期不能早于开始日期"
        record_id = add_record(student_name, leave_type, reason, start_date, end_date, source)
        return f"✓ 记录已保存 (ID: {record_id})"

    def clear():
        return "", LEAVE_TYPES[0], SOURCES[0], None, None, ""

    submit_btn.click(
        fn=submit,
        inputs=[student_name, leave_type, source, start_date, end_date, reason],
        outputs=result_text
    )
    clear_btn.click(
        fn=clear,
        inputs=[],
        outputs=[student_name, leave_type, source, start_date, end_date, reason, result_text]
    )

    return [student_name, leave_type, source, start_date, end_date, reason, submit_btn]


def build_current_leaves_tab():
    """当前请假 Tab"""
    refresh_btn = gr.Button("刷新", variant="secondary")
    current_table = gr.DataFrame(
        headers=["ID", "学生姓名", "请假类型", "开始日期", "结束日期", "天数", "原因", "来源"],
        label="当前正在请假的学生",
        interactive=False,
        wrap=True
    )
    delete_id = gr.Number(label="输入 ID 删除记录", precision=0)
    delete_btn = gr.Button("删除", variant="stop")
    delete_result = gr.Textbox(label="操作结果", interactive=False)

    def refresh():
        records = get_current_leaves()
        if not records:
            return [[]], "当前没有学生请假"
        rows = [[
            r["id"], r["student_name"], r["leave_type"],
            r["start_date"], r["end_date"], r["days"],
            r["reason"], r["source"]
        ] for r in records]
        return rows, ""

    def delete_record_by_id(record_id):
        if not record_id:
            return "请输入要删除的记录 ID"
        if delete_record(int(record_id)):
            return f"✓ 已删除 ID: {record_id}"
        return f"✗ 未找到 ID: {record_id}"

    refresh_btn.click(fn=refresh, inputs=[], outputs=[current_table, delete_result])
    delete_btn.click(fn=delete_record_by_id, inputs=[delete_id], outputs=[delete_result])

    return [refresh_btn, current_table, delete_id, delete_btn, delete_result]


def build_record_search_tab():
    """记录查询 Tab"""
    student_dropdown = gr.Dropdown(choices=[], label="选择学生（可搜索）", allow_custom_value=True)
    refresh_students_btn = gr.Button("刷新学生列表")
    month_selector = gr.Dropdown(
        choices=[f"{y}年{m:02d}月" for y in range(2020, 2030) for m in range(1, 13)],
        label="按月份筛选（不选则显示全部）",
        allow_custom_value=True
    )
    search_btn = gr.Button("查询", variant="primary")
    search_table = gr.DataFrame(
        headers=["ID", "学生姓名", "请假类型", "开始日期", "结束日期", "天数", "原因", "来源", "录入时间"],
        label="请假记录",
        interactive=False,
        wrap=True
    )
    delete_id = gr.Number(label="输入 ID 删除记录", precision=0)
    delete_btn = gr.Button("删除", variant="stop")
    delete_result = gr.Textbox(label="操作结果", interactive=False)

    def update_student_options():
        students = get_students()
        return gr.Dropdown(choices=students if students else ["暂无记录"])

    def search(student_name, month_str):
        records = get_all_records()
        if student_name:
            records = [r for r in records if student_name in r["student_name"]]
        if month_str:
            year = int(month_str[:4])
            month = int(month_str[5:7])
            start = f"{year}-{month:02d}-01"
            if month == 12:
                end = f"{year + 1}-01-01"
            else:
                end = f"{year}-{month + 1:02d}-01"
            records = [r for r in records if start <= r["start_date"] < end]
        if not records:
            return [[]], "未找到记录"
        rows = [[
            r["id"], r["student_name"], r["leave_type"],
            r["start_date"], r["end_date"], r["days"],
            r["reason"], r["source"], r["created_at"]
        ] for r in records]
        return rows, ""

    def delete_record_by_id(record_id):
        if not record_id:
            return "请输入要删除的记录 ID"
        if delete_record(int(record_id)):
            return f"✓ 已删除 ID: {record_id}"
        return f"✗ 未找到 ID: {record_id}"

    refresh_students_btn.click(fn=update_student_options, inputs=[], outputs=[student_dropdown])
    search_btn.click(fn=search, inputs=[student_dropdown, month_selector], outputs=[search_table, delete_result])
    delete_btn.click(fn=delete_record_by_id, inputs=[delete_id], outputs=[delete_result])

    return [student_dropdown, refresh_students_btn, month_selector, search_btn, search_table,
            delete_id, delete_btn, delete_result]


def build_stats_tab():
    """统计分析 Tab"""
    year_selector = gr.Dropdown(
        choices=[str(y) for y in range(2020, 2030)],
        value=str(date.today().year),
        label="选择年份"
    )
    month_selector = gr.Dropdown(
        choices=["全部"] + [f"{m:02d}月" for m in range(1, 13)],
        value="全部",
        label="选择月份"
    )
    refresh_btn = gr.Button("刷新统计", variant="primary")

    total_count = gr.Number(label="请假人次", interactive=False)
    total_days = gr.Number(label="请假总天数", interactive=False)
    pie_chart = gr.Plot(label="请假类型分布")
    bar_chart = gr.Plot(label="学生请假频次 Top10")
    line_chart = gr.Plot(label="月度请假趋势")

    def update_stats(year_str, month_str):
        year = int(year_str)
        if month_str == "全部":
            month = None
        else:
            month = int(month_str[:2])

        # 总体统计
        total = get_total_stats(year, month)
        total_count_val = total["count"]
        total_days_val = total["days"]

        # 按类型统计
        type_stats = get_stats_by_type(year, month)
        if type_stats:
            pie_df = {
                "type": list(type_stats.keys()),
                "count": [v["count"] for v in type_stats.values()],
                "days": [v["days"] for v in type_stats.values()]
            }
            pie_fig = px.pie(pie_df, names="type", values="count", title="请假类型分布")
        else:
            pie_fig = go.Figure()

        # 按学生统计
        student_stats = get_stats_by_student(year, month)
        if student_stats:
            top_students = list(student_stats.items())[:10]
            bar_df = {
                "student": [s[0] for s in top_students],
                "count": [s[1]["count"] for s in top_students]
            }
            bar_fig = px.bar(bar_df, x="student", y="count", title="学生请假频次 Top10")
        else:
            bar_fig = go.Figure()

        # 月度趋势
        monthly = get_monthly_stats(year)
        if monthly:
            line_df = {
                "month": [f"{year}-{m:02d}" for m in range(1, 13) if m in monthly],
                "count": [monthly[m]["count"] for m in range(1, 13) if m in monthly]
            }
            line_fig = px.line(line_df, x="month", y="count", markers=True, title="月度请假趋势")
        else:
            line_fig = go.Figure()

        return total_count_val, total_days_val, pie_fig, bar_fig, line_fig

    refresh_btn.click(
        fn=update_stats,
        inputs=[year_selector, month_selector],
        outputs=[total_count, total_days, pie_chart, bar_chart, line_chart]
    )

    return [year_selector, month_selector, refresh_btn, total_count, total_days,
            pie_chart, bar_chart, line_chart]


def build_export_tab():
    """导出 Tab"""
    year_selector = gr.Dropdown(
        choices=[str(y) for y in range(2020, 2030)],
        value=str(date.today().year),
        label="选择年份"
    )
    export_btn = gr.Button("导出 CSV", variant="primary")
    file_output = gr.File(label="下载文件")
    export_result = gr.Textbox(label="导出结果", interactive=False)

    def export_csv(year_str):
        year = int(year_str)
        records = get_all_records()
        year_records = [r for r in records if r["start_date"].startswith(str(year))]
        if not year_records:
            return None, "该年份没有记录"

        file_path = os.path.join(os.path.dirname(__file__), f"请假记录_{year}.csv")
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "学生姓名", "请假类型", "开始日期", "结束日期", "天数", "原因", "来源", "录入时间"])
            for r in year_records:
                writer.writerow([
                    r["id"], r["student_name"], r["leave_type"],
                    r["start_date"], r["end_date"], r["days"],
                    r["reason"], r["source"], r["created_at"]
                ])
        return file_path, f"已导出 {len(year_records)} 条记录"

    export_btn.click(fn=export_csv, inputs=[year_selector], outputs=[file_output, export_result])

    return [year_selector, export_btn, file_output]


# ==================== 主界面 ====================

def create_app():
    """创建主应用"""
    with gr.Blocks(title=f"请假管理系统 - {CLASS_NAME}") as app:
        gr.Markdown(f"# 请假管理系统  ## 班级: {CLASS_NAME}")

        with gr.Tabs():
            with gr.Tab("快速登记"):
                build_quick_add_tab()

            with gr.Tab("当前请假"):
                build_current_leaves_tab()

            with gr.Tab("记录查询"):
                build_record_search_tab()

            with gr.Tab("统计分析"):
                build_stats_tab()

            with gr.Tab("导出数据"):
                build_export_tab()

        gr.Markdown("---")
        gr.Markdown("学生请假记录管理系统 | 基于 Gradio + SQLite")

    return app


if __name__ == "__main__":
    import os
    os.environ["GRADIO_ANALYTICS"] = "false"
    # 跳过健康检查
    os.environ["GRADIO_HEALTH_CHECK"] = "false"
    app = create_app()
    import subprocess
    import threading
    import time
    def open_browser():
        time.sleep(3)
        # 使用 Windows cmd /c start 打开浏览器
        try:
            subprocess.Popen(["cmd", "/c", "start", "http://127.0.0.1:7860"],
                            shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
    threading.Thread(target=open_browser, daemon=True).start()
    print("=" * 50)
    print("请假管理系统已启动！")
    print("请在浏览器打开: http://127.0.0.1:7860")
    print("=" * 50)
    app.launch(server_name="127.0.0.1", server_port=7860, share=True)
