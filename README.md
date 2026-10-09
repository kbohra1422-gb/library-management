# 📚 Library Management System - Native Desktop Application

> **Quality Goal Q10 – Enhanced Quality Documentation & User Guidance**  
> A high-performance, native Desktop GUI Application for library cataloging, real-time metrics tracking, issue/return toggling, and multi-criteria book search built with Python 3, CustomTkinter, and SQLite.

---

## 🌟 Desktop Features

- 🖥️ **Native Desktop Window**: Standalone GUI desktop application window with native title bar, window controls, and theme switching (Dark/Light/System).
- 📊 **Real-Time Dashboard Cards**: Live stats overview for Total Books, Available inventory, Borrowed items, and Category count.
- 📖 **Full CRUD Capabilities**: Add, view, edit, and delete books in real time.
- 🔍 **Search & Multi-Filter**: Search by title, author, or category keywords, plus filter dropdowns for Category and Status.
- 🔄 **One-Click Issue / Return Toggle**: Change book status between `Available` and `Borrowed` directly from the records table.
- ✏️ **Modal Edit Dialog**: Pop-up window for editing book records with validation safety.
- ❓ **Help & User Guide**: Integrated FAQ tab explaining desktop features.

---

## 🚀 Quick Start Guide

### How to Run the Desktop App:

**Option A: Command Line**
```bash
python main.py
```
*(or `python desktop_app.py`)*

**Option B: Double-Click Batch File (Windows)**
Double click [`run_desktop_app.bat`](file:///c:/Users/ADMIN/library_management/run_desktop_app.bat).

---

## 🗄️ Database Schema (`books`)

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique Identifier |
| `title` | `TEXT` | `NOT NULL` | Book Title |
| `author` | `TEXT` | `NOT NULL` | Author Name |
| `category` | `TEXT` | `NOT NULL` | Book Category |
| `status` | `TEXT` | `DEFAULT 'Available'` | Book Status (`Available` / `Borrowed`) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Record Creation Timestamp |

---

## 📁 Desktop Application Structure

```text
library_management/
│
├── main.py                  # Entry point to launch Desktop GUI app
├── desktop_app.py           # CustomTkinter Desktop GUI application logic
├── library.db               # Local SQLite database file
├── run_desktop_app.bat      # Windows batch launcher script
├── requirements.txt         # Dependencies (customtkinter, pillow, flask)
├── README.md                # Project Overview & Architecture Guide
├── USER_MANUAL.md           # Desktop Application User Manual
└── KNOWLEDGE_BASE.md        # Technical Knowledge Base & Specs
```