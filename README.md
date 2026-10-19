# 📚 Library Management System (Web & Native Desktop Edition)

> **Enhanced Quality Documentation & User Guidance**  
> A high-performance, full-featured Library Management System featuring real-time inventory tracking, member directory management, automated due date & fine calculation, Open Library ISBN auto-fetching, Chart.js visual analytics, and printable QR-code receipts.

---

## 🌟 Key Application Features

- 🖥️ **Dual Interface Support**: Native CustomTkinter Desktop GUI (`python main.py`) and Web Application (`python app.py`).
- 👤 **Member & Profile Directory**: Register Students, Faculty, and Staff with full contact records and membership logs.
- 🔄 **Book Issue / Return & Fine Tracker**: Automatic 14-day due date tracking with dynamic late fine calculations (₹5/day).
- 🔍 **ISBN Auto-Fetch via Open Library API**: Enter an ISBN code to automatically retrieve Book Title, Author, Category, and Cover Image URLs.
- 📦 **Multi-Copy Inventory Tracking**: Manage `total_copies` and `available_copies` with stock badges.
- 📊 **Visual Analytics Dashboard**: Interactive Chart.js graphs displaying category distribution, status ratios, and member demographics.
- 📄 **Printable Receipts & QR Code Verification**: Auto-generate printable receipts with QR code authentication for issued books.
- 🌙 **Dark / Light Theme Sync**: Real-time theme switching with LocalStorage state persistence.

---

## 🚀 Quick Start Guide

### Option A: Standalone Desktop Application (Recommended)
```bash
python main.py
```
*(or simply double-click [`run_desktop_app.bat`](file:///c:/Users/ADMIN/library_management/run_desktop_app.bat))*  
Opens LibManager as a standalone, native desktop application window with Edge WebView2 runtime and the full web experience.

### Option B: Web Application (Browser Mode)
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`

### Option C: Legacy CustomTkinter GUI
```bash
python main.py --tkinter
```

---

## 🗄️ Enhanced Database Schema

### `books` Table
| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique Identifier |
| `title` | `TEXT` | `NOT NULL` | Book Title |
| `author` | `TEXT` | `NOT NULL` | Author Name |
| `category` | `TEXT` | `NOT NULL` | Book Category |
| `status` | `TEXT` | `DEFAULT 'Available'` | Status (`Available` / `Borrowed`) |
| `isbn` | `TEXT` | `OPTIONAL` | International Standard Book Number |
| `cover_url` | `TEXT` | `OPTIONAL` | Book Cover Image Link |
| `total_copies` | `INTEGER` | `DEFAULT 1` | Total Inventory Copies |
| `available_copies` | `INTEGER` | `DEFAULT 1` | Currently Available Copies |

### `members` Table
| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Member Unique Identifier |
| `name` | `TEXT` | `NOT NULL` | Full Name |
| `email` | `TEXT` | `UNIQUE` | Email Address |
| `phone` | `TEXT` | `OPTIONAL` | Contact Phone Number |
| `member_type` | `TEXT` | `DEFAULT 'Student'` | Role (`Student`, `Faculty`, `Staff`) |

### `borrow_records` Table
| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Transaction Record ID |
| `book_id` | `INTEGER` | `FOREIGN KEY` | Referenced Book ID |
| `member_id` | `INTEGER` | `FOREIGN KEY` | Referenced Member ID |
| `issue_date` | `DATE` | `DEFAULT CURRENT_DATE` | Date Book Was Issued |
| `due_date` | `DATE` | `NOT NULL` | Return Due Date |
| `return_date` | `DATE` | `OPTIONAL` | Actual Return Date |
| `fine_amount` | `REAL` | `DEFAULT 0.0` | Overdue Fine Calculated |
| `status` | `TEXT` | `DEFAULT 'Issued'` | Record Status (`Issued` / `Returned`) |

### `users` Table
| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | User ID |
| `username` | `TEXT` | `UNIQUE NOT NULL` | Login Username |
| `email` | `TEXT` | `UNIQUE NOT NULL` | User Email |
| `password_hash` | `TEXT` | `NOT NULL` | Werkzeug SHA-256 Hashed Password |
| `full_name` | `TEXT` | `OPTIONAL` | Display Name |
| `role` | `TEXT` | `DEFAULT 'Student'` | Role (`Admin`, `Librarian`, `Faculty`, `Student`) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Account Registration Date |

### `wishlist` Table
| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique Identifier |
| `user_id` | `INTEGER` | `NOT NULL` | Foreign key referencing `users(id)` |
| `book_id` | `INTEGER` | `NOT NULL` | Foreign key referencing `books(id)` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Bookmark Saved Date |

---

## 🔑 Default Demo Accounts

For immediate testing, default accounts are seeded automatically on first run:
- **👑 Administrator Account**:
  - Username: `admin`
  - Password: `admin123`
- **🎓 Student Account**:
  - Username: `student`
  - Password: `student123`

---

## 📁 Project Structure

```text
library_management/
│
├── app.py                   # Flask Web Application routes, auth & database models
├── main.py                  # Entry point to launch Desktop GUI app
├── desktop_app.py           # CustomTkinter Desktop GUI application logic
├── library.db               # Local SQLite database file
├── run_desktop_app.bat      # Windows batch launcher script
├── requirements.txt         # Project Dependencies
├── README.md                # Project Architecture & Features Guide
├── USER_MANUAL.md           # Desktop & Web Application User Manual
├── static/
│   ├── css/style.css        # Modern Glassmorphic CSS Design System
│   ├── style.css            # Mirrored CSS Bundle
│   └── uploads/pdfs/        # E-Book PDF repository
└── templates/
    ├── base.html            # Global base template with responsive navbar & theme engine
    ├── home.html            # Main Library Landing & Dashboard Portal
    ├── wishlist.html        # "Want to Read" Curated Personal Reading Wishlist
    ├── login.html           # Glassmorphic user login with 1-click demo fill
    ├── register.html        # Account creation & role registration
    ├── profile.html         # User settings, password management & Want to Read collection
    ├── index.html           # Full Books Catalog management & filtering
    ├── members.html         # Member directory
    ├── borrow.html          # Circulation issue/return desk with Due Date Countdown & Overdue Alerts
    ├── reservations.html    # Book hold requests
    ├── analytics.html       # Chart.js visual statistics
    ├── reader.html          # In-browser E-Book PDF reader
    ├── receipt.html         # Printable QR-code loan receipt
    ├── reviews.html         # Star ratings & book feedback
    ├── edit.html            # Book editor
    ├── help.html            # FAQ & User assistance
    └── about.html           # Project background & TQM compliance
```