// COPILOT: Refactor CallGiant backend into production architecture

// GOAL:
// Move from single-file server to scalable backend structure.

// REQUIREMENTS:
// 1. Split server into modules:
//    - app.js (express app setup)
//    - server.js (boot server)
//    - routes/callRoutes.js
//    - services/queueService.js
//    - services/agentService.js
// 2. Keep Socket.io integration clean in server.js
// 3. Move all business logic OUT of server file
// 4. Queue system must remain in-memory for now
// 5. Add validation layer for API requests
// 6. Add centralized error handler middleware
// 7. Keep everything working exactly like before (NO breaking changes)
// 8. Use CommonJS consistently

// END GOAL:
// Clean architecture backend ready for database + scaling

const express = require("express");
const path = require("path");

function createApp(io) {
  const app = express();

  // ─── Middleware ──────────────────────────────────────────────────────────
  app.use(express.json());
  app.use(express.static(path.join(__dirname, "..", "frontend")));

  // ─── Request logger (production-light) ──────────────────────────────────
  app.use((req, res, next) => {
    const start = Date.now();
    res.on("finish", () => {
      const ms = Date.now() - start;
      if (req.path.startsWith("/api")) {
        console.log(`${req.method} ${req.path} ${res.statusCode} ${ms}ms`);
      }
    });
    next();
  });

  // ─── Routes ─────────────────────────────────────────────────────────────
  const createCallRoutes = require("./routes/callRoutes");
  const callRouter = createCallRoutes(io);
  app.use("/api", callRouter);

  // ─── Health check ───────────────────────────────────────────────────────
  app.get("/health", (req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  // ─── 404 handler ────────────────────────────────────────────────────────
  app.use((req, res) => {
    res.status(404).json({ error: "Not found" });
  });

  // ─── Centralized error handler ──────────────────────────────────────────
  app.use((err, req, res, _next) => {
    console.error("Unhandled error:", err.stack || err.message);
    res.status(500).json({ error: "Internal server error" });
  });

  // Expose router helpers for socket handler in server.js
  app._callRouter = callRouter;

  return app;
}

module.exports = createApp;
