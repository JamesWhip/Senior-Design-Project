// server.js — Socket.IO server for smart chessboard

const express = require("express");
const http = require("http");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);

// Allow connections from anywhere on your LAN
const io = new Server(server, {
  cors: {
    origin: "*",
  },
});

const PORT = 3000; // make sure this matches SOCKETIO_SERVER_URL port on the Pi

// Simple homepage so you can see something in a browser
app.get("/", (req, res) => {
  res.send("Chessboard Socket.IO server is running.");
});

// HTTP endpoint to trigger a move, e.g.
//   http://SERVER_IP:3000/move?start=E2&end=E4
app.get("/move", (req, res) => {
  let { start, end } = req.query;
  if (!start || !end) {
    return res
      .status(400)
      .send('Usage: /move?start=E2&end=E4');
  }

  start = String(start).toUpperCase().trim();
  end   = String(end).toUpperCase().trim();

  console.log(`[HTTP] Request to move: ${start} -> ${end}`);

  // Broadcast to all connected Pis
  io.emit("move_piece", { start, end });

  res.send(`Emitted move_piece: ${start} -> ${end}`);
});

// Socket.IO events
io.on("connection", (socket) => {
  console.log("[IO] Client connected:", socket.id);

  // Pi will send this when done with a move
  socket.on("move_piece_done", (data) => {
    console.log("[IO] move_piece_done from Pi:", data);
  });

  socket.on("disconnect", (reason) => {
    console.log("[IO] Client disconnected:", socket.id, "reason:", reason);
  });
});

// Start the server
server.listen(PORT, () => {
  console.log(`Chessboard server listening on port ${PORT}`);
  console.log(`Visit http://localhost:${PORT}/ in a browser to check.`);
});

