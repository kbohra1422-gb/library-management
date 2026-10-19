# 📚 Library Management System - Comprehensive User Manual

> **Complete Guide & Operating Manual**

---

## 1. Introduction

Welcome to the **Library Management System**. This user manual guides you through operating both the **Web Portal** (`app.py`) and **Native Desktop GUI** (`main.py`) to manage books, members, borrow/return logs, reservations, star ratings, and analytics.

---

## 2. Getting Started

### Launching the Native Desktop Application (Recommended)
```bash
python main.py
```
Or double-click `run_desktop_app.bat` on Windows.
*Opens LibManager in an independent native desktop window with the full web experience, login authentication, and offline capability.*

### Launching in Web Browser Mode
```bash
python app.py
```
Open your web browser and navigate to: `http://127.0.0.1:5000`

### Launching Legacy CustomTkinter GUI
```bash
python main.py --tkinter
```

---

## 3. Core Modules & Step-by-Step Usage

### 🏠 0. Home Page & Instant Search
- **Central Portal (`/`)**: Overview with live counters for total books, available copies, borrowed books, members, digital e-books, and reservations.
- **Global Search**: Type book title, author, category, or ISBN to search the entire library collection.
- **Featured Books & Quick Actions**: Fast shortcuts to digital reading, reservation desk, and account login.

### 🔐 1. User Authentication & Role Management
- **Login (`/login`)**: Secure sign-in using username or email with SHA-256 hashed password verification.
- **Demo Accounts**: Instant 1-click test buttons for:
  - 👑 **Admin**: `admin` / `admin123` (Full catalog editing, member management, issuing, analytics)
  - 🎓 **Student**: `student` / `student123` (Browsing, personal borrowing history, reservations)
- **Sign Up (`/register`)**: Create new accounts as Student, Faculty, Librarian, or Administrator.
- **User Profile (`/profile`)**: Update profile details, change passwords, and track personal borrowed books.
- **Logout (`/logout`)**: Securely terminate session and return to home.

### 📖 2. Books Catalog & ISBN Auto-Fetch (`/books`)

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