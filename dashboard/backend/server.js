// CallGiant — Server boot file
// Starts HTTP + WebSocket server, wires up app and socket handlers

require("dotenv").config();

const http = require("http");
const { Server } = require("socket.io");

const createApp = require("./app");
const queueService = require("./services/queueService");
const agentService = require("./services/agentService");

// ─── Load persisted queue data ──────────────────────────────────────────────

queueService.load();

// ─── Create HTTP + Socket.IO server ────────────────────────────────────────

const io = new Server({ cors: { origin: "*", methods: ["GET", "POST"] } });
const app = createApp(io);
const server = http.createServer(app);
io.attach(server);

// Grab broadcast/assign helpers from the call router
const { _broadcastQueueUpdate: broadcastQueueUpdate, _tryAssignCall: tryAssignCall } =
  app._callRouter;

// ─── WebSocket Events ───────────────────────────────────────────────────────

io.on("connection", (socket) => {
  console.log(`Socket connected: ${socket.id}`);

  // Agent registers themselves
  socket.on("agent:register", (data) => {
    const agentName = data && data.name ? data.name : "Agent";
    const agent = agentService.register(socket.id, agentName);
    console.log(`Agent registered: ${agent.name} (${agent.id})`);

    socket.emit("agent:registered", agent);
    broadcastQueueUpdate();
    tryAssignCall();
  });

  // Agent disconnects
  socket.on("disconnect", () => {
    const agent = agentService.get(socket.id);
    if (agent) {
      console.log(`Agent disconnected: ${agent.name} (${agent.id})`);

      // If agent had an active call, move it back to queue
      const activeCalls = queueService.getActiveCalls();
      const activeIndex = activeCalls.findIndex((c) => c.agentId === agent.id);
      if (activeIndex !== -1) {
        const orphanedCall = queueService.removeActiveCall(activeCalls[activeIndex].id);
        if (orphanedCall) {
          queueService.requeueCall(orphanedCall);
        }
      }

      agentService.remove(socket.id);
      broadcastQueueUpdate();
    }
  });
});

// ─── Start Server ───────────────────────────────────────────────────────────

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
