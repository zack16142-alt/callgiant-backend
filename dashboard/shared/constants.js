// Shared constants and configuration for CallGiant
// Used by both backend and frontend (where applicable)

module.exports = {
  EVENTS: {
    QUEUE_UPDATE: "queue:update",
    CALL_ASSIGNED: "call:assigned",
    CALL_ENDED: "call:ended",
    AGENT_REGISTER: "agent:register",
    AGENT_REGISTERED: "agent:registered",
  },
  AGENT_STATUS: {
    AVAILABLE: "available",
    BUSY: "busy",
  },
  CALL_STATUS: {
    QUEUED: "queued",
    ACTIVE: "active",
    ENDED: "ended",
  },
};
