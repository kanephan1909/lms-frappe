# 📚 Module Training - Hướng dẫn sử dụng và phát triển

## 🎯 Tổng quan

Module **Training** là một hệ thống quản lý đào tạo nhân viên tích hợp với LMS (Learning Management System), cho phép:
- Lập kế hoạch đào tạo theo kỳ, phòng ban, chức danh
- Tự động gán khóa học cho nhân viên
- Đồng bộ tiến độ học tập từ LMS
- Quản lý workflow phê duyệt kế hoạch đào tạo

---

## 📁 Cấu trúc Module

```
lms/training/
├── __init__.py                    # Khởi tạo module (có thể để trống)
├── api.py                         # Tất cả các API public (@frappe.whitelist)
├── workspace/                     # Workspace (menu bên trái)
│   └── training/
│       └── training.json          # Định nghĩa menu "Training"
└── doctype/
    ├── training_plan/             # Kế hoạch đào tạo
    │   ├── training_plan.json     # Định nghĩa DocType
    │   ├── training_plan.py       # Logic nghiệp vụ Python
    │   ├── training_plan.js       # Form script JavaScript
    │   └── training_plan_list.js  # List view script JavaScript
    ├── training_assignment/       # Phân công đào tạo
    │   ├── training_assignment.json
    │   ├── training_assignment.py
    │   └── training_assignment.js
    ├── training_plan_item/        # Chi tiết kế hoạch (Child Table)
    │   ├── training_plan_item.json
    │   └── training_plan_item.py
    └── training_period/           # Kỳ đào tạo
        ├── training_period.json
        ├── training_period.py
        └── training_period.js
```

**Lưu ý:** Module phải được khai báo trong `lms/modules.txt`:
```
Training
```

---

## 🗂️ Các DocType chính

### 1. Training Plan (Kế hoạch đào tạo)

**Mục đích:** Lưu trữ kế hoạch đào tạo tổng thể cho một kỳ, phòng ban, hoặc toàn công ty.

**Các trường quan trọng:**
- `plan_name`: Tên kế hoạch
- `period`: Kỳ đào tạo (Link đến Training Period)
- `department`: Phòng ban (optional)
- `training_manager`: Người quản lý đào tạo (Link đến User)
- `status`: Trạng thái (`Draft` → `Submitted` → `Approved` / `Rejected`)
- `total_estimated_cost`: Tổng chi phí ước tính (tự động tính)
- `plan_details`: Bảng con (Child Table) chứa các khóa học cần đào tạo

**Workflow:**
```
Draft → Submitted → Approved / Rejected
```

**Quyền truy cập:**
- **Training HR**: Có thể tạo, sửa, xóa plan ở trạng thái `Draft` hoặc `Submitted`
- **Training Manager/Approver**: Chỉ có thể xem và phê duyệt plan ở trạng thái `Submitted`

**File:** `doctype/training_plan/training_plan.py`

**Các hàm quan trọng:**
- `validate()`: Validate dữ liệu, tính toán chi phí
- `validate_status_change()`: Kiểm tra quyền thay đổi status
- `on_update()`: Tự động tạo Training Assignment khi plan được Approve
- `create_training_assignments()`: Tạo assignment cho nhân viên phù hợp

---

### 2. Training Assignment (Phân công đào tạo)

**Mục đích:** Ghi nhận việc một nhân viên cụ thể được gán học một khóa học cụ thể.

**Các trường quan trọng:**
- `employee`: Nhân viên (Link đến Employee)
- `lms_course`: Khóa học (Link đến LMS Course)
- `training_plan`: Kế hoạch đào tạo liên quan (Link đến Training Plan)
- `status`: Trạng thái (`Pending` / `In Progress` / `Completed` / `Overdue`)
- `progress`: Tiến độ học tập (%, tự động sync từ LMS)
- `completion_date`: Deadline hoàn thành

**File:** `doctype/training_assignment/training_assignment.py`

