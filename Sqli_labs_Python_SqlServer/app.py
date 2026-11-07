"""Local Flask application for the SQL Server injection labs."""

import argparse
import os
import secrets
import sys
import uuid
from urllib.parse import unquote

import pyodbc
from flask import Flask, Response, abort, render_template, request, session
from werkzeug.exceptions import MethodNotAllowed

import database
from lessons import BY_NUMBER, GROUPS, LESSONS

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("LAB_SESSION_KEY") or secrets.token_bytes(32),
    SESSION_COOKIE_NAME="sqli_lab_session",
    SESSION_COOKIE_SAMESITE="Strict",
    TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    MAX_CONTENT_LENGTH=16_384,
)

SOURCES = {"url": "URL", "form": "Form", "header": "Header", "cookie": "Cookie",
           "stored": "Form → CSDL"}


def plain(body, status=200):
    return Response(body, status=status, content_type="text/plain; charset=utf-8")


@app.before_request
def local_requests():
    if request.path.startswith("/lab/") and request.headers.get("Sec-Fetch-Site") == "cross-site":
        abort(403)


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.path.startswith("/lab/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def get_lesson(number):
    lesson = BY_NUMBER.get(number)
    if not lesson:
        abort(404)
    return lesson


def get_mode():
    mode = request.args.get("mode", "vuln")
    if mode not in ("vuln", "fixed"):
        abort(400, "Chế độ phải là vuln hoặc fixed.")
    return mode


def browser_scope(mode):
    if "learner" not in session:
        session["learner"] = uuid.uuid4().hex
    return session["learner"] + mode[0]


@app.get("/")
def index():
    return render_template("index.html", lessons=LESSONS, groups=GROUPS, sources=SOURCES)


@app.get("/guide")
def guide():
    return render_template("guide.html")


@app.get("/lessons/<int:number>")
def notebook(number):
    lesson = get_lesson(number)
    mode = get_mode()
    browser_scope(mode)
    return render_template("lesson.html", lesson=lesson, lessons=LESSONS, groups=GROUPS,
                           sources=SOURCES, mode=mode)


def read_input(lesson):
    if lesson.source == "url":
        value = request.args.get(lesson.key)
    elif lesson.source == "header":
        value = request.headers.get(lesson.key, request.headers.get("User-Agent"))
    elif lesson.source == "cookie":
        raw = request.cookies.get(lesson.key)
        value = unquote(raw) if raw is not None else None
    else:
        value = request.form.get(lesson.key)
    if value is None:
        abort(400, f"Thiếu đầu vào {lesson.key}.")
    if len(value.encode("utf-16-le")) > 1200:
        abort(400, "Đầu vào vượt quá 600 đơn vị UTF-16.")
    return value


def render_rows(rows):
    if not rows:
        return "Không tìm thấy sản phẩm."
    return "id  |  title\n" + "\n".join(f"{row[0]}  |  {row[1]}" for row in rows)


def run_sql(lesson, value, mode, scope):
    with database.training_connection(scope) as db:
        cur = db.cursor()
        if lesson.result == "stored":
            # The second request gets its input from SQL Server, never from a form.
            row = cur.execute("SELECT term FROM dbo.saved_filters WHERE scope=?", scope).fetchone()
            if row is None:
                return plain("Chưa có bộ lọc. Hãy lưu ở bước 1 trong chế độ này.", 409)
            value = row.term
        if lesson.result == "update":
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.profiles WITH (UPDLOCK,HOLDLOCK) WHERE scope=?) "
                "INSERT dbo.profiles(scope, display_name, badge) VALUES (?, N'Minh', N'Member')",
                scope, scope,
            )
        # The contrast between these two calls is the subject of every lesson.
        if mode == "fixed":
            cur.execute(lesson.fixed_sql, value)
        else:
            cur.execute(lesson.vulnerable_sql.replace("{input}", value))

        if lesson.result == "time":
            # A delay can be in the next statement of the batch. Wait for it.
            while cur.nextset():
                pass
            return plain("Đã nhận yêu cầu.")
        if lesson.result == "insert":
            return plain("Đã ghi tên client vào nhật ký.")
        if lesson.result == "update":
            row = cur.execute("SELECT display_name, badge FROM dbo.profiles WHERE scope=?", scope).fetchone()
            return plain(f"display_name = {row.display_name}\nbadge = {row.badge}")
        if lesson.result in ("exists", "invite"):
            return plain(boolean_signal(lesson, cur.fetchone() is not None))
        return plain(render_rows(cur.fetchmany(1 if lesson.result == "first" else 30)))


def boolean_signal(lesson, found):
    if lesson.result == "invite":
        return "Mã mời hợp lệ." if found else "Mã mời không hợp lệ."
    return "Có sản phẩm." if found else "Không có sản phẩm."


@app.route("/lab/<int:number>", methods=["GET", "POST"])
def exercise(number):
    lesson = get_lesson(number)
    method = "GET" if request.method == "HEAD" else request.method
    if method != lesson.method:
        raise MethodNotAllowed(valid_methods=[lesson.method])
    mode = get_mode()
    value = None if lesson.result == "stored" else read_input(lesson)
    try:
        return run_sql(lesson, value, mode, browser_scope(mode))
    except pyodbc.Error as exc:
        state = str(exc.args[0])
        if state.startswith("08"):
            raise database.DatabaseUnavailable("Mất kết nối SQL Server.") from exc
        if state in ("HYT00", "HYT01"):
            return plain("Truy vấn vượt thời gian cho phép.", 408)
        if lesson.result == "time":
            return plain("Đã nhận yêu cầu.")
        if lesson.result in ("exists", "invite"):
            return plain(boolean_signal(lesson, False))
        if mode == "fixed":
            return plain("Giá trị không phù hợp với truy vấn.", 422)
        return plain(f"SQL Server · {state}\n{exc.args[-1]}", 422)


@app.post("/lab/12/save")
def save_filter():
    lesson = get_lesson(12)
    scope = browser_scope(get_mode())
    term = read_input(lesson)
    # Parameterized in BOTH modes. Only the later use differs.
    with database.training_connection(scope) as db:
        db.cursor().execute(
            "UPDATE dbo.saved_filters WITH (UPDLOCK,HOLDLOCK) SET term=? WHERE scope=?; "
            "IF @@ROWCOUNT=0 INSERT dbo.saved_filters (scope,term) VALUES (?,?)",
            term, scope, scope, term,
        )
    return plain("Đã lưu nguyên văn bộ lọc. Bây giờ hãy chạy bước 2.")


@app.errorhandler(database.DatabaseUnavailable)
def unavailable(exc):
    return plain(f"{exc} Kiểm tra SQL Server và chạy python app.py init trong thư mục lab.", 503)


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
def request_error(exc):
    response = plain(str(exc.description), exc.code)
    if isinstance(exc, MethodNotAllowed) and exc.valid_methods:
        response.headers["Allow"] = ", ".join(exc.valid_methods)
    return response


def main():
    parser = argparse.ArgumentParser(description="SQLi Labs · Flask / SQL Server")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "init", "reset"])
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    if args.command == "serve":
        print(f"Mở http://127.0.0.1:{args.port}", flush=True)
        app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
    else:
        try:
            database.initialize(reset=args.command == "reset")
        except (pyodbc.Error, KeyError, RuntimeError) as exc:
            parser.exit(1, f"Khởi tạo thất bại: {exc}\n")
        print(f"{database.DATABASE} đã sẵn sàng.")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
