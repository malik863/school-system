(function () {
  "use strict";
  const api = window.schoolOffline;
  const form = document.querySelector('form[data-offline-attendance="1"]');
  if (!api || !form) return;

  const statusBox = document.getElementById("attendance-sync-status");
  const classroom = form.querySelector('[name="classroom"]');
  const date = form.querySelector('[name="date"]');
  const csrf = form.querySelector('[name="csrfmiddlewaretoken"]');

  function setStatus(text, kind) {
    if (!statusBox) return;
    statusBox.textContent = text;
    statusBox.className = `alert mt-3 ${kind || "alert-secondary"}`;
    statusBox.hidden = false;
  }

  function collect() {
    const records = [];
    form.querySelectorAll('select[name^="student_"]').forEach(select => {
      if (!select.value) return;
      records.push({
        student_id: Number(select.name.replace("student_", "")),
        status: select.value,
        baseline: select.dataset.serverStatus || ""
      });
    });
    return {classroom_id: Number(classroom.value), date: date.value, records};
  }

  function queue(payload) {
    let items = api.getPending();
    const key = `${payload.classroom_id}:${payload.date}`;
    items = items.filter(item => `${item.classroom_id}:${item.date}` !== key);
    items.push(payload);
    api.setPending(items);
    setStatus("تم حفظ الحضور على هذا الجهاز — في انتظار المزامنة", "alert-warning");
  }

  async function send(payload) {
    const response = await fetch("/teacher/attendance/offline-sync/", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.value},
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      if (response.status === 409) return {conflict: true, ...(await response.json())};
      throw new Error(`sync ${response.status}`);
    }
    return response.json();
  }

  async function syncPending() {
    if (!navigator.onLine) return;
    let items = api.getPending();
    if (!items.length) return;
    const remaining = [];
    let conflicts = 0;
    for (const item of items) {
      try {
        const result = await send(item);
        if (result.conflict) { remaining.push(item); conflicts += 1; }
      } catch (_) { remaining.push(item); }
    }
    api.setPending(remaining);
    if (conflicts) setStatus("يوجد تعارض في حضور محفوظ دون اتصال. افتح اليوم والفصل أثناء الاتصال لمراجعته قبل إعادة الحفظ.", "alert-danger");
    else if (!remaining.length) {
      setStatus("تمت مزامنة الحضور بنجاح ✓", "alert-success");
      form.querySelectorAll('select[name^="student_"]').forEach(s => { s.dataset.serverStatus = s.value || ""; });
    } else setStatus("تعذر إكمال المزامنة. سيعاد المحاولة عند توفر الاتصال.", "alert-warning");
  }

  form.addEventListener("submit", async event => {
    if (navigator.onLine) return; // normal Django POST remains unchanged online
    event.preventDefault();
    const payload = collect();
    if (!payload.classroom_id || !payload.date || !payload.records.length) {
      setStatus("اختر حالة طالب واحد على الأقل قبل الحفظ.", "alert-warning");
      return;
    }
    queue(payload);
  });

  document.addEventListener("school-online", syncPending);
  document.addEventListener("DOMContentLoaded", syncPending);
  if (api.getPending().length) setStatus("يوجد حضور محفوظ على هذا الجهاز في انتظار المزامنة.", "alert-warning");
})();