**Logic tự động:**
- Tự động sync `progress` từ `LMS Enrollment` mỗi khi lưu
- Tự động cập nhật `status` dựa trên `progress` và `completion_date`:
  - `progress = 100%` → `Completed`
  - `progress > 0%` và `deadline chưa đến` → `In Progress`
  - `progress = 0%` → `Pending`
  - `progress < 100%` và `deadline đã qua` → `Overdue`

---

### 3. Training Plan Item (Chi tiết kế hoạch)

**Mục đích:** Child Table của Training Plan, lưu từng khóa học trong kế hoạch.

**Các trường:**
- `lms_course`: Khóa học
- `designation`: Chức danh đích (nhân viên có chức danh này sẽ được gán học)
- `training_mode`: Hình thức đào tạo (`Online` / `Offline` / `Blended`)
- `is_mandatory`: Bắt buộc hay không
- `completion_date`: Deadline
- `estimated_cost`: Chi phí ước tính

**File:** `doctype/training_plan_item/training_plan_item.json`

---

## 🔄 Luồng nghiệp vụ chi tiết

### Bước 1: Training HR tạo Training Plan

1. Vào **Training Plan** → Click **New**
2. Nhập thông tin:
   - `plan_name`: "Đào tạo Q1 2025"
   - `period`: Chọn kỳ đào tạo (ví dụ: "Q1-2025")
   - `department`: (Optional) Chọn phòng ban
   - `training_manager`: Chọn người duyệt
3. Thêm các dòng trong `plan_details`:
   - Dòng 1: `Python Basics` cho `Developer`, deadline `2025-03-31`, cost `500,000 VND`
   - Dòng 2: `SQL Advanced` cho `Developer`, deadline `2025-03-31`, cost `300,000 VND`
   - Dòng 3: `Project Management` cho `Manager`, deadline `2025-03-31`, cost `1,000,000 VND`
4. Click **Save** → Status = `Draft`

**Hệ thống tự động:**
- Validate `completion_date` phải nằm trong khoảng thời gian của `period`
- Tính `total_estimated_cost` = tổng các `estimated_cost`

---

### Bước 2: Training HR Submit kế hoạch

1. Mở Training Plan vừa tạo
2. Đổi `status` từ `Draft` → `Submitted`
3. Click **Save**

**Hệ thống tự động:**
- Gửi notification cho `training_manager` (người được chỉ định duyệt)
- Tạo `Notification Log` để Training Manager thấy trong thông báo

---

### Bước 3: Training Manager/Approver phê duyệt

1. Training Manager đăng nhập → Xem thông báo
2. Vào **Training Plan List** → Chỉ thấy các plan có `status = Submitted`
3. Mở plan cần duyệt
4. Click **Approve** hoặc **Reject**

**Khi Approve (`status` → `Approved`):**

**Hệ thống tự động chạy `create_training_assignments()`:**

```
Với mỗi dòng trong plan_details:
  ├─ Tìm tất cả Employee có:
  │   ├─ designation = dòng.designation
  │   ├─ status = "Active"
  │   └─ department = plan.department (nếu có)
  │
  └─ Với mỗi Employee tìm được:
      ├─ Kiểm tra: Đã có Training Assignment cho (employee, course, plan) chưa?
      │
      ├─ Nếu CHƯA CÓ:
      │   ├─ Tạo Training Assignment mới:
      │   │   ├─ employee = Employee.name
      │   │   ├─ lms_course = dòng.lms_course
      │   │   ├─ training_plan = Plan.name
      │   │   ├─ status = "Pending"
      │   │   └─ completion_date = dòng.completion_date
      │   │
      │   └─ Nếu employee có user_id:
      │       └─ Tự động enroll vào LMS Course (tạo LMS Enrollment)
      │
      └─ Nếu ĐÃ CÓ: Bỏ qua (tránh duplicate)
```

**Ví dụ cụ thể:**

- Plan có:
  - `department` = "IT"
  - `plan_details[0]`: `Python Basics` cho `Developer`
  
