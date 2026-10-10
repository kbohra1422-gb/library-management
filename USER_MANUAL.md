# 📚 Library Management System - Comprehensive User Manual

> **Complete Guide & Operating Manual**

---

## 1. Introduction

Welcome to the **Library Management System**. This user manual guides you through operating both the **Web Portal** (`app.py`) and **Native Desktop GUI** (`main.py`) to manage books, members, borrow/return logs, reservations, star ratings, and analytics.

---

## 2. Getting Started

### Launching the Web Application (Flask)
```bash
python app.py
```
Open your web browser and navigate to: `http://127.0.0.1:5000`

### Launching the Desktop Application (CustomTkinter)
```bash
python main.py
```
Or double-click `run_desktop_app.bat` on Windows.

---

## 3. Core Modules & Step-by-Step Usage

### 📖 1. Books Catalog & ISBN Auto-Fetch
- **Auto-Fetch by ISBN**: Enter an ISBN (e.g. `9780132350884`) and click **Fetch** to automatically auto-fill Title, Author, Category, and Cover Image URL from Open Library API.
- **Multi-Copy Quantity**: Set `total_copies` when adding books. `available_copies` updates dynamically.
- **Multi-Criteria Sorting**: Sort catalog by Newest, Title (A-Z / Z-A), Author (A-Z), or Category.

### 👤 2. Member & Profile Management
- Navigate to the **Members** tab to register Students, Faculty, and Staff.
- Manage contact details (Email, Phone Number) and view registration history.

### 🔄 3. Book Issue, Return & Fine Tracker
- Go to the **Issue / Return** page to issue books to registered members.
- **Automated Due Date**: Automatically sets 14 days return window.
- **Late Fine Calculator**: Overdue books accumulate ₹5/day fine, calculated dynamically.
- **Printable Slips & Receipts**: Click **📄 Slip** to open a clean printable transaction receipt featuring an authentic QR code verification badge.

### 📌 4. Book Reservations & Hold Queue
- Navigate to **Reservations** to place hold requests on books currently marked as `Borrowed`.
- When the book is returned, track pending hold requests and fulfill or cancel holds.

### ⭐ 5. Reader Reviews & Star Ratings
- Click **⭐ Reviews** on any book card/table row.
- Submit 1 to 5 star ratings with written community feedback.
- View average book score badges (e.g. ⭐ 4.8 / 5.0).

### 📊 6. Visual Analytics Dashboard
- Open the **Analytics** page to view live interactive Chart.js charts:
  - Books per Category (Bar Chart)
  - Inventory Status Availability Ratio (Doughnut Chart)
  - Member Demographics (Bar Chart)

---

## 4. Troubleshooting & Support

If you encounter any issues, click **Help & FAQ** in the navigation bar.