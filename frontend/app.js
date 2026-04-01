// COPILOT: Convert frontend into structured real-time app

// REQUIREMENTS:
// 1. Move all inline JS from HTML into this file
// 2. Add modular functions:
//    - connectSocket()
//    - renderQueue()
//    - renderAgents()
//    - handleEvents()
// 3. Add reconnect logic if socket drops
// 4. Improve UI state handling (loading, empty queue)
// 5. Keep vanilla JS only (no frameworks)
// 6. Must stay compatible with backend socket events

// END GOAL:
// Stable real-time dashboard ready for production use

(function () {
  "use strict";

  // ─── Config ──────────────────────────────────────────────────────────────
  const BACKEND = window.location.origin || "http://localhost:3000";

  // ─── DOM Refs ────────────────────────────────────────────────────────────
  const dom = {
    connStatus:      document.getElementById("connStatus"),
    queueList:       document.getElementById("queueList"),
    activeList:      document.getElementById("activeList"),
    agentList:       document.getElementById("agentList"),
    queueCount:      document.getElementById("queueCount"),
    activeCount:     document.getElementById("activeCount"),
    agentCount:      document.getElementById("agentCount"),
    btnStartCall:    document.getElementById("btnStartCall"),
    btnRegisterAgent: document.getElementById("btnRegisterAgent"),
    toasts:          document.getElementById("toasts"),
  };

  // ─── State ───────────────────────────────────────────────────────────────
  let myAgent = null;
  let socket = null;

  // ─── Socket Connection with Reconnect ────────────────────────────────────
  function connectSocket() {
    socket = io(BACKEND, {
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    });

    socket.on("connect", () => {
      setConnectionStatus(true);
      showToast("Connected to backend", "success");
      fetchQueue();
    });

    socket.on("disconnect", (reason) => {
      setConnectionStatus(false);
      showToast(`Disconnected: ${reason}`, "error");
    });

    socket.on("reconnect_attempt", (attempt) => {
      dom.connStatus.textContent = `Reconnecting (${attempt})...`;
    });

    socket.on("reconnect", () => {
      setConnectionStatus(true);
      showToast("Reconnected!", "success");
      fetchQueue();

      // Re-register agent if we had one
      if (myAgent) {
        socket.emit("agent:register", { name: myAgent.name });
      }
    });

    handleEvents();
  }

  // ─── Event Handlers ─────────────────────────────────────────────────────
  function handleEvents() {
    socket.on("queue:update", (data) => {
      renderQueue(data.queue);
      renderActive(data.activeCalls);
      renderAgents(data.agents);
    });

    socket.on("call:assigned", (call) => {
      showToast(`Call assigned: ${call.callerName} \u2192 ${call.agentName}`, "success");
    });

    socket.on("call:ended", (call) => {
      showToast(`Call ended: ${call.callerName}`, "info");
    });

    socket.on("agent:registered", (agent) => {
      myAgent = agent;
      dom.btnRegisterAgent.textContent = `\u2705 ${agent.name} (Available)`;
      dom.btnRegisterAgent.disabled = true;
      showToast(`Registered as ${agent.name}`, "success");
    });
  }

  // ─── Connection Status UI ───────────────────────────────────────────────
  function setConnectionStatus(connected) {
    if (connected) {
      dom.connStatus.textContent = "Connected";
      dom.connStatus.classList.remove("disconnected");
    } else {
      dom.connStatus.textContent = "Disconnected";
      dom.connStatus.classList.add("disconnected");
    }
  }

  // ─── Fetch Initial State ────────────────────────────────────────────────
  async function fetchQueue() {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND}/api/queue`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderQueue(data.queue);
      renderActive(data.activeCalls);
      renderAgents(data.agents);
    } catch (err) {
      console.error("Failed to fetch queue:", err);
      showToast("Failed to load queue data", "error");
    } finally {
      setLoading(false);
    }
  }

  function setLoading(isLoading) {
    if (isLoading) {
      dom.queueList.innerHTML = '<div class="empty">Loading...</div>';
      dom.activeList.innerHTML = '<div class="empty">Loading...</div>';
      dom.agentList.innerHTML = '<div class="empty">Loading...</div>';
    }
  }

  // ─── Render Functions ───────────────────────────────────────────────────
  function renderQueue(queue) {
    dom.queueCount.textContent = queue.length;
    if (queue.length === 0) {
      dom.queueList.innerHTML = '<div class="empty">No calls in queue</div>';
      return;
    }
    dom.queueList.innerHTML = queue.map((c) => `
      <div class="card">
        <div class="card-info">
          <h3>${esc(c.callerName)}</h3>
          <p>${esc(c.callerNumber)} &middot; ${timeAgo(c.createdAt)}</p>
        </div>
        <span class="tag tag-queued">Queued</span>
      </div>
    `).join("");
  }

  function renderActive(calls) {
    dom.activeCount.textContent = calls.length;
    if (calls.length === 0) {
      dom.activeList.innerHTML = '<div class="empty">No active calls</div>';
      return;
    }
    dom.activeList.innerHTML = calls.map((c) => `
      <div class="card">
        <div class="card-info">
          <h3>${esc(c.callerName)} &rarr; ${esc(c.agentName)}</h3>
          <p>${esc(c.callerNumber)} &middot; ${timeAgo(c.startedAt)}</p>
        </div>
        <button class="btn-end-small" data-call-id="${esc(c.id)}">End</button>
      </div>
    `).join("");

    // Attach end-call handlers via delegation
    dom.activeList.querySelectorAll(".btn-end-small").forEach((btn) => {
      btn.addEventListener("click", () => endCall(btn.dataset.callId));
    });
  }

  function renderAgents(agentArr) {
    dom.agentCount.textContent = agentArr.length;
    if (agentArr.length === 0) {
      dom.agentList.innerHTML = '<div class="empty">No agents connected</div>';
      return;
    }
    dom.agentList.innerHTML = agentArr.map((a) => `
      <div class="card">
        <div class="card-info">
          <h3>${esc(a.name)}</h3>
          <p>Since ${timeAgo(a.connectedAt)}</p>
        </div>
        <span class="tag ${a.status === "available" ? "tag-available" : "tag-busy"}">
          ${a.status}
        </span>
      </div>
    `).join("");
  }

  // ─── Actions ─────────────────────────────────────────────────────────────
  async function startCall() {
    const names = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank"];
    const name = names[Math.floor(Math.random() * names.length)];
    const number = `+1-555-${String(Math.floor(Math.random() * 9000) + 1000)}`;

    try {
      const res = await fetch(`${BACKEND}/api/call/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callerName: name, callerNumber: number }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast(`Call started: ${name}`, "info");
    } catch (err) {
      showToast("Failed to start call", "error");
    }
  }

  function registerAgent() {
    const agentNames = ["Agent Smith", "Agent Jones", "Agent Brown", "Agent Taylor"];
    const name = agentNames[Math.floor(Math.random() * agentNames.length)];
    socket.emit("agent:register", { name });
  }

  async function endCall(callId) {
    try {
      const res = await fetch(`${BACKEND}/api/call/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      showToast("Failed to end call", "error");
    }
  }

  // ─── Utilities ───────────────────────────────────────────────────────────
  function esc(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function timeAgo(iso) {
    if (!iso) return "";
    const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 5) return "just now";
    if (seconds < 60) return `${seconds}s ago`;
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ago`;
  }

  function showToast(message, type) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    dom.toasts.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  // ─── Bind UI Events ─────────────────────────────────────────────────────
  dom.btnStartCall.addEventListener("click", startCall);
  dom.btnRegisterAgent.addEventListener("click", registerAgent);

  // ─── Boot ────────────────────────────────────────────────────────────────
  connectSocket();

})();