- Tìm được 3 nhân viên:
  - `EMP001` (Developer, IT, user_id = "user1@example.com")
  - `EMP002` (Developer, IT, user_id = "user2@example.com")
  - `EMP003` (Developer, IT, user_id = None)

- Hệ thống tạo:
  - `Training Assignment` cho EMP001 → Enroll vào LMS
  - `Training Assignment` cho EMP002 → Enroll vào LMS
  - `Training Assignment` cho EMP003 → Không enroll (chưa có user_id)

---

### Bước 4: Nhân viên học và đồng bộ tiến độ

1. Nhân viên vào LMS → Học khóa học
2. Tiến độ được cập nhật trong `LMS Enrollment`
3. Mỗi khi lưu `Training Assignment`, hệ thống tự động:
   - Sync `progress` từ `LMS Enrollment`
   - Cập nhật `status` dựa trên `progress` và `deadline`

**Ví dụ:**
- `progress = 50%`, `completion_date = 2025-04-30`, `today = 2025-04-15`
  → `status = "In Progress"`
  
- `progress = 50%`, `completion_date = 2025-04-10`, `today = 2025-04-15`
  → `status = "Overdue"`

---

## 🔌 API Reference

Tất cả API được định nghĩa trong `api.py` và có decorator `@frappe.whitelist()` để có thể gọi từ frontend.

### 1. `get_training_dashboard_stats()`

**Mục đích:** Lấy thống kê tổng quan về Training Assignment.

**Quyền:** Training HR, Training Manager, Training Approver, System Manager

**Returns:**
```python
{
    "total_assignments": 100,
    "status_counts": {
        "Pending": 20,
        "In Progress": 50,
        "Completed": 25,
        "Overdue": 5
    }
}
```

**Gọi từ JS:**
```javascript
frappe.call({
    method: 'lms.training.api.get_training_dashboard_stats',
    callback: function(r) {
        console.log(r.message.total_assignments);
        console.log(r.message.status_counts);
    }
});
```

---

### 2. `add_employees_to_course(employees, lms_course, training_plan, completion_date)`

**Mục đích:** Thêm nhiều nhân viên vào một khóa học (tạo Training Assignment).

**Quyền:** Training HR, System Manager

**Parameters:**
- `employees`: List employee names hoặc string JSON
- `lms_course`: Tên LMS Course
- `training_plan`: (Optional) Tên Training Plan
- `completion_date`: Deadline

**Returns:**
```python
{
    "added": 5,      # Số nhân viên đã thêm thành công
    "skipped": 2     # Số nhân viên đã có assignment (bỏ qua)
}
```

**Gọi từ JS:**
```javascript
frappe.call({
    method: 'lms.training.api.add_employees_to_course',
    args: {
        employees: ['EMP001', 'EMP002', 'EMP003'],
        lms_course: 'Python Basics',
        training_plan: 'TRN-PLN-2025-00001',
        completion_date: '2025-03-31'
    },
    callback: function(r) {
        frappe.msgprint(`Đã thêm ${r.message.added} nhân viên`);
    }
});
```

**Logic:**
1. Với mỗi employee:
   - Kiểm tra đã có Training Assignment chưa (dựa trên employee + course + plan)
   - Nếu chưa có → Tạo mới
   - Nếu có user_id → Tự động enroll vào LMS

---

### 3. `enroll_employee_in_lms(assignment_name)`

**Mục đích:** Enroll nhân viên vào LMS Course từ Training Assignment.

**Quyền:** Training HR, System Manager

**Parameters:**
- `assignment_name`: Tên Training Assignment document

**Returns:**
```python
{
    "success": True,
    "message": "Đã enroll nhân viên vào khóa học thành công"
}
```

**Gọi từ JS:**
```javascript
frappe.call({
    method: 'lms.training.api.enroll_employee_in_lms',
    args: {
        assignment_name: 'abc123xyz'
    },
    callback: function(r) {
        frappe.msgprint(r.message.message);
    }
});
```

---

### 4. `export_training_plan(plan_name)`

**Mục đích:** Export Training Plan ra file Excel.

