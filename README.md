# 学生请假记录管理系统

基于 Gradio + SQLite 的轻量级学生请假记录工具，适合班主任日常管理。

## 功能特点

- **快速登记** - 收到家长通知后快速录入请假信息
- **当前请假** - 一目了然看到今天谁在请假
- **记录查询** - 按学生、月份筛选历史记录
- **统计分析** - 请假类型分布、学生频次排名、月度趋势
- **数据导出** - 导出 CSV 方便上报

## 安装运行

```bash
cd leave_tracker
pip install -r requirements.txt
python app.py
```

运行后浏览器自动打开，默认地址 http://localhost:7860

## 数据存储

所有数据存储在 `leave_records.db`（SQLite 文件）中，删除该文件会清空所有记录。

## 配置班级

编辑 `app.py`，修改 `CLASS_NAME` 变量即可：

```python
CLASS_NAME = "初三(1)班"  # 改成你的班级
```
