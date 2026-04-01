// Agent management service for CallGiant
// Manages agent registration, status, and socket mapping

const queueService = require("./queueService");

// ─── Agent Store (in-memory, keyed by socket ID) ───────────────────────────

const agents = new Map(); // socketId -> { id, socketId, name, status, connectedAt }

// ─── Public API ─────────────────────────────────────────────────────────────

function register(socketId, name) {
  const agent = {
    id: queueService.generateId(),
    socketId,
    name: name || "Agent",
    status: "available",
    connectedAt: new Date().toISOString(),
  };
  agents.set(socketId, agent);
  return agent;
}

function remove(socketId) {
  const agent = agents.get(socketId);
  if (!agent) return null;
  agents.delete(socketId);
  return agent;
}

function get(socketId) {
  return agents.get(socketId) || null;
}

function findAvailable() {
  for (const [socketId, agent] of agents) {
    if (agent.status === "available") {
      return { socketId, agent };
    }
  }
  return null;
}

function findByAgentId(agentId) {
  for (const [, agent] of agents) {
    if (agent.id === agentId) return agent;
  }
  return null;
}

function setStatus(agentId, status) {
  for (const [, agent] of agents) {
    if (agent.id === agentId) {
      agent.status = status;
      return agent;
    }
  }
  return null;
}

function getAll() {
  return Array.from(agents.values());
}

module.exports = {
  register,
  remove,
  get,
  findAvailable,
  findByAgentId,
  setStatus,
  getAll,
};