**Quyền:** Training HR, System Manager

**Parameters:**
- `plan_name`: Tên Training Plan document

**Returns:**
```python
{
    "file_url": "/files/Training_Plan_TRN-PLN-2025-00001_20250115_143022.xlsx",
    "filename": "Training_Plan_TRN-PLN-2025-00001_20250115_143022.xlsx"
}
```

**Gọi từ JS:**
```javascript
frappe.call({
    method: 'lms.training.api.export_training_plan',
    args: {
        plan_name: 'TRN-PLN-2025-00001'
    },
    callback: function(r) {
        // Download file
        const link = document.createElement('a');
        link.href = r.message.file_url;
        link.download = r.message.filename;
        link.click();
    }
});
```

**File Excel bao gồm:**
- Headers: Plan Name, Period, Department, Training Manager, Status, Total Cost, LMS Course, Designation, Training Mode, Is Mandatory, Completion Date, Estimated Cost
- Mỗi dòng = 1 plan_detail (1 khóa học trong kế hoạch)

---

### 5. `import_training_plan(file_url, update_existing=0)`

**Mục đích:** Import Training Plan từ file Excel/CSV.

**Quyền:** Training HR, System Manager

**Parameters:**
- `file_url`: URL file Excel/CSV đã upload
- `update_existing`: `0` (không cập nhật) hoặc `1` (cập nhật nếu đã tồn tại)

**Returns:**
```python
{
    "imported": 3,   # Số plan mới import
    "updated": 2     # Số plan đã cập nhật
}
```

**Gọi từ JS:**
```javascript
frappe.call({
    method: 'lms.training.api.import_training_plan',
    args: {
        file_url: '/files/plan_import.xlsx',
        update_existing: 1
    },
    callback: function(r) {
        frappe.msgprint(`Đã import ${r.message.imported} kế hoạch`);
    }
});
```

**Format file Excel/CSV:**

Bắt buộc có các cột:
- `Plan Name`
- `LMS Course`
- `Designation`
- `Training Mode`
- `Completion Date`

Optional:
- `Period`
- `Department`
- `Training Manager`
- `Status`
- `Estimated Cost`
- `Is Mandatory`

**Logic:**
1. Đọc file Excel/CSV
2. Group các dòng theo `Plan Name`
3. Với mỗi plan:
   - Nếu chưa tồn tại → Tạo mới
   - Nếu đã tồn tại và `update_existing=1`:
     - **KHÔNG cho phép cập nhật plan đã Approved** (bảo mật workflow)
     - Kiểm tra quyền write
     - Cập nhật các field từ dòng đầu tiên của plan
     - Xóa toàn bộ `plan_details` cũ
     - Thêm lại `plan_details` từ các dòng còn lại
4. Validate:
   - `LMS Course` phải tồn tại
   - `Designation` phải tồn tại
   - Plan phải có ít nhất 1 plan_detail hợp lệ

---

## 🛡️ Bảo mật và Quyền truy cập

### Permissions trong DocType JSON

**Training Plan:**
- `Training HR`: Create, Read, Write, Delete (full quyền)
- `Training Manager`: Read, Write (không tạo mới)
- `Training Approver`: Read, Write (không tạo mới)

**Training Assignment:**
- `Training HR`: Create, Read, Write (không xóa)
- `Training Manager`: Read only
- `Employee`: Read only (chỉ xem assignment của mình)

### Kiểm tra quyền trong API

**Tất cả API đều có kiểm tra quyền:**

```python
@frappe.whitelist()
def my_api():
    # Kiểm tra role
    user_roles = frappe.get_roles()
    if "Training HR" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Bạn không có quyền"), frappe.PermissionError)
    
    # Hoặc kiểm tra permission cụ thể
    if not frappe.has_permission("Training Plan", "read", plan_name):
        frappe.throw(_("Không có quyền truy cập"), frappe.PermissionError)
```

---

## 💻 Cách phát triển thêm tính năng

### Thêm API mới

