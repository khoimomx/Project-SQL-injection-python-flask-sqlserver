# SQLi Labs · Flask + SQL Server

Phòng thực hành gồm 12 bài SQL injection bằng tiếng Việt, lấy cảm hứng từ [Audi-1/sqli-labs](https://github.com/Audi-1/sqli-labs). Mỗi bài có một endpoint HTTP thật, dữ liệu giả, gợi ý, payload mẫu, câu SQL đang chạy và hai chế độ để so sánh kết quả. Phản hồi và độ trễ đến từ Microsoft SQL Server.

## Khởi động trên Windows

Cần Python 3.10 trở lên, Microsoft SQL Server 2016 trở lên và Microsoft ODBC Driver 18 for SQL Server. Mặc định ứng dụng kết nối instance `localhost` bằng tài khoản Windows hiện tại. Tài khoản khởi tạo cần quyền tạo database và quản lý các đối tượng trong database đó.

Trong PowerShell, bắt đầu từ thư mục cha `Project_SQL_injection`:

```powershell
cd .\Sqli_labs_Python_SqlServer
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py init
.\.venv\Scripts\python.exe app.py serve
```

Mở **[http://127.0.0.1:5000](http://127.0.0.1:5000)**. Nhấn Ctrl+C trong terminal để dừng. Với môi trường Python đã có Flask và pyodbc, có thể dùng trực tiếp `python app.py init` và `python app.py serve`. Khi cổng 5000 đang bận, dùng `python app.py serve --port 5050` rồi mở http://127.0.0.1:5050.

### Instance hoặc tài khoản khác

- Instance có tên, ví dụ SQL Server Express: đặt `$env:LAB_SQL_SERVER = '.\SQLEXPRESS'` trước khi chạy các lệnh trên.
- Có thể đặt `LAB_ODBC_DRIVER` theo đúng tên driver trong `pyodbc.drivers()`. Mặc định là `ODBC Driver 18 for SQL Server`.
- Với SQL Authentication, đặt `LAB_SQL_USER` và `LAB_SQL_PASSWORD` trong môi trường của terminal. Nếu không có `LAB_SQL_USER`, ứng dụng dùng Windows Authentication.
- Nếu dùng tài khoản riêng để chạy web, cấp cho tài khoản đó quyền kết nối database lab và `IMPERSONATE ON USER::lab_student` trong database này. Tài khoản chạy web có thể khác tài khoản dùng cho `init`.

### Khởi tạo và reset

`init` tạo **SQLiLabs_Flask_Training**, đánh dấu database thuộc dự án, tạo schema và nạp dữ liệu mẫu. Có thể chạy lại lệnh này để kiểm tra schema mà vẫn giữ dữ liệu. Nếu tên đã thuộc một database khác, lệnh sẽ dừng.

```powershell
python app.py reset
```

`reset` làm mới sáu bảng trong database đã đánh dấu, bao gồm nhật ký, hồ sơ và bộ lọc đã lưu của tất cả người học. Các database khác nằm ngoài phạm vi lệnh. Nên dùng lệnh sau buổi thực hành.

## Bộ bài tập

| Bài | Chủ đề | Đường đi của đầu vào | Tín hiệu cần quan sát |
| --- | --- | --- | --- |
| 01 | UNION, ngữ cảnh số | GET /lab/1 · id trong URL | Một dòng ngoài danh mục ở trang chi tiết |
| 02 | UNION, ngữ cảnh chuỗi LIKE | POST /lab/2 · trường q | Dòng bổ sung trong danh sách kết quả |
| 03 | Error-based, ngữ cảnh chuỗi | GET /lab/3 · sku trong URL | Mã văn bản xuất hiện trong lỗi chuyển kiểu |
| 04 | Error-based, truy vấn con | POST /lab/4 · trường id | Trích mã bằng biểu thức T-SQL ở vị trí số |
| 05 | Boolean blind | GET /lab/5 · sku trong URL | Có sản phẩm / không có sản phẩm |
| 06 | Boolean blind | POST /lab/6 · trường invite | Mã mời hợp lệ / không hợp lệ |
| 07 | Time blind, ngữ cảnh số | GET /lab/7 · id trong URL | Cùng nội dung, độ trễ có điều kiện |
| 08 | Time blind, ngữ cảnh chuỗi | POST /lab/8 · trường invite | Độ trễ trong form có chuỗi nháy đơn |
| 09 | Header, INSERT | POST /lab/9 · X-Lab-Client hoặc User-Agent | Lỗi khi ghi giá trị header vào nhật ký |
| 10 | Cookie, UNION | GET /lab/10 · cookie lab_visitor | Cùng URL nhưng khác tập kết quả |
| 11 | UPDATE | POST /lab/11 · trường name | Hai cột thay đổi qua một ô nhập |
| 12 | Second-order | POST /lab/12/save rồi POST /lab/12 | Giá trị đã lưu chỉ phát huy tác dụng ở lần dùng sau |

Bài 04 giữ mục tiêu Double Query bằng lỗi chuyển kiểu của T-SQL. Bài Dump into Outfile của MySQL dùng một cú pháp riêng để ghi tệp trên máy chủ. Bộ lab này tập trung vào những tín hiệu có thể quan sát trực tiếp trong Flask + SQL Server.

## Một lượt thực hành

1. Mở **bài 01**, giữ chế độ **Dễ lỗi**. Gửi giá trị gốc `1` rồi thử `-1`. Xem HTTP status và nội dung phản hồi.
2. Trong **Gợi ý và payload mẫu**, chọn **Ghép thêm một dòng → Dùng thử**, rồi **Gửi request**. Kết quả sẽ chứa mã của thẻ `union-id`.
3. Chọn **Đã sửa** rồi gửi lại cùng payload. Giá trị thử được giữ nguyên ở ô nhập. Mở **Câu SQL của bài này** để đối chiếu vị trí ghép dữ liệu với tham số `?`.

Workbench gửi request qua trình duyệt. Mục **Request đã gửi** hiển thị phương thức, URL và phần dữ liệu của bài. Thời gian đo bao gồm toàn bộ lượt gửi và nhận HTTP. Trong bài 07/08, SQL Server thực thi `WAITFOR DELAY`; hãy so sánh những lần thử đúng/sai lặp lại.

### Gửi request trực tiếp từ PowerShell

```powershell
curl.exe -G --data-urlencode "id=-1 UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='union-id'" http://127.0.0.1:5000/lab/1
curl.exe -G --data-urlencode "mode=fixed" --data-urlencode "id=-1 UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='union-id'" http://127.0.0.1:5000/lab/1
curl.exe --data-urlencode "q=Sổ" http://127.0.0.1:5000/lab/2
curl.exe -X POST -A "LabBrowser" http://127.0.0.1:5000/lab/9
curl.exe -b "lab_visitor=MK-01" http://127.0.0.1:5000/lab/10
```

Ví dụ cho bài 12 dùng cùng cookie phiên trong hai request:

```powershell
$jar = Join-Path $env:TEMP 'sqli-lab12-cookies.txt'
curl.exe -c $jar --data-urlencode "filter=NONE' UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='saved'-- " http://127.0.0.1:5000/lab/12/save
curl.exe -b $jar -X POST http://127.0.0.1:5000/lab/12
```

Để đối chiếu bản sửa của bài 12, thêm `?mode=fixed` vào **cả hai** URL và lưu lại bộ lọc. Bài 11/12 dùng vùng dữ liệu riêng theo cookie phiên và chế độ. Khi khởi động lại app, mặc định khóa phiên được tạo lại. Có thể đặt `LAB_SESSION_KEY` cố định trong môi trường nếu muốn giữ phiên giữa các lần chạy.

## Cách ly môi trường lab

Server mặc định chỉ lắng nghe trên `127.0.0.1` và tắt debugger. Mỗi request SQL mở một kết nối riêng, hạ quyền bằng `EXECUTE AS USER = 'lab_student' WITH NO REVERT` trước khi dữ liệu người học đi vào truy vấn. Principal này được cấp quyền trên các bảng bài tập. Row-level security giới hạn hồ sơ và bộ lọc theo phiên. Chạy bộ lab với dữ liệu giả trên instance dành cho thực hành.

## Kiểm thử và chẩn đoán

Sau khi `init`, chạy bộ kiểm thử tích hợp từ thư mục lab. Bộ kiểm thử gọi route Flask và thực thi truy vấn trên SQL Server thật, kể cả hai phép đo trễ hai giây. Các lượt thử ghi dữ liệu mẫu như thao tác từ trình duyệt.

```powershell
python -m unittest -v test_labs
```

| Triệu chứng | Cách kiểm tra |
| --- | --- |
| Không tìm thấy ODBC Driver | Chạy `python -c "import pyodbc; print(pyodbc.drivers())"` và kiểm tra tên driver. |
| Login timeout / không kết nối được localhost | Kiểm tra dịch vụ **SQL Server (MSSQLSERVER)** hoặc instance có tên của bạn. Với Windows Authentication có thể thử `sqlcmd -S localhost -E -C -l 5 -Q "SELECT @@VERSION"`. |
| Không có database hoặc chưa mở được phiên lab | Chạy `python app.py init` bằng tài khoản có quyền khởi tạo. Kiểm tra instance ở cả terminal chạy init và terminal chạy Flask. |
| HTTP 400 / 405 | Kiểm tra đúng tên tham số, vị trí URL/form/header/cookie và đúng phương thức của bài. |
| Bài 12 trả HTTP 409 | Lưu bộ lọc ở bước 1, rồi chạy bước 2 trong cùng phiên và cùng chế độ. |

## Cấu trúc

- `app.py` — route Flask, cách xử lý phản hồi, runner và CLI.
- `lessons.py` — mục tiêu, payload, câu SQL dễ lỗi và câu SQL tham số hóa của từng bài.
- `database.py`, `sql/` — kết nối ODBC, khởi tạo, quyền, schema và dữ liệu mẫu.
- `templates/`, `static/` — giao diện, workbench gửi request và đo thời gian.
- `test_labs.py` — kiểm thử tích hợp.
