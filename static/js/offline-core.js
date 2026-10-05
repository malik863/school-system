(function () {
  "use strict";

  const userId = document.body.dataset.offlineUser || "";
  const role = document.body.dataset.offlineRole || "";
  const isAttendance = location.pathname === "/teacher/attendance/";
  const pendingKey = `school-offline-attendance:${userId}`;

  function announce(online) {
    let bar = document.getElementById("offline-status-bar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "offline-status-bar";
      bar.style.cssText = "position:fixed;left:12px;bottom:12px;z-index:2000;padding:8px 13px;border-radius:10px;font:600 13px Tahoma,Arial,sans-serif;box-shadow:0 3px 14px rgba(0,0,0,.18)";
      document.body.appendChild(bar);
    }
    bar.textContent = online ? "متصل بالإنترنت" : "غير متصل — البيانات المعروضة هي آخر نسخة محفوظة";
    bar.style.background = online ? "#dcfce7" : "#fef3c7";
    bar.style.color = online ? "#166534" : "#92400e";
    if (online) setTimeout(() => { if (navigator.onLine && bar) bar.style.display = "none"; }, 2500);
    else bar.style.display = "block";
  }

  function protectOfflineEdits() {
    if (navigator.onLine) return;
    document.querySelectorAll("form").forEach(form => {
      if (isAttendance && role === "teacher" && form.dataset.offlineAttendance === "1") return;
      form.querySelectorAll("button[type=submit], input[type=submit]").forEach(el => {
        el.disabled = true;
        el.title = "هذا التعديل يحتاج اتصالاً بالإنترنت";
      });
    });
  }

  async function registerWorker() {
    if (!("serviceWorker" in navigator) || !userId) return;
    try {
      const registration = await navigator.serviceWorker.register("/service-worker.js", {scope: "/"});
      const sendIdentity = () => {
        const worker = navigator.serviceWorker.controller || registration.active || registration.waiting;
        if (worker) worker.postMessage({type: "SET_USER", userId});
      };
      sendIdentity();
      navigator.serviceWorker.addEventListener("controllerchange", sendIdentity);
    } catch (err) {
      console.warn("Offline worker unavailable", err);
    }
  }

  window.schoolOffline = {
    userId,
    role,
    pendingKey,
    getPending() {
      try { return JSON.parse(localStorage.getItem(pendingKey) || "[]"); }
      catch (_) { return []; }
    },
    setPending(items) { localStorage.setItem(pendingKey, JSON.stringify(items)); },
  };

  window.addEventListener("online", () => { announce(true); document.dispatchEvent(new Event("school-online")); });
  window.addEventListener("offline", () => { announce(false); protectOfflineEdits(); });
  document.addEventListener("DOMContentLoaded", () => { announce(navigator.onLine); protectOfflineEdits(); registerWorker(); });
})();
