// COPILOT: Add persistent queue system upgrade

// REQUIREMENTS:
// 1. Replace in-memory queue with file-based persistence (JSON file)
// 2. Save queue state to /data/queue.json
// 3. Load queue on server start
// 4. Ensure no data loss on restart
// 5. Keep API compatibility unchanged
// 6. Handle file read/write safely (no corruption)

// END GOAL:
// Queue survives server restarts without database yet

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DATA_DIR = path.join(__dirname, "..", "..", "data");
const QUEUE_FILE = path.join(DATA_DIR, "queue.json");
const ACTIVE_FILE = path.join(DATA_DIR, "active.json");

// ─── Ensure data directory exists ───────────────────────────────────────────

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

// ─── Safe file I/O (atomic write to prevent corruption) ────────────────────

function readJSON(filePath, fallback) {
  try {
    if (!fs.existsSync(filePath)) return fallback;
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch (err) {
    console.error(`Failed to read ${filePath}:`, err.message);
    return fallback;
  }
}

function writeJSON(filePath, data) {
  try {
    ensureDataDir();
    const tmp = filePath + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2), "utf-8");
    fs.renameSync(tmp, filePath);
  } catch (err) {
    console.error(`Failed to write ${filePath}:`, err.message);
  }
}

// ─── Queue State ────────────────────────────────────────────────────────────

let callQueue = [];
let activeCalls = [];

function load() {
  ensureDataDir();
  callQueue = readJSON(QUEUE_FILE, []);
  activeCalls = readJSON(ACTIVE_FILE, []);
  console.log(`Queue loaded: ${callQueue.length} queued, ${activeCalls.length} active`);
}

function persist() {
  writeJSON(QUEUE_FILE, callQueue);
  writeJSON(ACTIVE_FILE, activeCalls);
}

// ─── Public API ─────────────────────────────────────────────────────────────

function generateId() {
  return crypto.randomUUID();
}

function addToQueue(callerName, callerNumber) {
  const call = {
    id: generateId(),
    callerName,
    callerNumber,
    status: "queued",
    createdAt: new Date().toISOString(),
  };
  callQueue.push(call);
  persist();
  return call;
}

function getQueue() {
  return callQueue;
}

function getActiveCalls() {
  return activeCalls;
}

function dequeue() {
  if (callQueue.length === 0) return null;
  const call = callQueue.shift();
  persist();
  return call;
}

function addActiveCall(activeCall) {
  activeCalls.push(activeCall);
  persist();
}

function removeActiveCall(callId) {
  const idx = activeCalls.findIndex((c) => c.id === callId);
  if (idx === -1) return null;
  const removed = activeCalls.splice(idx, 1)[0];
  persist();
  return removed;
}

function requeueCall(call) {
  callQueue.unshift({
    id: call.id,
    callerName: call.callerName,
    callerNumber: call.callerNumber,
    status: "queued",
    createdAt: call.startedAt || call.createdAt,
  });
  persist();
}

function getSnapshot() {
  return {
    queue: [...callQueue],
    activeCalls: [...activeCalls],
  };
}

module.exports = {
  load,
  persist,
  generateId,
  addToQueue,
  getQueue,
  getActiveCalls,
  dequeue,
  addActiveCall,
  removeActiveCall,
  requeueCall,
  getSnapshot,
};
