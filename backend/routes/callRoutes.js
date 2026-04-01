// Call routes for CallGiant
// Handles REST API endpoints for call management

const express = require("express");
const router = express.Router();

const queueService = require("../services/queueService");
const agentService = require("../services/agentService");

// ─── Validation helpers ─────────────────────────────────────────────────────

function validateStartCall(req, res, next) {
  const { callerName, callerNumber } = req.body;
  if (!callerName || typeof callerName !== "string" || !callerName.trim()) {
    return res.status(400).json({ error: "callerName is required and must be a non-empty string" });
  }
  if (!callerNumber || typeof callerNumber !== "string" || !callerNumber.trim()) {
    return res.status(400).json({ error: "callerNumber is required and must be a non-empty string" });
  }
  next();
}

function validateEndCall(req, res, next) {
  const { callId } = req.body;
  if (!callId || typeof callId !== "string" || !callId.trim()) {
    return res.status(400).json({ error: "callId is required and must be a non-empty string" });
  }
  next();
}

// ─── Route factory (needs io for broadcasting) ─────────────────────────────

function createRoutes(io) {

  function broadcastQueueUpdate() {
    const snapshot = queueService.getSnapshot();
    io.emit("queue:update", {
      queue: snapshot.queue,
      activeCalls: snapshot.activeCalls,
      agents: agentService.getAll(),
    });
  }

  function tryAssignCall() {
    const queue = queueService.getQueue();
    if (queue.length === 0) return;

    const entry = agentService.findAvailable();
    if (!entry) return;

    const call = queueService.dequeue();
    if (!call) return;

    const { socketId, agent } = entry;
    agent.status = "busy";

    const activeCall = {
      id: call.id,
      callerName: call.callerName,
      callerNumber: call.callerNumber,
      agentId: agent.id,
      agentName: agent.name,
      startedAt: new Date().toISOString(),
    };

    queueService.addActiveCall(activeCall);
    io.to(socketId).emit("call:assigned", activeCall);
    broadcastQueueUpdate();
  }

  // POST /api/call/start
  router.post("/call/start", validateStartCall, (req, res) => {
    const { callerName, callerNumber } = req.body;
    const call = queueService.addToQueue(callerName.trim(), callerNumber.trim());
    broadcastQueueUpdate();
    tryAssignCall();
    return res.status(201).json({ message: "Call queued", call });
  });

  // POST /api/call/end
  router.post("/call/end", validateEndCall, (req, res) => {
    const { callId } = req.body;
    const endedCall = queueService.removeActiveCall(callId.trim());

    if (!endedCall) {
      return res.status(404).json({ error: "Active call not found" });
    }

    agentService.setStatus(endedCall.agentId, "available");
    io.emit("call:ended", endedCall);
    broadcastQueueUpdate();
    tryAssignCall();
    return res.json({ message: "Call ended", call: endedCall });
  });

  // GET /api/queue
  router.get("/queue", (req, res) => {
    const snapshot = queueService.getSnapshot();
    return res.json({
      queue: snapshot.queue,
      activeCalls: snapshot.activeCalls,
      agents: agentService.getAll(),
    });
  });

  // Expose helpers for socket handler
  router._broadcastQueueUpdate = broadcastQueueUpdate;
  router._tryAssignCall = tryAssignCall;

  return router;
}

module.exports = createRoutes;
