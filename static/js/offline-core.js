(function () {
  "use strict";
  const userId = document.body.dataset.offlineUser || "";
  const role = document.body.dataset.offlineRole || "";
  const isAttendance = location.pathname === "/teacher/attendance/";
  const pendingKey = `school-offline-attendance:${userId}`;
  let preparing = false;

  function status(message, warning) {
    let bar = document.getElementById("offline-status-bar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "offline-status-bar";
      bar.setAttribute("role", "status");
      bar.style.cssText = "position:fixed;left:12px;bottom:12px;z-index:2000;padding:8px 13px;border-radius:10px;font:600 13px Tahoma,Arial,sans-serif;box-shadow:0 3px 14px rgba(0,0,0,.18)";
      document.body.appendChild(bar);
    }
    bar.textContent = message;
    bar.style.background = warning ? "#fef3c7" : "#dcfce7";
    bar.style.color = warning ? "#92400e" : "#166534";
    bar.style.display = "block";
    if (!warning) setTimeout(() => { if (navigator.onLine) bar.style.display = "none"; }, 3500);
  }

  function protectOfflineEdits() {
    if (navigator.onLine) return;
    document.querySelectorAll("form").forEach(form => {
      if (isAttendance && role === "teacher" && (form.dataset.offlineAttendance === "1" || form.method.toLowerCase() === "get")) return;
      form.querySelectorAll("button[type=submit], input[type=submit]").forEach(el => {
        el.disabled = true;
        el.title = "هذا التعديل يحتاج اتصالاً بالإنترنت";
      });
    });
  }

  // Enforce offline read-only behavior at submission time, including Enter-key
  // submissions and dynamically inserted forms. Only attendance is locally queued.
  document.addEventListener("submit", event => {
    if (navigator.onLine) return;
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if ((form.getAttribute("method") || "get").toLowerCase() === "get") return;
    if (isAttendance && role === "teacher" && form.dataset.offlineAttendance === "1") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    status("لا يمكن حفظ التعديلات دون إنترنت؛ يُسمح فقط بحضور المعلم", true);
  }, true);

  function waitForWorkerResult(worker, urls) {
    return new Promise((resolve, reject) => {
      const channel = new MessageChannel();
      const timer = setTimeout(() => { channel.port1.close(); reject(new Error("Offline preparation timed out")); }, 90000);
      channel.port1.onmessage = event => {
        if (event.data?.type !== "PREPARE_DONE") return;
        clearTimeout(timer);
        channel.port1.close();
        resolve(event.data);
      };
      worker.postMessage({type: "PREPARE_PAGES", userId, urls}, [channel.port2]);
    });
  }

  async function prepareOffline(registration) {
    if (preparing || !navigator.onLine) return;
    preparing = true;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 12000);
      let response;
      try {
        response = await fetch("/offline-manifest/", {credentials: "same-origin", cache: "no-store", signal: controller.signal});
      } finally { clearTimeout(timer); }
      if (!response.ok) throw new Error(`Manifest HTTP ${response.status}`);
      const data = await response.json();
      const worker = navigator.serviceWorker.controller || registration.active;
      if (!worker) throw new Error("Service worker unavailable");
      const result = await waitForWorkerResult(worker, data.urls || []);
      if (result.failed) console.warn("Offline pages not prepared:", result.failedUrls);
      if (result.saved) status(`تم تجهيز ${result.saved} صفحة للعمل دون إنترنت${result.failed ? ` (${result.failed} غير متاحة)` : ""}`, Boolean(result.failed));
      else status("تعذر تجهيز الصفحات تلقائيًا؛ تحقق من وحدة التحكم", true);
    } catch (error) {
      console.warn("Automatic offline preparation failed:", error);
      status("تعذر تجهيز بعض الصفحات للعمل دون إنترنت", true);
    } finally { preparing = false; }
  }

  async function registerWorker() {
    if (!("serviceWorker" in navigator) || !userId) return;
    try {
      const registration = await navigator.serviceWorker.register("/service-worker.js", {scope: "/"});
      const worker = navigator.serviceWorker.controller || registration.active || registration.waiting || registration.installing;
      if (worker && worker.state !== "activated") await new Promise(resolve => {
        const timer = setTimeout(resolve, 8000);
        worker.addEventListener("statechange", () => { if (worker.state === "activated") { clearTimeout(timer); resolve(); } });
      });
      const active = navigator.serviceWorker.controller || registration.active;
      if (!active) return;
      const channel = new MessageChannel();
      const acknowledged = new Promise(resolve => {
        const timer = setTimeout(resolve, 5000);
        channel.port1.onmessage = () => { clearTimeout(timer); channel.port1.close(); resolve(); };
      });
      active.postMessage({type: "SET_USER", userId}, [channel.port2]);
      await acknowledged;
      // Prepare quietly after authentication. Each failed URL is skipped independently.
      if (navigator.onLine) prepareOffline(registration);
    } catch (error) { console.warn("Offline worker unavailable:", error); }
  }

  window.schoolOffline = {
    userId, role, pendingKey,
    getPending() { try { return JSON.parse(localStorage.getItem(pendingKey) || "[]"); } catch (_) { return []; } },
    setPending(items) { localStorage.setItem(pendingKey, JSON.stringify(items)); },
  };

  window.addEventListener("online", () => {
    status("متصل بالإنترنت", false);
    document.dispatchEvent(new Event("school-online"));
    navigator.serviceWorker?.ready.then(prepareOffline).catch(() => {});
  });
  window.addEventListener("offline", () => { status("غير متصل — البيانات المعروضة هي آخر نسخة محفوظة", true); protectOfflineEdits(); });
  document.addEventListener("DOMContentLoaded", () => {
    if (!userId) return;
    protectOfflineEdits();
    if (!navigator.onLine) status("غير متصل — البيانات المعروضة هي آخر نسخة محفوظة", true);
    registerWorker();
    // Explicit logout clears offline pages. Keep unsynced attendance pending until user chooses to clear it.
    document.querySelectorAll('form[action*="logout"]').forEach(form => form.addEventListener("submit", () => {
      navigator.serviceWorker?.controller?.postMessage({type: "CLEAR_USER", userId});
    }));
  });
})();