**Bước 1:** Thêm hàm vào `api.py`

```python
@frappe.whitelist()
def get_employee_assignments(employee):
    """
    Lấy danh sách Training Assignment của một nhân viên
    """
    # Kiểm tra quyền
    user = frappe.session.user
    roles = frappe.get_roles()
    
    # Chỉ Training HR, System Manager, hoặc chính nhân viên đó mới được xem
    employee_user_id = frappe.db.get_value("Employee", employee, "user_id")
    
    if (
        "Training HR" not in roles
        and "System Manager" not in roles
        and employee_user_id != user
    ):
        frappe.throw(_("Bạn không có quyền"), frappe.PermissionError)
    
    # Lấy dữ liệu
    assignments = frappe.get_all(
        "Training Assignment",
        filters={"employee": employee},
        fields=["name", "lms_course", "status", "progress", "completion_date"],
        order_by="completion_date asc"
    )
    
    return assignments
```

**Bước 2:** Gọi từ JavaScript

```javascript
frappe.call({
    method: 'lms.training.api.get_employee_assignments',
    args: {
        employee: 'EMP001'
    },
    callback: function(r) {
        console.log(r.message); // List assignments
    }
});
```

---

### Thêm validation logic vào DocType

**File:** `doctype/training_plan/training_plan.py`

```python
class TrainingPlan(Document):
    def validate(self):
        # Validate hiện có
        self.validate_plan_details()
        self.calculate_total_cost()
        self.validate_status_change()
        
        # Thêm validation mới
        self.validate_budget_limit()
    
    def validate_budget_limit(self):
        """Kiểm tra tổng chi phí không vượt quá ngân sách"""
        budget_limit = frappe.db.get_value(
            "Training Period",
            self.period,
            "budget_limit"
        )
        
        if budget_limit and self.total_estimated_cost > budget_limit:
            frappe.throw(
                _("Tổng chi phí ({0}) vượt quá ngân sách ({1})").format(
                    self.total_estimated_cost,
                    budget_limit
                )
            )
```

---

### Thêm button/custom action trong Form

**File:** `doctype/training_plan/training_plan.js`

```javascript
frappe.ui.form.on('Training Plan', {
    refresh: function(frm) {
        // Thêm button mới
        if (frm.doc.status === 'Approved' && !frm.is_new()) {
            frm.add_custom_button(__('Tạo báo cáo'), function() {
                // Gọi API hoặc mở dialog
                frappe.call({
                    method: 'lms.training.api.generate_report',
                    args: { plan_name: frm.doc.name },
                    callback: function(r) {
                        // Xử lý kết quả
                    }
                });
            }, __('Actions'));
        }
    }
});
```

---

## 📝 Best Practices

1. **Luôn kiểm tra quyền trong API**
   - Không tin tưởng client-side (JavaScript)
   - Luôn validate quyền ở server-side

2. **Sử dụng `ignore_permissions=True` cẩn thận**
   - Chỉ dùng trong luồng hệ thống tự động (như `create_training_assignments()`)
   - Phải đảm bảo logic đã kiểm tra quyền trước đó

3. **Error handling**
   - Luôn có try-catch trong các thao tác quan trọng
   - Log lỗi bằng `frappe.log_error()` để debug

4. **Validate dữ liệu**
   - Validate ở cả client-side (JS) và server-side (Python)
   - Client-side để UX tốt hơn (phản hồi nhanh)
   - Server-side để bảo mật (không thể bypass)

5. **Transaction safety**
   - Các thao tác tạo nhiều record nên có rollback nếu lỗi
   - Sử dụng `frappe.db.commit()` hoặc để Frappe tự quản lý

---

## 🔍 Debugging

### Xem logs

```bash
# Xem logs realtime
bench --site your-site tail

# Xem error logs
bench --site your-site console
```

### Test API từ console

```python
# Vào Python console
bench --site your-site console

# Import và gọi API
import frappe
from lms.training import api

# Gọi hàm (phải set user trước)
frappe.set_user('user@example.com')
result = api.get_training_dashboard_stats()
print(result)
```

