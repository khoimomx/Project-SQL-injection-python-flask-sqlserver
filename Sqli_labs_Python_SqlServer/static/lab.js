"use strict";

const filters = document.querySelectorAll("[data-filter]");
for (const button of filters) {
  button.addEventListener("click", () => {
    for (const tab of filters) tab.setAttribute("aria-pressed", String(tab === button));
    for (const group of document.querySelectorAll("[data-group]")) {
      group.hidden = button.dataset.filter !== "all" && group.dataset.group !== button.dataset.filter;
    }
  });
}

function setupWorkbench(form) {
  const lab = form.dataset;
  const input = form.querySelector("textarea");
  const body = document.querySelector("#response-body");
  const meta = document.querySelector("#response-meta");
  const panel = document.querySelector(".response");
  const timingList = document.querySelector("#timings");
  const measurements = [];
  const storageKey = "sqli.input." + lab.number;

  // Keep the exact input while switching modes, including empty strings.
  try { input.value = sessionStorage.getItem(storageKey) ?? lab.baseline; } catch {}
  function remember() {
    try { sessionStorage.setItem(storageKey, input.value); } catch {}
  }
  function fill(value) {
    input.value = value;
    remember();
    input.focus();
  }
  input.addEventListener("input", remember);
  form.querySelector("[data-restore]").addEventListener("click", () => fill(lab.baseline));
  for (const example of document.querySelectorAll("[data-example]")) {
    example.addEventListener("click", () => fill(example.dataset.example));
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const saving = event.submitter?.value === "save";
    const url = new URL(saving ? lab.save : lab.endpoint, location.origin);
    if (lab.mode === "fixed") url.searchParams.set("mode", "fixed");
    const options = { method: lab.method, credentials: "same-origin", cache: "no-store" };
    const buttons = form.querySelectorAll("button[type=submit]");
    for (const button of buttons) button.disabled = true;
    meta.textContent = "Đang gửi…";
    panel.removeAttribute("data-status");
    body.textContent = "Đang chờ SQL Server…";
    document.querySelector("#request-detail").hidden = true;
    remember();
    try {
      let wire = "";
      if (lab.source === "url") {
        url.searchParams.set(lab.key, input.value);
      } else if (lab.source === "form" || saving) {
        options.body = new URLSearchParams([[lab.key, input.value]]);
        wire = "\nContent-Type: application/x-www-form-urlencoded\n\n" + options.body;
      } else if (lab.source === "header") {
        options.headers = { [lab.key]: input.value };
        wire = "\n" + lab.key + ": " + input.value;
      } else if (lab.source === "cookie") {
        const cookie = lab.key + "=" + encodeURIComponent(input.value);
        document.cookie = cookie + "; Path=" + url.pathname + "; SameSite=Strict";
        wire = "\nCookie: " + cookie;
      }
      document.querySelector("#wire-request").textContent = lab.method + " " + url.pathname + url.search + wire;
      document.querySelector("#request-detail").hidden = false;
      const start = performance.now();
      const response = await fetch(url, options);
      const content = await response.text();
      const elapsed = Math.round(performance.now() - start);
      body.textContent = content;
      meta.textContent = "HTTP " + response.status + " · " + elapsed + " ms";
      panel.dataset.status = response.ok ? "ok" : "error";
      if (lab.timing && response.ok) {
        measurements.push(elapsed + " ms");
        timingList.textContent = "Các lần đo gần nhất: " + measurements.slice(-5).join(" / ");
        timingList.hidden = false;
      }
    } catch (error) {
      meta.textContent = "Lỗi request";
      panel.dataset.status = "error";
      body.textContent = lab.source === "header"
        ? "Kiểm tra kết nối và giá trị header. Dùng một dòng ký tự ASCII khi gửi header từ trình duyệt."
        : "Không gửi được request. Hãy kiểm tra Flask đang chạy trên localhost.";
    } finally {
      for (const button of buttons) button.disabled = false;
    }
  });
}

const workbench = document.querySelector("#workbench");
if (workbench) setupWorkbench(workbench);
