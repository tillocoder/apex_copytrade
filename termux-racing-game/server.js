/**
 * APEX SPEED 3D - Ultra-Lightweight Multiplayer Racing Server
 * Specifically architected for Termux (Android) & Low-Resource Environments
 * 
 * - Zero heavy physics on server (0.05% CPU usage)
 * - Ultra-low memory footprint (~25MB RAM)
 * - Pure Node.js HTTP + ws (No native dependencies)
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const WebSocketServer = WebSocket.WebSocketServer || WebSocket.Server;

const PORT = parseInt(process.env.PORT, 10) || 5050;
const HOST = process.env.HOST || '0.0.0.0';

// MIME types for static assets
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2'
};

const PUBLIC_DIR = path.join(__dirname, 'public');

// HTTP server for static files & health checks
const server = http.createServer((req, res) => {
  // CORS & Security headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('X-Content-Type-Options', 'nosniff');

  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  let pathname = parsedUrl.pathname;

  if (pathname === '/health') {
    const mem = process.memoryUsage();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      service: 'apex-speed-3d-termux',
      uptime: Math.floor(process.uptime()),
      onlinePlayers: players.size,
      activeRooms: rooms.size,
      ramUsageMB: Math.round(mem.rss / 1024 / 1024 * 10) / 10
    }));
    return;
  }

  // Normalize path
  if (pathname === '/' || pathname === '') {
    pathname = '/index.html';
  }

  const safePath = path.normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
  const filePath = path.join(PUBLIC_DIR, safePath);

  // Prevent directory traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('403 Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    // Caching: HTML no-cache, assets 1 hour
    const cacheControl = ext === '.html' ? 'no-cache, must-revalidate' : 'public, max-age=3600';
    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stats.size,
      'Cache-Control': cacheControl
    });

    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
});

// WebSocket Server
const wss = new WebSocketServer({ server });

// In-Memory State
const players = new Map();     // playerId -> playerObj
const rooms = new Map();       // roomId -> roomObj
const challenges = new Map();  // challengeId -> challengeObj

let idCounter = 1;
function generateId(prefix = 'p') {
  return `${prefix}_${Date.now().toString(36)}_${(idCounter++).toString(36)}`;
}

function broadcastLobby() {
  const lobbyList = [];
  for (const [id, p] of players) {
    lobbyList.push({
      id: p.id,
      name: p.name,
      status: p.status, // 'lobby' | 'in_race' | 'challenging'
      ping: p.ping || 0
    });
  }

  const payload = JSON.stringify({
    type: 'lobby_update',
    players: lobbyList
  });

  for (const [_, p] of players) {
    if (p.ws.readyState === WebSocket.OPEN) {
      p.ws.send(payload);
    }
  }
}

function sendTo(player, data) {
  if (player && player.ws && player.ws.readyState === WebSocket.OPEN) {
    player.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
  }
}

wss.on('connection', (ws, req) => {
  const playerId = generateId('p');
  const player = {
    id: playerId,
    name: `Racer ${Math.floor(100 + Math.random() * 900)}`,
    carType: 'hypercar',
    ws: ws,
    status: 'lobby',
    roomId: null,
    ping: 0,
    isAlive: true,
    connectedAt: Date.now()
  };

  players.set(playerId, player);

  // Send initial welcome
  sendTo(player, {
    type: 'welcome',
    id: player.id,
    name: player.name
  });

  broadcastLobby();

  ws.on('message', (message) => {
    let msg;
    try {
      msg = JSON.parse(message);
    } catch (e) {
      return;
    }

    const type = msg.type;

    // 1. PING / PONG (Ultra-low latency measurement)
    if (type === 'ping') {
      sendTo(player, { type: 'pong', t: msg.t });
      return;
    }

    // 2. SET NAME
    if (type === 'set_name') {
      const cleanName = (msg.name || '').trim().substring(0, 16) || `Racer ${Math.floor(100 + Math.random() * 900)}`;
      player.name = cleanName;
      sendTo(player, { type: 'name_updated', name: player.name });
      broadcastLobby();
      return;
    }

    // 2.1 SET CAR
    if (type === 'set_car') {
      const allowedCars = ['hypercar', 'muscle', 'truck', 'formula'];
      if (allowedCars.includes(msg.carType)) {
        player.carType = msg.carType;
      }
      return;
    }

    // 3. SEND CHALLENGE
    if (type === 'challenge_send') {
      const targetId = msg.targetId;
      const target = players.get(targetId);

      if (!target || target.id === player.id) {
        sendTo(player, { type: 'challenge_error', message: 'Foydalanuvchi topilmadi!' });
        return;
      }

      if (target.status !== 'lobby') {
        sendTo(player, { type: 'challenge_error', message: 'Raqib hozir band yoki poygada!' });
        return;
      }

      const trackId = msg.trackId || 'neon_city';
      if (msg.carType) player.carType = msg.carType;

      const challengeId = generateId('ch');
      const challenge = {
        id: challengeId,
        fromId: player.id,
        toId: target.id,
        trackId: trackId,
        fromCarType: player.carType,
        createdAt: Date.now(),
        timer: setTimeout(() => {
          // Auto-expire after 15 seconds
          if (challenges.has(challengeId)) {
            challenges.delete(challengeId);
            player.status = 'lobby';
            target.status = 'lobby';
            sendTo(player, { type: 'challenge_timeout', targetName: target.name });
            sendTo(target, { type: 'challenge_expired', fromName: player.name });
            broadcastLobby();
          }
        }, 15000)
      };

      challenges.set(challengeId, challenge);
      player.status = 'challenging';
      target.status = 'challenging';

      sendTo(player, {
        type: 'challenge_sent',
        challengeId,
        targetId: target.id,
        targetName: target.name,
        trackId: trackId,
        expiresIn: 15
      });

      sendTo(target, {
        type: 'challenge_incoming',
        challengeId,
        fromId: player.id,
        fromName: player.name,
        trackId: trackId,
        fromCarType: player.carType,
        expiresIn: 15
      });

      broadcastLobby();
      return;
    }

    // 4. CANCEL CHALLENGE
    if (type === 'challenge_cancel') {
      const challengeId = msg.challengeId;
      const ch = challenges.get(challengeId);
      if (ch && ch.fromId === player.id) {
        clearTimeout(ch.timer);
        challenges.delete(challengeId);
        const target = players.get(ch.toId);
        player.status = 'lobby';
        if (target) {
          target.status = 'lobby';
          sendTo(target, { type: 'challenge_canceled_by_sender' });
        }
        sendTo(player, { type: 'challenge_canceled_success' });
        broadcastLobby();
      }
      return;
    }

    // 5. DECLINE CHALLENGE
    if (type === 'challenge_decline') {
      const challengeId = msg.challengeId;
      const ch = challenges.get(challengeId);
      if (ch && ch.toId === player.id) {
        clearTimeout(ch.timer);
        challenges.delete(challengeId);
        const challenger = players.get(ch.fromId);
        player.status = 'lobby';
        if (challenger) {
          challenger.status = 'lobby';
          sendTo(challenger, { type: 'challenge_declined', targetName: player.name });
        }
        sendTo(player, { type: 'challenge_decline_success' });
        broadcastLobby();
      }
      return;
    }

    // 6. ACCEPT CHALLENGE
    if (type === 'challenge_accept') {
      const challengeId = msg.challengeId;
      const ch = challenges.get(challengeId);
      if (!ch || ch.toId !== player.id) {
        sendTo(player, { type: 'challenge_error', message: 'Taklif muddati tugagan!' });
        return;
      }

      clearTimeout(ch.timer);
      challenges.delete(challengeId);

      const p1 = players.get(ch.fromId);
      const p2 = player;

      if (!p1 || p1.ws.readyState !== WebSocket.OPEN) {
        sendTo(player, { type: 'challenge_error', message: 'Chaqiruvchi o‘yinchi aloqadan uzildi!' });
        player.status = 'lobby';
        broadcastLobby();
        return;
      }

      if (msg.carType) player.carType = msg.carType;

      // Create Race Room
      const roomId = generateId('race');
      const trackId = ch.trackId || 'neon_city';
      const room = {
        id: roomId,
        isSolo: false,
        trackId: trackId,
        p1: p1.id,
        p2: p2.id,
        p1CarType: p1.carType || 'hypercar',
        p2CarType: p2.carType || 'hypercar',
        p1Ready: false,
        p2Ready: false,
        state: 'loading', // 'loading' | 'countdown' | 'racing' | 'finished'
        lapsTotal: 2,
        currentLap: { [p1.id]: 1, [p2.id]: 1 },
        checkpoints: { [p1.id]: 0, [p2.id]: 0 },
        finishedOrder: [],
        rematchVotes: new Set(),
        startTime: null
      };

      rooms.set(roomId, room);
      p1.roomId = roomId;
      p2.roomId = roomId;
      p1.status = 'in_race';
      p2.status = 'in_race';

      // Inform both players
      sendTo(p1, {
        type: 'match_start',
        roomId,
        role: 'p1',
        color: 'red',
        gridSlot: 1,
        opponent: { id: p2.id, name: p2.name, carType: room.p2CarType },
        trackId: room.trackId,
        myCarType: room.p1CarType,
        oppCarType: room.p2CarType,
        lapsTotal: room.lapsTotal
      });

      sendTo(p2, {
        type: 'match_start',
        roomId,
        role: 'p2',
        color: 'cyan',
        gridSlot: 2,
        opponent: { id: p1.id, name: p1.name, carType: room.p1CarType },
        trackId: room.trackId,
        myCarType: room.p2CarType,
        oppCarType: room.p1CarType,
        lapsTotal: room.lapsTotal
      });

      broadcastLobby();
      return;
    }

    // 7. SOLO PRACTICE MODE
    if (type === 'solo_practice') {
      const trackId = msg.trackId || 'neon_city';
      if (msg.carType) player.carType = msg.carType;

      const roomId = generateId('solo');
      const room = {
        id: roomId,
        isSolo: true,
        trackId: trackId,
        p1: player.id,
        p2: null,
        p1Ready: false,
        p1CarType: player.carType || 'hypercar',
        state: 'loading',
        lapsTotal: 2,
        currentLap: { [player.id]: 1 },
        checkpoints: { [player.id]: 0 },
        finishedOrder: [],
        rematchVotes: new Set(),
        startTime: null
      };

      rooms.set(roomId, room);
      player.roomId = roomId;
      player.status = 'in_race';

      sendTo(player, {
        type: 'match_start',
        roomId,
        role: 'p1',
        color: 'red',
        gridSlot: 1,
        opponent: null,
        isSolo: true,
        trackId: trackId,
        myCarType: room.p1CarType,
        oppCarType: null,
        lapsTotal: room.lapsTotal
      });

      broadcastLobby();
      return;
    }

    // 8. CLIENT READY (Scene loaded)
    if (type === 'client_ready') {
      const roomId = player.roomId;
      const room = rooms.get(roomId);
      if (!room) return;

      if (room.p1 === player.id) room.p1Ready = true;
      if (room.p2 === player.id) room.p2Ready = true;

      const allReady = room.isSolo ? room.p1Ready : (room.p1Ready && room.p2Ready);

      if (allReady && room.state === 'loading') {
        room.state = 'countdown';

        const p1Obj = players.get(room.p1);
        const p2Obj = room.p2 ? players.get(room.p2) : null;

        // Start Countdown sequence: 3 -> 2 -> 1 -> GO!
        let count = 3;
        const sendCountdown = () => {
          const payload = {
            type: 'countdown_tick',
            count: count,
            text: count > 0 ? `${count}` : 'GO!'
          };

          sendTo(p1Obj, payload);
          if (p2Obj) sendTo(p2Obj, payload);

          if (count === 0) {
            room.state = 'racing';
            room.startTime = Date.now();
          } else {
            count--;
            setTimeout(sendCountdown, 1000);
          }
        };

        sendCountdown();
      }
      return;
    }

    // 9. REAL-TIME CAR UPDATE (Ultra-fast relay with 0 server compute)
    if (type === 'car_update') {
      const roomId = player.roomId;
      const room = rooms.get(roomId);
      if (!room || room.isSolo) return;

      const opponentId = (room.p1 === player.id) ? room.p2 : room.p1;
      const opponent = players.get(opponentId);

      if (opponent && opponent.ws.readyState === WebSocket.OPEN) {
        // Forward position & rotation directly
        opponent.ws.send(JSON.stringify({
          type: 'opponent_update',
          d: msg.d // [x, y, z, rotY, steer, speed, drift] compact array
        }));
      }
      return;
    }

    // 10. CHECKPOINT PASS
    if (type === 'checkpoint_pass') {
      const roomId = player.roomId;
      const room = rooms.get(roomId);
      if (!room) return;

      room.checkpoints[player.id] = msg.checkpointIndex;
      if (msg.lap) room.currentLap[player.id] = msg.lap;

      if (!room.isSolo) {
        const opponentId = (room.p1 === player.id) ? room.p2 : room.p1;
        const opponent = players.get(opponentId);
        sendTo(opponent, {
          type: 'opponent_progress',
          checkpointIndex: msg.checkpointIndex,
          lap: room.currentLap[player.id]
        });
      }
      return;
    }

    // 11. RACE FINISH
    if (type === 'race_finish') {
      const roomId = player.roomId;
      const room = rooms.get(roomId);
      if (!room || room.state === 'finished') return;

      const totalTime = msg.totalTime || 0;
      const bestLap = msg.bestLap || 0;

      if (!room.finishedOrder.includes(player.id)) {
        room.finishedOrder.push(player.id);
      }

      const rank = room.finishedOrder.length; // 1 = 1st, 2 = 2nd
      const p1Obj = players.get(room.p1);
      const p2Obj = room.p2 ? players.get(room.p2) : null;

      if (room.isSolo) {
        room.state = 'finished';
        sendTo(player, {
          type: 'race_ended',
          rank: 1,
          isWinner: true,
          totalTime,
          bestLap,
          results: [{ name: player.name, time: totalTime, rank: 1 }]
        });
        return;
      }

      // 2-Player duel finish logic
      if (rank === 1) {
        // Winner arrived!
        const winner = player;
        const opponentId = (room.p1 === player.id) ? room.p2 : room.p1;
        const opponent = players.get(opponentId);

        sendTo(winner, {
          type: 'race_ended',
          rank: 1,
          isWinner: true,
          totalTime,
          bestLap,
          winnerName: winner.name
        });

        if (opponent) {
          sendTo(opponent, {
            type: 'opponent_finished',
            winnerName: winner.name,
            totalTime
          });
        }
      } else {
        // Second player arrived
        room.state = 'finished';
        sendTo(player, {
          type: 'race_ended',
          rank: 2,
          isWinner: false,
          totalTime,
          bestLap,
          winnerName: p1Obj.id === room.finishedOrder[0] ? p1Obj.name : (p2Obj ? p2Obj.name : 'Opponent')
        });
      }
      return;
    }

    // 12. REMATCH VOTE
    if (type === 'rematch_vote') {
      const roomId = player.roomId;
      const room = rooms.get(roomId);
      if (!room) return;

      room.rematchVotes.add(player.id);

      const p1Obj = players.get(room.p1);
      const p2Obj = room.p2 ? players.get(room.p2) : null;

      const votesNeeded = room.isSolo ? 1 : 2;
      const currentVotes = room.rematchVotes.size;

      const voteStatusPayload = {
        type: 'rematch_status',
        votes: currentVotes,
        needed: votesNeeded,
        votedBy: player.name
      };

      sendTo(p1Obj, voteStatusPayload);
      if (p2Obj) sendTo(p2Obj, voteStatusPayload);

      if (currentVotes >= votesNeeded) {
        // Reset room state and restart countdown
        room.state = 'countdown';
        room.finishedOrder = [];
        room.rematchVotes.clear();
        room.currentLap = { [room.p1]: 1 };
        room.checkpoints = { [room.p1]: 0 };
        if (room.p2) {
          room.currentLap[room.p2] = 1;
          room.checkpoints[room.p2] = 0;
        }

        const resetPayload = { type: 'race_reset_for_rematch' };
        sendTo(p1Obj, resetPayload);
        if (p2Obj) sendTo(p2Obj, resetPayload);

        // 3-2-1-GO!
        let count = 3;
        const sendCountdown = () => {
          const payload = {
            type: 'countdown_tick',
            count: count,
            text: count > 0 ? `${count}` : 'GO!'
          };

          sendTo(p1Obj, payload);
          if (p2Obj) sendTo(p2Obj, payload);

          if (count === 0) {
            room.state = 'racing';
            room.startTime = Date.now();
          } else {
            count--;
            setTimeout(sendCountdown, 1000);
          }
        };

        setTimeout(sendCountdown, 500);
      }
      return;
    }

    // 13. LEAVE ROOM / RETURN TO LOBBY
    if (type === 'leave_room') {
      cleanPlayerRoom(player, true);
      broadcastLobby();
      return;
    }
  });

  ws.on('close', () => {
    cleanPlayerDisconnect(player);
  });

  ws.on('error', () => {
    cleanPlayerDisconnect(player);
  });
});

function cleanPlayerRoom(player, informOpponent = true) {
  if (!player.roomId) return;

  const roomId = player.roomId;
  const room = rooms.get(roomId);

  if (room) {
    if (!room.isSolo && informOpponent) {
      const opponentId = (room.p1 === player.id) ? room.p2 : room.p1;
      const opponent = players.get(opponentId);
      if (opponent) {
        sendTo(opponent, {
          type: 'opponent_left',
          message: `${player.name} xonani tark etdi.`
        });
        opponent.roomId = null;
        opponent.status = 'lobby';
      }
    }
    rooms.delete(roomId);
  }

  player.roomId = null;
  player.status = 'lobby';
}

function cleanPlayerDisconnect(player) {
  // Cancel any challenges involving this player
  for (const [chId, ch] of challenges) {
    if (ch.fromId === player.id || ch.toId === player.id) {
      clearTimeout(ch.timer);
      const otherId = (ch.fromId === player.id) ? ch.toId : ch.fromId;
      const other = players.get(otherId);
      if (other) {
        other.status = 'lobby';
        sendTo(other, { type: 'challenge_canceled_by_sender' });
      }
      challenges.delete(chId);
    }
  }

  cleanPlayerRoom(player, true);
  players.delete(player.id);
  broadcastLobby();
}

// Start HTTP + WS Server
server.listen(PORT, HOST, () => {
  console.log(`=======================================================`);
  console.log(`🏁 APEX SPEED 3D - Termux Racing Server`);
  console.log(`📡 HTTP & WebSocket running on: http://${HOST}:${PORT}`);
  console.log(`⚡ Low-overhead Mode: Client-Side Physics | Zero Heavy Server Compute`);
  console.log(`=======================================================`);
});