### Debug JavaScript

```javascript
// Thêm console.log trong JS file
console.log('Debug info:', frm.doc);

// Sử dụng frappe.show_alert để hiển thị thông báo
frappe.show_alert('Debug message', 5);
```

---

## 📚 Tài liệu tham khảo

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [Frappe DocType Documentation](https://frappeframework.com/docs/user/en/desk/doctype)
- [Frappe API Documentation](https://frappeframework.com/docs/user/en/api)

---

## 🤝 Đóng góp

Nếu bạn phát hiện bug hoặc muốn thêm tính năng mới, vui lòng:
1. Tạo issue trên repository
2. Tạo pull request với code changes
3. Đảm bảo code đã được test kỹ

---

---

## 🆕 Cách tạo Module mới trong Frappe

### Bước 1: Tạo cấu trúc thư mục

```bash
# Trong app của bạn (ví dụ: apps/lms)
cd apps/lms/lms

# Tạo thư mục module mới
mkdir -p my_module/doctype
mkdir -p my_module/workspace/my_module
```

### Bước 2: Tạo file __init__.py

```python
# lms/my_module/__init__.py
# Có thể để trống hoặc import các module con
```

### Bước 3: Khai báo module trong modules.txt

```bash
# Thêm tên module vào lms/modules.txt
echo "My Module" >> lms/modules.txt
```

**File:** `lms/modules.txt`
```
LMS
Job
Training
My Module
```

### Bước 4: Tạo DocType đầu tiên

```bash
# Sử dụng bench để tạo DocType
bench --site your-site make-doctype "My DocType"
```

Hoặc tạo thủ công:
- Tạo thư mục: `lms/my_module/doctype/my_doctype/`
- Tạo file JSON: `my_doctype.json` (định nghĩa fields)
- Tạo file Python: `my_doctype.py` (logic nghiệp vụ)
- Tạo file JS: `my_doctype.js` (form script)

### Bước 5: Tạo Workspace (Menu bên trái)

**File:** `lms/my_module/workspace/my_module/my_module.json`

```json
{
  "app": "lms",
  "label": "My Module",
  "title": "My Module",
  "icon": "folder",
  "module": "My Module",
  "name": "My Module",
  "public": 1,
  "roles": ["System Manager"],
  "links": [
    {
      "type": "Link",
      "label": "My DocType",
      "link_type": "DocType",
      "link_to": "My DocType"
    }
  ]
}
```

### Bước 6: Migrate và cài đặt

```bash
# Migrate database
bench --site your-site migrate

# Hoặc nếu cần cài lại
bench --site your-site reinstall
```

---

## 🎨 Nguyên lý hoạt động của JavaScript trong Frappe Form

### 1. Frappe tự động load JS files

**Quy tắc naming convention:**

Khi bạn mở một DocType form, Frappe tự động tìm và load các file JS sau:

```
doctype/{doctype_name}/{doctype_name}.js          → Form script
doctype/{doctype_name}/{doctype_name}_list.js     → List view script
doctype/{doctype_name}/{doctype_name}_tree.js     → Tree view script (nếu có)
doctype/{doctype_name}/{doctype_name}_calendar.js → Calendar view script (nếu có)
```

**Ví dụ với Training Plan:**
- Form view → Load `training_plan.js`
- List view → Load `training_plan_list.js`

### 2. Cách Frappe render form

**Quy trình:**

```
1. User mở Training Plan form
   ↓
2. Frappe load training_plan.json (định nghĩa fields)
   ↓
3. Frappe tự động render form dựa trên JSON:
   - Tạo các field inputs
   - Tạo các section breaks
   - Tạo child tables
   ↓
4. Frappe load training_plan.js
   ↓
5. Chạy các event handlers:
   - onload() → Chạy khi form load
   - refresh() → Chạy mỗi khi form refresh
   - {fieldname}() → Chạy khi field thay đổi
```

### 3. Các event handlers trong training_plan.js

```javascript
frappe.ui.form.on('Training Plan', {
    // Chạy khi form được load lần đầu
    onload: function(frm) {
        // frm = form object
        // frm.doc = document data
        // frm.fields_dict = dictionary các fields
    },
    
    // Chạy mỗi khi form refresh (sau khi save, sau khi load, ...)
    refresh: function(frm) {
        // Thêm buttons, thay đổi field properties, ...
    },
    
    // Chạy khi field 'period' thay đổi
    period: function(frm) {
        // frm.doc.period = giá trị mới
    },
    
    // Chạy khi field 'status' thay đổi
    status: function(frm) {
        // Logic xử lý khi status thay đổi
    }
});
```

### 4. Các phương thức quan trọng của frm object

```javascript
refresh: function(frm) {
    // Set giá trị field
    frm.set_value('status', 'Draft');
    
    // Set property của field
    frm.set_df_property('status', 'read_only', 1);
    frm.set_df_property('status', 'options', 'Draft\nSubmitted');
    
    // Thêm custom button
    frm.add_custom_button('Tên nút', function() {
        // Xử lý khi click
    }, 'Nhóm nút');
    
    // Kiểm tra form mới
    if (frm.is_new()) {
        // Logic cho form mới
    }
    
    // Disable save
    frm.disable_save();
    
    // Set read only
    frm.set_read_only();
    
    // Reload document
    frm.reload_doc();
    
    // Lấy giá trị field
    const status = frm.doc.status;
    
    // Kiểm tra field đã thay đổi
    if (frm.has_value_changed('status')) {
        // Logic khi status thay đổi
    }
}
```

### 5. Ví dụ cụ thể từ training_plan.js

**Thêm button Export:**

```javascript
refresh: function(frm) {
    // Chỉ hiển thị cho Training HR và System Manager
    if ((frappe.user_roles.includes('Training HR') || 
         frappe.user_roles.includes('System Manager')) && 
        !frm.is_new()) {
        
        // Thêm button vào header
        frm.page.add_inner_button(__('Export'), function() {
            export_training_plan(frm);
        }, __('Actions'));
    }
}
```

**Giải thích:**
- `frm.page.add_inner_button()`: Thêm button vào header của form
- `frappe.user_roles`: Array các role của user hiện tại
- `frm.is_new()`: Kiểm tra form có phải mới tạo không
- `__()`: Hàm translate (đa ngôn ngữ)

**Thay đổi field properties:**

```javascript
refresh: function(frm) {
    // Training HR chỉ có thể chọn Draft hoặc Submitted
    if (frappe.user_roles.includes('Training HR')) {
        frm.set_df_property('status', 'options', 'Draft\nSubmitted');
        frm.set_df_property('status', 'read_only', 0);
    }
}
```

**Giải thích:**
- `set_df_property(fieldname, property, value)`: Thay đổi property của field
- `options`: Danh sách các giá trị có thể chọn (phân cách bằng `\n`)
- `read_only`: Field có read-only không

---

## 📋 Cách tạo Menu "Training" bên trái sidebar

### Cách 1: Tạo Workspace tự động (Khuyến nghị)

Frappe tự động tạo Workspace dựa trên:
1. **Module name** trong `modules.txt`
2. **Workspace JSON file** trong `workspace/{module_name}/{module_name}.json`

### Bước 1: Đảm bảo module đã được khai báo

**File:** `lms/modules.txt`
```
Training
```

### Bước 2: Tạo Workspace JSON

**File:** `lms/training/workspace/training/training.json`

```json
{
  "app": "lms",
  "label": "Training",
  "title": "Training",
  "icon": "clipboard",
  "module": "Training",
  "name": "Training",
  "public": 1,
  "roles": [
    "Training HR",
    "Training Manager",
    "Training Approver"
  ],
  "links": [
    {
      "type": "Card Break",
      "label": "Training Management"
    },
    {
      "type": "Link",
      "label": "Training Period",
      "link_type": "DocType",
      "link_to": "Training Period"
    },
    {
      "type": "Link",
      "label": "Training Plan",
      "link_type": "DocType",
      "link_to": "Training Plan"
    },
    {
      "type": "Link",
      "label": "Training Assignment",
      "link_type": "DocType",
      "link_to": "Training Assignment"
    }
  ],
  "shortcuts": [
    {
      "type": "DocType",
      "label": "Training Plan",
      "link_to": "Training Plan",
      "doc_view": "List",
      "color": "Blue"
    }
  ]
}
```

**Giải thích các field quan trọng:**

- `app`: Tên app (phải khớp với app_name trong hooks.py)
- `module`: Tên module (phải khớp với tên trong modules.txt)
- `name`: Tên workspace (thường giống module name)
- `label`: Tên hiển thị trong menu
- `icon`: Icon hiển thị (có thể dùng tên icon hoặc emoji)
- `public`: `1` = public workspace, `0` = private
- `roles`: Danh sách role có thể xem workspace này
- `links`: Danh sách các link trong workspace
  - `type: "Link"`: Link đến DocType/Report/Page
  - `type: "Card Break"`: Tạo section mới
- `shortcuts`: Các shortcut hiển thị ở đầu workspace

### Bước 3: Migrate database

```bash
bench --site your-site migrate
```

Frappe sẽ tự động:
1. Tạo Workspace document trong database
2. Hiển thị menu "Training" bên trái sidebar
3. Load các links và shortcuts đã định nghĩa

### Cách 2: Tạo Workspace thủ công từ UI

1. Vào **Workspace** → Click **New**
2. Điền thông tin:
   - **Title**: "Training"
   - **Module**: "Training"
   - **Icon**: Chọn icon (ví dụ: clipboard)
   - **Public**: Check nếu muốn public
3. Thêm **Links**:
   - Click **Add Row** trong Links
   - Chọn **Type**: "Link"
   - **Label**: "Training Plan"
   - **Link Type**: "DocType"
   - **Link To**: "Training Plan"
4. Click **Save**

### Các icon có sẵn trong Frappe

Frappe sử dụng [Font Awesome icons](https://fontawesome.com/icons). Một số icon phổ biến:

- `clipboard` - Clipboard
- `book` - Book
- `users` - Users
- `folder` - Folder
- `chart-line` - Chart
- `cog` - Settings
- `file` - File
- `calendar` - Calendar

Hoặc bạn có thể dùng emoji:
- `📚` - Books
- `🎓` - Graduation cap
- `📋` - Clipboard
- `👥` - Users

### Kiểm tra Workspace đã được tạo

```bash
# Vào console
bench --site your-site console

# Kiểm tra Workspace
import frappe
workspace = frappe.get_doc("Workspace", "Training")
print(workspace.links)
```

---

## 🔍 Debugging: Kiểm tra JS có được load không

### Cách 1: Kiểm tra trong Browser Console

1. Mở Training Plan form
2. Mở Developer Tools (F12)
3. Vào tab **Console**
4. Gõ:
```javascript
// Kiểm tra form object
cur_frm

// Kiểm tra các event handlers đã được đăng ký
cur_frm.script_manager.scripts
```

### Cách 2: Thêm console.log trong JS file

```javascript
frappe.ui.form.on('Training Plan', {
    refresh: function(frm) {
        console.log('Training Plan form loaded!');
        console.log('Current status:', frm.doc.status);
    }
});
```

### Cách 3: Kiểm tra file có được load trong Network tab

1. Mở Developer Tools (F12)
2. Vào tab **Network**
3. Filter: **JS**
4. Reload page
5. Tìm file `training_plan.js` trong danh sách

---

## 📚 Tài liệu tham khảo

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [Frappe DocType Documentation](https://frappeframework.com/docs/user/en/desk/doctype)
- [Frappe JavaScript API](https://frappeframework.com/docs/user/en/api/javascript)
- [Frappe Workspace Documentation](https://frappeframework.com/docs/user/en/desk/workspace)

---

**Chúc bạn phát triển thành công! 🚀**

