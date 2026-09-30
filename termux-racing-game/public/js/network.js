/**
 * APEX SPEED 3D - High-Performance WebSocket Network Client
 * Handles real-time telemetry relay, matchmaking, challenge flow, and ping measurement
 */

class NetworkManager {
  constructor() {
    this.ws = null;
    this.playerId = null;
    this.playerName = localStorage.getItem('apex_racer_name') || `Racer ${Math.floor(100 + Math.random() * 900)}`;
    this.selectedCarType = localStorage.getItem('apex_car_type') || 'hypercar';
    this.selectedTrackId = localStorage.getItem('apex_track_id') || 'neon_city';
    this.ping = 0;
    this.connected = false;
    this.currentRoom = null;
    this.activeChallenge = null;
    this.pingTimer = null;
    this.reconnectTimer = null;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${protocol}${window.location.host}`;

    this.updateConnectionStatus('connecting');

    try {
      this.ws = new WebSocket(wsUrl);
    } catch (e) {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.updateConnectionStatus('connected');
      
      // Register with saved or generated name
      this.send({ type: 'set_name', name: this.playerName });

      // Register selected car
      this.send({ type: 'set_car', carType: this.selectedCarType });

      // Start Ping loop
      this.startPingLoop();
    };

    this.ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        return;
      }
      this.handleMessage(msg);
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.updateConnectionStatus('offline');
      this.stopPingLoop();
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.connected = false;
      this.updateConnectionStatus('offline');
    };
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 2000);
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  startPingLoop() {
    this.stopPingLoop();
    this.pingTimer = setInterval(() => {
      if (this.connected) {
        this.send({ type: 'ping', t: Date.now() });
      }
    }, 1000);
  }

  stopPingLoop() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  updateConnectionStatus(status) {
    const badge = document.getElementById('termux-status-badge');
    if (!badge) return;

    if (status === 'connected') {
      badge.innerHTML = `<span class="live-dot"></span> Termux: Online`;
      badge.style.color = '#00ff88';
      badge.style.borderColor = 'rgba(0, 255, 136, 0.4)';
    } else if (status === 'connecting') {
      badge.innerHTML = `<span class="live-dot" style="background:#ffbe0b"></span> Ulanmoqda...`;
      badge.style.color = '#ffbe0b';
      badge.style.borderColor = 'rgba(255, 190, 11, 0.4)';
    } else {
      badge.innerHTML = `<span class="live-dot" style="background:#ff2b56"></span> Aloqa yo'q`;
      badge.style.color = '#ff2b56';
      badge.style.borderColor = 'rgba(255, 43, 86, 0.4)';
    }
  }

  setName(newName) {
    this.playerName = newName;
    localStorage.setItem('apex_racer_name', newName);
    this.send({ type: 'set_name', name: newName });
  }

  setCar(carType) {
    this.selectedCarType = carType;
    try {
      localStorage.setItem('apex_car_type', carType);
    } catch (e) {}
    this.send({ type: 'set_car', carType });
  }

  setTrack(trackId) {
    this.selectedTrackId = trackId;
    try {
      localStorage.setItem('apex_track_id', trackId);
    } catch (e) {}
  }

  sendChallenge(targetId) {
    this.send({
      type: 'challenge_send',
      targetId,
      trackId: this.selectedTrackId,
      carType: this.selectedCarType
    });
  }

  cancelChallenge(challengeId) {
    this.send({ type: 'challenge_cancel', challengeId });
  }

  acceptChallenge(challengeId) {
    this.send({
      type: 'challenge_accept',
      challengeId,
      carType: this.selectedCarType
    });
  }

  declineChallenge(challengeId) {
    this.send({ type: 'challenge_decline', challengeId });
  }

  startSoloPractice() {
    this.send({
      type: 'solo_practice',
      trackId: this.selectedTrackId,
      carType: this.selectedCarType
    });
  }

  sendClientReady(roomId) {
    this.send({ type: 'client_ready', roomId });
  }

  sendCarUpdate(compactData) {
    // Direct array [x, y, z, rotY, steer, speed, isDrift]
    this.send({
      type: 'car_update',
      d: compactData
    });
  }

  sendCheckpointPass(index, lap) {
    this.send({
      type: 'checkpoint_pass',
      checkpointIndex: index,
      lap: lap
    });
  }

  sendRaceFinish(totalTime, bestLap) {
    this.send({
      type: 'race_finish',
      totalTime: totalTime,
      bestLap: bestLap
    });
  }

  sendRematchVote() {
    this.send({ type: 'rematch_vote' });
  }

  leaveRoom() {
    this.send({ type: 'leave_room' });
  }

  handleMessage(msg) {
    switch (msg.type) {
      case 'welcome':
        this.playerId = msg.id;
        this.playerName = msg.name;
        const nameInput = document.getElementById('player-name-input');
        if (nameInput) nameInput.value = this.playerName;
        break;

      case 'pong':
        this.ping = Math.max(1, Date.now() - msg.t);
        const pingHud = document.getElementById('hud-ping');
        const pingLobby = document.getElementById('lobby-ping');
        if (pingHud) pingHud.textContent = `Ping: ${this.ping} ms`;
        if (pingLobby) pingLobby.textContent = `${this.ping} ms`;
        break;

      case 'lobby_update':
        if (window.gameApp) {
          window.gameApp.renderLobbyPlayers(msg.players, this.playerId);
        }
        break;

      case 'challenge_sent':
        if (window.gameApp) {
          window.gameApp.showOutgoingChallengeModal(msg);
        }
        break;

      case 'challenge_incoming':
        if (window.gameApp) {
          window.gameApp.showIncomingChallengeModal(msg);
        }
        break;

      case 'challenge_timeout':
      case 'challenge_expired':
      case 'challenge_declined':
      case 'challenge_canceled_by_sender':
      case 'challenge_error':
        if (window.gameApp) {
          window.gameApp.hideChallengeModals();
          if (msg.message || msg.targetName) {
            alert(msg.message || `${msg.targetName || 'Raqib'} taklifni rad etdi yoki vaqt tugadi.`);
          }
        }
        break;

      case 'match_start':
        this.currentRoom = msg.roomId;
        if (window.gameApp) {
          window.gameApp.startRaceSession(msg);
        }
        break;

      case 'countdown_tick':
        if (window.gameApp) {
          window.gameApp.onCountdownTick(msg.count, msg.text);
        }
        break;

      case 'opponent_update':
        if (window.gameApp) {
          window.gameApp.onOpponentCarUpdate(msg.d);
        }
        break;

      case 'opponent_progress':
        if (window.gameApp) {
          window.gameApp.onOpponentProgress(msg.checkpointIndex, msg.lap);
        }
        break;

      case 'race_ended':
        if (window.gameApp) {
          window.gameApp.onRaceEnded(msg);
        }
        break;

      case 'opponent_finished':
        if (window.gameApp) {
          window.gameApp.onOpponentFinished(msg);
        }
        break;

      case 'rematch_status':
        if (window.gameApp) {
          window.gameApp.updateRematchStatus(msg.votes, msg.needed, msg.votedBy);
        }
        break;

      case 'race_reset_for_rematch':
        if (window.gameApp) {
          window.gameApp.resetForRematch();
        }
        break;

      case 'opponent_left':
        alert(msg.message || "Raqib xonadan chiqib ketdi.");
        if (window.gameApp) {
          window.gameApp.returnToLobby();
        }
        break;
    }
  }
}

window.networkManager = new NetworkManager();
