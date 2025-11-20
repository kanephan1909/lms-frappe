# TÀI LIỆU THIẾT KẾ KỸ THUẬT: PHÂN HỆ QUẢN LÝ ĐÀO TẠO (TMS)

**Dự án:** Tích hợp TMS cho Công ty Thương mại
**Nền tảng:** Frappe Framework / Frappe LMS
**Mục tiêu:** Tự động hóa quy trình lập kế hoạch và gán khóa học LMS cho nhân viên dựa trên vị trí công việc.

---

## 1. Cấu trúc Dữ liệu (Data Schema)

### 1.1. DocType: Training Period (Kỳ Đào tạo)
*Mục đích: Quản lý ngân sách và khung thời gian cho từng đợt đào tạo (Quý/Năm).*

| Field Label | Field Name | Field Type | Options / Notes | Mandatory |
| :--- | :--- | :--- | :--- | :---: |
| **Period Name** | `name` | Data | Primary Key (e.g., "2025-Q1") | Yes |
| Start Date | `start_date` | Date | | Yes |
| End Date | `end_date` | Date | | Yes |
| Total Budget | `total_budget` | Currency | Đơn vị: VND | No |
| Is Active | `is_active` | Check | Mặc định: 0 | No |

### 1.2. DocType: Training Plan (Kế hoạch Đào tạo)
*Mục đích: Văn bản kế hoạch chính, chứa danh sách các khóa cần học cho từng bộ phận.*

| Field Label | Field Name | Field Type | Options / Notes | Mandatory |
| :--- | :--- | :--- | :--- | :---: |
| **Series** | `naming_series` | Select | `TRN-PLN-.YYYY.-` | Yes |
| Plan Name | `plan_name` | Data | Tên gợi nhớ | Yes |
| Period | `period` | Link | `Training Period` | Yes |
| Department | `department` | Link | `Department` | No |
| Manager | `training_manager` | Link | `User` | Yes |
| **Status** | `status` | Select | Draft, Submitted, Approved, Rejected | Yes |
| Total Cost | `total_estimated_cost`| Currency | Read Only (Tính tổng từ bảng con) | No |
| **Details** | `plan_details` | Table | `Training Plan Item` | Yes |

### 1.3. Child Table: Training Plan Item
*Mục đích: Chi tiết từng dòng môn học trong kế hoạch.*

| Field Label | Field Name | Field Type | Options / Notes | Mandatory |
| :--- | :--- | :--- | :--- | :---: |
| **LMS Course** | `lms_course` | Link | `LMS Course` (Core Frappe LMS) | Yes |
| Target Role | `designation` | Link | `Designation` (HR Module) | Yes |
| Training Mode | `training_mode` | Select | Online, Offline, Blended | Yes |
| Is Mandatory | `is_mandatory` | Check | Mặc định: 1 | No |
| Deadline | `completion_date` | Date | Hạn chót hoàn thành | Yes |
| Est. Cost | `estimated_cost` | Currency | Chi phí dự kiến | No |

### 1.4. DocType: Training Assignment (Giao nhiệm vụ học tập)
*Mục đích: Bản ghi theo dõi tiến độ cá nhân (sinh ra tự động sau khi Plan được Approved).*

| Field Label | Field Name | Field Type | Options / Notes | Mandatory |
| :--- | :--- | :--- | :--- | :---: |
| **Employee** | `employee` | Link | `Employee` | Yes |
| Course | `lms_course` | Link | `LMS Course` | Yes |
| Related Plan | `training_plan` | Link | `Training Plan` | Yes |
| Status | `status` | Select | Pending, In Progress, Completed, Overdue | Yes |
| LMS Progress | `progress` | Percent | Sync từ LMS | No |

---

## 2. Luồng nghiệp vụ (Workflow Summary)

a. Lập kế hoạch (HR): Tạo Training Plan, chọn kỳ, thêm môn học và chức danh (Designation).

b. Kiểm soát: Hệ thống validate kế hoạch.

c. Phê duyệt (Manager): Chuyển trạng thái sang Approved.

d. Thực thi (System):

- Quét toàn bộ nhân viên khớp điều kiện.

- Ghi danh nhân viên vào khóa học trên LMS.

e. Học tập (Staff): Nhân viên đăng nhập Portal, thấy khóa học trong "My Courses".

f. Báo cáo (HR): Theo dõi tiến độ qua DocType Training Assignment.
