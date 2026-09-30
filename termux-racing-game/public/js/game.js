/**
 * APEX SPEED 3D - Main Game Loop & UI Orchestrator (V3.2)
 * High-performance WebGL renderer, interactive 3D showroom turntable,
 * visual SVG track maps, and multiplayer state machine.
 */

class GameApp {
  constructor() {
    this.container = document.getElementById('canvas-container');
    this.state = 'LOBBY'; // 'LOBBY' | 'COUNTDOWN' | 'RACING' | 'FINISHED'
    
    this.scene = null;
    this.camera = null;
    this.renderer = null;

    this.track = null;
    this.localCar = null;
    this.remoteCar = null;

    // Showroom 3D Turntable State
    this.showroomGroup = null;
    this.showroomPodium = null;
    this.showroomPodiumRing = null;
    this.showroomCar = null;
    this.showroomAngle = 0;
    this.userDragRotY = 0;
    this.isDraggingShowroom = false;
    this.dragStartX = 0;

    this.role = 'p1'; // 'p1' | 'p2'
    this.isSolo = false;
    this.lapsTotal = 2;
    this.currentLap = 1;
    this.currentCheckpoint = 0;
    this.opponentLap = 1;
    this.opponentCheckpoint = 0;

    // Car & Track Selection State
    this.carTypesList = ['hypercar', 'muscle', 'truck', 'formula'];
    this.currentCarType = localStorage.getItem('apex_car_type') || 'hypercar';
    this.currentTrackId = localStorage.getItem('apex_track_id') || 'neon_city';
    this.cameraShake = 0;

    // Car Specifications Map
    this.carSpecs = {
      hypercar: {
        name: 'Apex GT',
        badge: 'HYPERCAR',
        speedText: '340 KM/H',
        speedPct: 88,
        accelText: '0-100: 2.8s',
        accelPct: 82,
        handlingText: 'High Grip',
        handlingPct: 85,
        durabilityText: 'Standart',
        durabilityPct: 70
      },
      muscle: {
        name: 'V8 Beast',
        badge: 'MUSCLE GT',
        speedText: '320 KM/H',
        speedPct: 82,
        accelText: '0-100: 2.4s',
        accelPct: 96,
        handlingText: 'Drift Heavy',
        handlingPct: 65,
        durabilityText: 'Kuchli',
        durabilityPct: 82
      },
      truck: {
        name: 'Cyber Armor',
        badge: '4X4 TRUCK',
        speedText: '290 KM/H',
        speedPct: 72,
        accelText: '0-100: 3.5s',
        accelPct: 62,
        handlingText: 'Og\'ir Barqaror',
        handlingPct: 60,
        durabilityText: 'Zirhli 100%',
        durabilityPct: 100
      },
      formula: {
        name: 'Aero GP',
        badge: 'FORMULA 1',
        speedText: '370 KM/H',
        speedPct: 100,
        accelText: '0-100: 2.1s',
        accelPct: 94,
        handlingText: 'Maksimal Boshqaruv',
        handlingPct: 98,
        durabilityText: 'Yengil',
        durabilityPct: 55
      }
    };

    // Timing
    this.clock = new THREE.Clock();
    this.raceStartTime = 0;
    this.lapStartTime = 0;
    this.bestLapTime = Infinity;
    this.totalRaceTime = 0;

    // Network throttle (30 updates/sec = 33ms interval for silky multiplayer)
    this.lastNetSendTime = 0;
    this.netSendInterval = 0.033;

    // FPS calculation
    this.frameCount = 0;
    this.lastFpsUpdate = 0;
    this.currentFps = 60;

    // Outgoing/Incoming Challenge Tracking
    this.challengeTimeoutId = null;
    this.challengeProgressInterval = null;

    this.initThree();
    this.initShowroom();
    this.initPointerDragControls();
    this.initEventListeners();
    this.animate();
  }

  initThree() {
    // 1. Scene & Atmospheric Lighting
    this.scene = new THREE.Scene();
    this.updateEnvironmentAtmosphere(this.currentTrackId);

    // 2. Camera
    const aspect = window.innerWidth / window.innerHeight;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.5, 800);
    this.camera.position.set(0, 1.85, 5.2);
    this.camera.lookAt(0, 0.65, 0);

    // 3. Renderer (Optimized for 60 FPS mobile: capped 1.5 pixelRatio, no heavy shadow passes)
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = false; // Massive FPS boost across all devices!
    this.container.appendChild(this.renderer.domElement);

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0x5a6d8a, 0.95);
    this.scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff5e6, 1.4);
    sunLight.position.set(80, 120, 60);
    sunLight.castShadow = false;
    this.scene.add(sunLight);

    // 5. Build Procedural Race Track for current track theme
    this.track = new RaceTrack(this.scene, this.currentTrackId);

    // Handle Window Resize
    window.addEventListener('resize', () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  // --- 3D SHOWROOM PODIUM & VEHICLE STAGE ---
  initShowroom() {
    this.showroomGroup = new THREE.Group();

    // 1. Dark metallic rotating podium base
    const baseGeo = new THREE.CylinderGeometry(3.4, 3.7, 0.35, 36);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x0f1522,
      roughness: 0.3,
      metalness: 0.85
    });
    this.showroomPodium = new THREE.Mesh(baseGeo, baseMat);
    this.showroomPodium.position.set(0, 0.175, 0);
    this.showroomPodium.receiveShadow = true;
    this.showroomGroup.add(this.showroomPodium);

    // 2. Glowing cyan perimeter neon ring
    const ringGeo = new THREE.TorusGeometry(3.5, 0.06, 12, 48);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    this.showroomPodiumRing = new THREE.Mesh(ringGeo, ringMat);
    this.showroomPodiumRing.rotation.x = Math.PI / 2;
    this.showroomPodiumRing.position.set(0, 0.35, 0);
    this.showroomGroup.add(this.showroomPodiumRing);

    // 3. Inner glowing cyber floor circle
    const floorGeo = new THREE.CircleGeometry(3.3, 36);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x141e33,
      roughness: 0.2,
      metalness: 0.7
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(0, 0.352, 0);
    floorMesh.receiveShadow = true;
    this.showroomGroup.add(floorMesh);

    // 4. Subtle underglow light beneath the car
    const underglow = new THREE.PointLight(0x00f0ff, 2.8, 6);
    underglow.position.set(0, 0.45, 0);
    this.showroomGroup.add(underglow);

    // 5. Overhead dramatic showroom spotlights
    const spotFront = new THREE.SpotLight(0xffffff, 2.2, 22, Math.PI / 4, 0.4);
    spotFront.position.set(2, 6, 4);
    spotFront.target = this.showroomPodium;
    this.showroomGroup.add(spotFront);

    const spotBack = new THREE.SpotLight(0x00f0ff, 2.5, 22, Math.PI / 4, 0.4);
    spotBack.position.set(-3, 5, -4);
    spotBack.target = this.showroomPodium;
    this.showroomGroup.add(spotBack);

    this.scene.add(this.showroomGroup);

    // 6. Spawn initial 3D showroom car
    this.switchShowroomCar(this.currentCarType, false);
  }

  switchShowroomCar(carType, playSound = true) {
    if (!this.carSpecs[carType]) carType = 'hypercar';
    this.currentCarType = carType;

    if (this.showroomCar) {
      this.showroomCar.dispose();
      this.showroomCar = null;
    }

    if (this.state === 'LOBBY') {
      this.showroomCar = new Car(this.scene, 'red', false, carType);
      this.showroomCar.mesh.position.set(0, 0.35, 0);
      this.showroomAngle += 0.8; // subtle spin impulse on change
    }

    this.updateCarSpecsHUD(carType);
    window.networkManager.setCar(carType);

    if (playSound && window.soundEngine) {
      window.soundEngine.playCheckpoint();
    }
  }

  prevCar() {
    const idx = this.carTypesList.indexOf(this.currentCarType);
    const prevIdx = (idx - 1 + this.carTypesList.length) % this.carTypesList.length;
    this.switchShowroomCar(this.carTypesList[prevIdx]);
  }

  nextCar() {
    const idx = this.carTypesList.indexOf(this.currentCarType);
    const nextIdx = (idx + 1) % this.carTypesList.length;
    this.switchShowroomCar(this.carTypesList[nextIdx]);
  }

  updateCarSpecsHUD(carType) {
    const spec = this.carSpecs[carType] || this.carSpecs.hypercar;

    // Center Showroom Header
    const nameEl = document.getElementById('showroom-car-name');
    const badgeEl = document.getElementById('showroom-car-badge');
    const specClassEl = document.getElementById('specs-car-class');
    if (nameEl) nameEl.textContent = spec.name;
    if (badgeEl) badgeEl.textContent = spec.badge;
    if (specClassEl) specClassEl.textContent = spec.badge;

    // Spec values & meter bars
    const valSpeed = document.getElementById('spec-val-speed');
    const barSpeed = document.getElementById('spec-bar-speed');
    if (valSpeed) valSpeed.textContent = spec.speedText;
    if (barSpeed) barSpeed.style.width = `${spec.speedPct}%`;

    const valAccel = document.getElementById('spec-val-accel');
    const barAccel = document.getElementById('spec-bar-accel');
    if (valAccel) valAccel.textContent = spec.accelText;
    if (barAccel) barAccel.style.width = `${spec.accelPct}%`;

    const valHand = document.getElementById('spec-val-handling');
    const barHand = document.getElementById('spec-bar-handling');
    if (valHand) valHand.textContent = spec.handlingText;
    if (barHand) barHand.style.width = `${spec.handlingPct}%`;

    const valDur = document.getElementById('spec-val-durability');
    const barDur = document.getElementById('spec-bar-durability');
    if (valDur) valDur.textContent = spec.durabilityText;
    if (barDur) barDur.style.width = `${spec.durabilityPct}%`;

    // Active pill state
    document.querySelectorAll('.car-pill').forEach(pill => {
      if (pill.dataset.car === carType) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
  }

  // --- 360-DEGREE MOUSE / TOUCH DRAG CONTROLS ---
  initPointerDragControls() {
    const dom = this.renderer.domElement;
    dom.addEventListener('pointerdown', (e) => {
      if (this.state === 'LOBBY') {
        this.isDraggingShowroom = true;
        this.dragStartX = e.clientX;
      }
    });

    window.addEventListener('pointermove', (e) => {
      if (this.isDraggingShowroom && this.state === 'LOBBY') {
        const dx = e.clientX - this.dragStartX;
        this.dragStartX = e.clientX;
        this.userDragRotY += dx * 0.012;
      }
    });

    window.addEventListener('pointerup', () => {
      this.isDraggingShowroom = false;
    });

    window.addEventListener('pointercancel', () => {
      this.isDraggingShowroom = false;
    });
  }

  updateEnvironmentAtmosphere(trackId) {
    if (trackId === 'desert_canyon') {
      this.scene.background = new THREE.Color(0x1a0f0a);
      this.scene.fog = new THREE.FogExp2(0x1a0f0a, 0.0035);
    } else if (trackId === 'arctic_glacier') {
      this.scene.background = new THREE.Color(0x0a1424);
      this.scene.fog = new THREE.FogExp2(0x0a1424, 0.0038);
    } else {
      // Neon City
      this.scene.background = new THREE.Color(0x0a0e17);
      this.scene.fog = new THREE.FogExp2(0x0a0e17, 0.004);
    }
  }

  initEventListeners() {
    // Player Name Change
    const nameInput = document.getElementById('player-name-input');
    if (nameInput) {
      nameInput.value = window.networkManager.playerName;
      nameInput.addEventListener('change', (e) => {
        window.networkManager.setName(e.target.value);
      });
    }

    // Car Carousel Nav Buttons [❮] and [❯]
    const btnPrev = document.getElementById('btn-prev-car');
    const btnNext = document.getElementById('btn-next-car');
    if (btnPrev) btnPrev.addEventListener('click', () => this.prevCar());
    if (btnNext) btnNext.addEventListener('click', () => this.nextCar());

    // Quick Car Selector Pills
    document.querySelectorAll('.car-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const cType = pill.dataset.car;
        this.switchShowroomCar(cType);
      });
    });

    // Visual Track Map Cards Selection ("yollar ham maps da korinib tursin")
    const trackCards = document.querySelectorAll('.track-map-card');
    const trackNameTag = document.getElementById('selected-track-name');

    trackCards.forEach(card => {
      const tId = card.dataset.track;
      if (tId === this.currentTrackId) {
        card.classList.add('selected');
        if (trackNameTag) trackNameTag.textContent = this.getTrackDisplayName(tId).toUpperCase();
      } else {
        card.classList.remove('selected');
      }

      card.addEventListener('click', () => {
        if (window.soundEngine) {
          window.soundEngine.unlock();
          window.soundEngine.playCheckpoint();
        }
        trackCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        this.currentTrackId = tId;
        if (trackNameTag) trackNameTag.textContent = this.getTrackDisplayName(tId).toUpperCase();
        window.networkManager.setTrack(tId);

        // Update 3D preview backdrop in lobby
        if (this.state === 'LOBBY') {
          if (this.track) this.track.dispose();
          this.updateEnvironmentAtmosphere(tId);
          this.track = new RaceTrack(this.scene, tId);
        }
      });
    });

    // Music Toggle (Lobby Header & In-Game HUD)
    const lobbyMusicBtn = document.getElementById('btn-music-toggle');
    const hudMusicBtn = document.getElementById('hud-music-btn');

    const updateMusicUI = (isOn) => {
      if (lobbyMusicBtn) {
        lobbyMusicBtn.innerHTML = isOn
          ? `🎵 <span class="btn-text">Musiqa: ON</span>`
          : `🔇 <span class="btn-text">Musiqa: OFF</span>`;
      }
      if (hudMusicBtn) hudMusicBtn.textContent = isOn ? '🎵 Musiqa' : '🔇 Jimlik';
    };

    if (lobbyMusicBtn) {
      lobbyMusicBtn.addEventListener('click', () => {
        if (window.soundEngine) {
          window.soundEngine.unlock();
          const enabled = window.soundEngine.toggleMusic();
          updateMusicUI(enabled);
        }
      });
    }

    if (hudMusicBtn) {
      hudMusicBtn.addEventListener('click', () => {
        if (window.soundEngine) {
          window.soundEngine.unlock();
          const enabled = window.soundEngine.toggleMusic();
          updateMusicUI(enabled);
        }
      });
    }

    // Multiplayer Drawer Toggles
    const openDrawerBtn = document.getElementById('btn-open-multiplayer');
    const challengeFlowBtn = document.getElementById('btn-challenge-flow');
    const closeDrawerBtn = document.getElementById('btn-close-drawer');
    const drawer = document.getElementById('multiplayer-drawer');

    const toggleDrawer = (show) => {
      if (drawer) {
        if (show) drawer.classList.remove('hidden');
        else drawer.classList.add('hidden');
      }
    };

    if (openDrawerBtn) openDrawerBtn.addEventListener('click', () => toggleDrawer(true));
    if (challengeFlowBtn) challengeFlowBtn.addEventListener('click', () => toggleDrawer(true));
    if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', () => toggleDrawer(false));

    // Controls Help Modal
    const controlsHelpBtn = document.getElementById('btn-controls-help');
    const controlsModal = document.getElementById('controls-modal');
    const closeControlsBtn = document.getElementById('btn-close-controls');

    if (controlsHelpBtn && controlsModal) {
      controlsHelpBtn.addEventListener('click', () => controlsModal.classList.remove('hidden'));
    }
    if (closeControlsBtn && controlsModal) {
      closeControlsBtn.addEventListener('click', () => controlsModal.classList.add('hidden'));
    }

    // Solo Practice Button
    const soloBtn = document.getElementById('btn-solo-practice');
    if (soloBtn) {
      soloBtn.addEventListener('click', () => {
        if (window.soundEngine) window.soundEngine.unlock();
        window.networkManager.startSoloPractice();
      });
    }

    // Rematch Button
    const rematchBtn = document.getElementById('btn-rematch');
    if (rematchBtn) {
      rematchBtn.addEventListener('click', () => {
        rematchBtn.disabled = true;
        rematchBtn.textContent = 'Kutilmoqda... (1/2)';
        window.networkManager.sendRematchVote();
      });
    }

    // Exit to Lobby Button
    const exitBtn = document.getElementById('btn-exit-lobby');
    if (exitBtn) {
      exitBtn.addEventListener('click', () => {
        window.networkManager.leaveRoom();
        this.returnToLobby();
      });
    }

    // Direct click/tap on Nitro HUD gauge to fire Nitro
    const nitroWrap = document.getElementById('hud-nitro-wrap');
    if (nitroWrap) {
      nitroWrap.addEventListener('click', () => {
        if (this.localCar && this.state === 'RACING') {
          if (this.localCar.triggerNitro()) {
            if (window.soundEngine) window.soundEngine.playNitro();
            this.showHudAlert('🔥 NITRO ISHLATILDI! +160 KM/H', 'nitro');
            this.cameraShake = Math.max(this.cameraShake, 0.5);
          }
        }
      });
    }
  }

  getTrackDisplayName(trackId) {
    if (trackId === 'desert_canyon') return 'Desert Canyon';
    if (trackId === 'arctic_glacier') return 'Arctic Glacier';
    return 'Neon Metropolis';
  }

  getCarDisplayName(carType) {
    if (carType === 'muscle') return 'V8 Beast (Muscle GT)';
    if (carType === 'truck') return 'Cyber Armor (4x4 Truck)';
    if (carType === 'formula') return 'Aero GP (Formula 1)';
    return 'Apex GT (Hypercar)';
  }

  // --- LOBBY PLAYERS RENDERING ---
  renderLobbyPlayers(playersList, myId) {
    const listEl = document.getElementById('lobby-players-list');
    const countBadge = document.getElementById('online-count-badge');
    const drawerCount = document.getElementById('drawer-player-count');
    if (!listEl) return;

    const countText = `${playersList.length} Online`;
    if (countBadge) countBadge.textContent = countText;
    if (drawerCount) drawerCount.textContent = countText;

    listEl.innerHTML = '';

    const otherPlayers = playersList.filter(p => p.id !== myId);

    if (otherPlayers.length === 0) {
      listEl.innerHTML = `
        <div class="no-players">
          Hozircha serverda boshqa o'yinchi yo'q.<br>
          Do'stingizga linkni yuboring yoki <b>SOLO POYGA</b> qiling!
        </div>
      `;
      return;
    }

    otherPlayers.forEach(p => {
      const item = document.createElement('div');
      item.className = 'player-item';

      let statusBadge = '';
      let actionBtn = '';

      if (p.status === 'lobby') {
        statusBadge = `<span class="status-badge lobby">Online</span>`;
        actionBtn = `<button class="btn-challenge" onclick="window.gameApp.onChallengeClick('${p.id}')">⚔️ Duel</button>`;
      } else if (p.status === 'in_race') {
        statusBadge = `<span class="status-badge in_race">Poygada</span>`;
        actionBtn = `<button class="btn-challenge" disabled>Band</button>`;
      } else {
        statusBadge = `<span class="status-badge challenging">Kutmoqda</span>`;
        actionBtn = `<button class="btn-challenge" disabled>Band</button>`;
      }

      item.innerHTML = `
        <div class="player-item-info">
          <div class="avatar-circle">🏎️</div>
          <div>
            <div class="player-name-text">${this.escapeHtml(p.name)}</div>
            ${statusBadge}
          </div>
        </div>
        ${actionBtn}
      `;
      listEl.appendChild(item);
    });
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str;
    return div.innerHTML;
  }

  onChallengeClick(targetId) {
    if (window.soundEngine) window.soundEngine.unlock();
    window.networkManager.sendChallenge(targetId);
  }

  showOutgoingChallengeModal(msg) {
    const modal = document.getElementById('outgoing-challenge-modal');
    const targetNameEl = document.getElementById('outgoing-target-name');
    const trackInfoEl = document.getElementById('outgoing-track-info');
    const cancelBtn = document.getElementById('btn-cancel-outgoing');
    const bar = document.getElementById('outgoing-countdown-bar');

    if (targetNameEl) targetNameEl.textContent = msg.targetName;
    if (trackInfoEl) trackInfoEl.textContent = `📍 Trassa: ${this.getTrackDisplayName(msg.trackId || this.currentTrackId)}`;
    if (modal) modal.classList.remove('hidden');

    if (bar) {
      bar.style.transition = 'none';
      bar.style.width = '100%';
      setTimeout(() => {
        bar.style.transition = 'width 15s linear';
        bar.style.width = '0%';
      }, 50);
    }

    if (cancelBtn) {
      cancelBtn.onclick = () => {
        window.networkManager.cancelChallenge(msg.challengeId);
        this.hideChallengeModals();
      };
    }
  }

  showIncomingChallengeModal(msg) {
    if (window.soundEngine) {
      window.soundEngine.unlock();
      window.soundEngine.playCountdown(3);
    }

    const modal = document.getElementById('incoming-challenge-modal');
    const senderNameEl = document.getElementById('incoming-sender-name');
    const trackInfoEl = document.getElementById('incoming-track-info');
    const acceptBtn = document.getElementById('btn-accept-challenge');
    const declineBtn = document.getElementById('btn-decline-challenge');
    const bar = document.getElementById('incoming-countdown-bar');

    if (senderNameEl) {
      const oppCarText = msg.fromCarType ? ` [${this.getCarDisplayName(msg.fromCarType)}]` : '';
      senderNameEl.textContent = `${msg.fromName}${oppCarText}`;
    }
    if (trackInfoEl) {
      trackInfoEl.textContent = `📍 Trassa: ${this.getTrackDisplayName(msg.trackId)}`;
    }
    if (modal) modal.classList.remove('hidden');

    if (bar) {
      bar.style.transition = 'none';
      bar.style.width = '100%';
      setTimeout(() => {
        bar.style.transition = 'width 15s linear';
        bar.style.width = '0%';
      }, 50);
    }

    if (acceptBtn) {
      acceptBtn.onclick = () => {
        window.networkManager.acceptChallenge(msg.challengeId);
        this.hideChallengeModals();
      };
    }

    if (declineBtn) {
      declineBtn.onclick = () => {
        window.networkManager.declineChallenge(msg.challengeId);
        this.hideChallengeModals();
      };
    }
  }

  hideChallengeModals() {
    const incoming = document.getElementById('incoming-challenge-modal');
    const outgoing = document.getElementById('outgoing-challenge-modal');
    if (incoming) incoming.classList.add('hidden');
    if (outgoing) outgoing.classList.add('hidden');
  }

  // --- RACE SESSION INITIALIZATION ---
  startRaceSession(config) {
    this.hideChallengeModals();
    this.state = 'COUNTDOWN';
    this.role = config.role;
    this.isSolo = !!config.isSolo;
    this.lapsTotal = config.lapsTotal || 2;
    this.currentLap = 1;
    this.currentCheckpoint = 0;
    this.opponentLap = 1;
    this.opponentCheckpoint = 0;
    this.cameraShake = 0;

    // Reset visual FX overlays
    const speedBlurEl = document.getElementById('speed-blur-fx');
    const impactBlurEl = document.getElementById('impact-blur-fx');
    const oilBlurEl = document.getElementById('oil-blur-fx');
    if (speedBlurEl) speedBlurEl.className = 'fx-overlay';
    if (impactBlurEl) impactBlurEl.className = 'fx-overlay';
    if (oilBlurEl) oilBlurEl.className = 'fx-overlay';

    // Switch UI Screens
    const lobbyScreen = document.getElementById('lobby-screen');
    const hudOverlay = document.getElementById('hud-overlay');
    const resultsModal = document.getElementById('results-modal');
    const drawer = document.getElementById('multiplayer-drawer');

    if (lobbyScreen) lobbyScreen.style.display = 'none';
    if (resultsModal) resultsModal.classList.add('hidden');
    if (drawer) drawer.classList.add('hidden');
    if (hudOverlay) hudOverlay.classList.remove('hidden');

    // Clean up Showroom Group during race
    if (this.showroomGroup) {
      this.showroomGroup.visible = false;
    }
    if (this.showroomCar) {
      this.showroomCar.dispose();
      this.showroomCar = null;
    }

    // Build or switch race track to requested map
    const targetTrackId = config.trackId || this.currentTrackId || 'neon_city';
    if (this.track) {
      this.track.dispose();
    }
    this.currentTrackId = targetTrackId;
    this.updateEnvironmentAtmosphere(targetTrackId);
    this.track = new RaceTrack(this.scene, targetTrackId);

    // Clean up previous cars if any
    if (this.localCar) this.localCar.dispose();
    if (this.remoteCar) this.remoteCar.dispose();

    // Spawn Local Car with customized car archetype
    const myColor = config.color; // 'red' or 'cyan'
    const myCarType = config.myCarType || this.currentCarType || 'hypercar';
    this.localCar = new Car(this.scene, myColor, false, myCarType);

    const slotIdx = (config.gridSlot || 1) - 1;
    const startData = this.track.startPositions[slotIdx];
    this.localCar.resetPosition(startData.pos.x, startData.pos.y, startData.pos.z, startData.rotY);

    // Spawn Remote Opponent Car (if multiplayer)
    if (!this.isSolo) {
      const oppColor = myColor === 'red' ? 'cyan' : 'red';
      const oppCarType = config.oppCarType || 'hypercar';
      this.remoteCar = new Car(this.scene, oppColor, true, oppCarType);

      const oppSlotIdx = slotIdx === 0 ? 1 : 0;
      const oppStartData = this.track.startPositions[oppSlotIdx];
      this.remoteCar.resetPosition(oppStartData.pos.x, oppStartData.pos.y, oppStartData.pos.z, oppStartData.rotY);
    } else {
      this.remoteCar = null;
    }

    // Start background synthwave music
    if (window.soundEngine) {
      window.soundEngine.startMusic();
    }

    // Lock input during countdown
    window.inputController.lock();

    // Reset Gantry lights
    this.track.setGantryLights('off');

    // Notify server we are ready
    window.networkManager.sendClientReady(config.roomId);
  }

  onCountdownTick(count, text) {
    const cdEl = document.getElementById('countdown-screen');
    if (!cdEl) return;

    cdEl.textContent = text;
    cdEl.className = 'active';

    if (count > 0) {
      if (window.soundEngine) window.soundEngine.playCountdown(count);
      this.track.setGantryLights(`${count}`);
    } else {
      // GO!
      cdEl.classList.add('go');
      if (window.soundEngine) window.soundEngine.playCountdown(0);
      this.track.setGantryLights('go');

      this.state = 'RACING';
      this.raceStartTime = performance.now();
      this.lapStartTime = performance.now();
      window.inputController.unlock();

      // Fade out countdown text after 1s
      setTimeout(() => {
        cdEl.className = '';
        this.track.setGantryLights('off');
      }, 1000);
    }
  }

  onOpponentCarUpdate(data) {
    // data = [x, y, z, rotY, steer, speed, isDrift, isNitro]
    if (this.remoteCar && data) {
      this.remoteCar.setRemoteState(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]);
    }
  }

  onOpponentCheckpointPass(cpIndex, lap) {
    this.opponentCheckpoint = cpIndex;
    this.opponentLap = lap;
  }

  onRaceFinish(msg = {}) {
    this.state = 'FINISHED';
    window.inputController.lock();

    if (this.localCar) {
      this.localCar.speed = 0;
      this.localCar.isNitro = false;
    }

    if (window.soundEngine) {
      window.soundEngine.stopEngine();
      window.soundEngine.stopMusic();
    }

    const modal = document.getElementById('results-modal');
    const titleEl = document.getElementById('results-title');
    const winnerEl = document.getElementById('results-winner-name');
    const totalTimeEl = document.getElementById('results-total-time');
    const bestLapEl = document.getElementById('results-best-lap');
    const rematchBtn = document.getElementById('btn-rematch');
    const rematchStatusPill = document.getElementById('rematch-status-pill');

    const isSolo = this.isSolo || msg.isSolo;
    const iWon = isSolo || msg.isWinner === true || msg.rank === 1 || (msg.winnerId && msg.winnerId === window.networkManager.playerId);

    if (isSolo) {
      if (titleEl) {
        titleEl.textContent = 'FINISH! 🏁';
        titleEl.style.color = '#00ff88';
      }
      if (winnerEl) winnerEl.textContent = '2 davrali poyga muvaffaqiyatli yakunlandi!';
      if (window.soundEngine) window.soundEngine.playWin();
    } else if (iWon) {
      if (titleEl) {
        titleEl.textContent = 'G\'ALABA! 🏆';
        titleEl.style.color = '#ffbe0b';
      }
      if (winnerEl) winnerEl.textContent = 'Tabriklaymiz, siz 1-o\'rinni egalladingiz!';
      if (window.soundEngine) window.soundEngine.playWin();
    } else {
      if (titleEl) {
        titleEl.textContent = '2-O\'RIN 🥈';
        titleEl.style.color = '#ff2b56';
      }
      if (winnerEl) winnerEl.textContent = `${msg.winnerName || 'Raqib'} marraga birinchi yetib keldi!`;
      if (window.soundEngine) window.soundEngine.playWin();
    }

    // Time extraction supporting all server & client response formats
    let finalTotalTime = msg.totalTime || this.totalRaceTime || 0;
    let finalBestLap = msg.bestLap || this.bestLapTime || 0;

    if (Array.isArray(msg.results) && msg.results.length > 0) {
      finalTotalTime = msg.results[0].time || finalTotalTime;
    } else if (msg.results && window.networkManager && msg.results[window.networkManager.playerId]) {
      const r = msg.results[window.networkManager.playerId];
      finalTotalTime = r.totalTime || finalTotalTime;
      finalBestLap = r.bestLap || finalBestLap;
    }

    if (totalTimeEl) totalTimeEl.textContent = this.formatTime(finalTotalTime);
    if (bestLapEl) bestLapEl.textContent = this.formatTime(finalBestLap);

    if (rematchBtn) {
      rematchBtn.disabled = false;
      rematchBtn.textContent = '🔄 Rematch (0/2)';
    }

    if (rematchStatusPill) {
      rematchStatusPill.textContent = isSolo
        ? 'Qaytadan poyga boshlash uchun Rematch bosing'
        : 'Rematch uchun ikkala poygachi ham tugmani bosishi kerak';
    }

    if (modal) modal.classList.remove('hidden');
  }

  // Network callback aliases
  onRaceEnded(msg) {
    this.onRaceFinish(msg);
  }

  onOpponentFinished(msg) {
    this.showHudAlert(`⚠️ ${msg.winnerName || 'Raqib'} marraga yetdi! Poygani yakunlang!`, 'obstacle');
  }

  onOpponentProgress(cpIndex, lap) {
    this.opponentCheckpoint = cpIndex;
    this.opponentLap = lap;
  }

  updateRematchStatus(votes, needed) {
    this.onRematchVoteStatus(votes, needed);
  }

  onRematchVoteStatus(votes, needed) {
    const rematchBtn = document.getElementById('btn-rematch');
    const rematchStatusPill = document.getElementById('rematch-status-pill');

    if (rematchBtn) {
      rematchBtn.textContent = `🔄 Rematch (${votes}/${needed})`;
    }
    if (rematchStatusPill) {
      rematchStatusPill.textContent = `${votes} ta o'yinchi rozilik berdi (${votes}/${needed})`;
    }
  }

  resetForRematch() {
    const resultsModal = document.getElementById('results-modal');
    if (resultsModal) resultsModal.classList.add('hidden');

    this.state = 'COUNTDOWN';
    this.currentLap = 1;
    this.currentCheckpoint = 0;
    this.opponentLap = 1;
    this.opponentCheckpoint = 0;
    this.bestLapTime = Infinity;

    // Reset local car
    const slotIdx = (this.role === 'p1' ? 1 : 2) - 1;
    const startData = this.track.startPositions[slotIdx];
    this.localCar.resetPosition(startData.pos.x, startData.pos.y, startData.pos.z, startData.rotY);

    // Reset remote car
    if (this.remoteCar) {
      const oppSlotIdx = slotIdx === 0 ? 1 : 0;
      const oppStartData = this.track.startPositions[oppSlotIdx];
      this.remoteCar.resetPosition(oppStartData.pos.x, oppStartData.pos.y, oppStartData.pos.z, oppStartData.rotY);
    }

    window.inputController.lock();
    this.track.setGantryLights('off');
  }

  returnToLobby() {
    this.state = 'LOBBY';
    window.inputController.lock();
    if (window.soundEngine) {
      window.soundEngine.stopEngine();
      window.soundEngine.stopMusic();
    }

    // Reset FX overlays
    const speedBlurEl = document.getElementById('speed-blur-fx');
    const impactBlurEl = document.getElementById('impact-blur-fx');
    const oilBlurEl = document.getElementById('oil-blur-fx');
    if (speedBlurEl) speedBlurEl.className = 'fx-overlay';
    if (impactBlurEl) impactBlurEl.className = 'fx-overlay';
    if (oilBlurEl) oilBlurEl.className = 'fx-overlay';

    const lobbyScreen = document.getElementById('lobby-screen');
    const hudOverlay = document.getElementById('hud-overlay');
    const resultsModal = document.getElementById('results-modal');

    if (lobbyScreen) lobbyScreen.style.display = 'flex';
    if (hudOverlay) hudOverlay.classList.add('hidden');
    if (resultsModal) resultsModal.classList.add('hidden');

    if (this.localCar) {
      this.localCar.dispose();
      this.localCar = null;
    }
    if (this.remoteCar) {
      this.remoteCar.dispose();
      this.remoteCar = null;
    }

    // Restore 3D showroom
    if (this.showroomGroup) {
      this.showroomGroup.visible = true;
    }
    this.switchShowroomCar(this.currentCarType, false);
  }

  formatTime(ms) {
    if (!ms || ms === Infinity) return '--:--.---';
    const totalSec = ms / 1000;
    const min = Math.floor(totalSec / 60);
    const sec = Math.floor(totalSec % 60);
    const millis = Math.floor((totalSec % 1) * 1000);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${millis.toString().padStart(3, '0')}`;
  }

  // --- MAIN ANIMATION & RENDER LOOP ---
  animate() {
    requestAnimationFrame(() => this.animate());

    const dt = Math.min(this.clock.getDelta(), 0.1);
    const now = performance.now();

    // FPS Meter
    this.frameCount++;
    if (now - this.lastFpsUpdate >= 500) {
      this.currentFps = Math.round((this.frameCount * 1000) / (now - this.lastFpsUpdate));
      this.frameCount = 0;
      this.lastFpsUpdate = now;
      const fpsEl = document.getElementById('hud-fps');
      if (fpsEl) fpsEl.textContent = `FPS: ${this.currentFps}`;
    }

    if (this.state === 'LOBBY') {
      // Rotate 3D Showroom Turntable
      this.showroomAngle += dt * 0.4;
      const totalRot = this.showroomAngle + this.userDragRotY;

      if (this.showroomCar && this.showroomCar.mesh) {
        this.showroomCar.mesh.position.set(0, 0.35, 0);
        this.showroomCar.mesh.rotation.y = totalRot;
      }
      if (this.showroomPodiumRing) {
        this.showroomPodiumRing.rotation.z -= dt * 0.5;
      }

      // Camera positions right in front of the 3D car
      this.camera.position.set(0, 1.85, 5.2);
      this.camera.lookAt(0, 0.65, 0);

      // Keep subtle environment animation alive
      if (this.track && this.track.update) {
        this.track.update(dt);
      }
    } else {
      // In-Game Update
      if (this.track && this.track.update) {
        this.track.update(dt);
      }

      if (this.localCar) {
        // Car Reset key [R]
        if (window.inputController.reset) {
          const cp = this.track.checkpoints[this.currentCheckpoint];
          if (cp) {
            const rotY = Math.atan2(cp.tangent.x, cp.tangent.z);
            this.localCar.resetPosition(cp.pos.x, 0, cp.pos.z, rotY);
          }
          window.inputController.reset = false;
        }

        this.localCar.update(dt, window.inputController);
        this.track.constrainCarToTrack(this.localCar);

        // Check Nitro & Obstacles interactions
        if (this.state === 'RACING') {
          const interactions = this.track.checkCarInteractions(this.localCar);
          if (interactions && interactions.length > 0) {
            interactions.forEach(inter => {
              if (inter.type === 'nitro') {
                const added = this.localCar.collectNitro();
                if (window.soundEngine) window.soundEngine.playCheckpoint();
                if (added) {
                  this.showHudAlert(`⚡ NITRO OLINDI! (${this.localCar.nitroCharges}/${this.localCar.maxNitroCharges}) [SHIFT / 🚀]`, 'nitro');
                } else {
                  this.showHudAlert('⚡ NITRO TO\'LIQ! [SHIFT / 🚀]', 'nitro');
                }
              } else if (inter.type === 'obstacle') {
                this.localCar.applyObstacleHit();
                if (window.soundEngine) window.soundEngine.playCrash();
                this.showHudAlert('⚠️ TO\'SIQ YORIB O\'TDI!', 'obstacle');
                this.cameraShake = 0.8;
                const impactEl = document.getElementById('impact-blur-fx');
                if (impactEl) {
                  impactEl.classList.remove('trigger');
                  void impactEl.offsetWidth; // Reflow to replay animation
                  impactEl.classList.add('trigger');
                }
              } else if (inter.type === 'oil') {
                this.localCar.applyOilSlick();
                if (window.soundEngine) window.soundEngine.playOilSpin();
                this.showHudAlert('🛢️ MOY TO\'SIQ! SIRPANISH', 'oil');
                this.cameraShake = 0.7;
                const oilEl = document.getElementById('oil-blur-fx');
                if (oilEl) {
                  oilEl.classList.remove('trigger');
                  void oilEl.offsetWidth; // Reflow
                  oilEl.classList.add('trigger');
                }
              }
            });
          }

          // Wind Noise audio updates
          if (window.soundEngine) {
            const speedRatio = Math.abs(this.localCar.speed) / this.localCar.maxSpeed;
            window.soundEngine.updateWind(speedRatio);
          }
        }

        // Checkpoint & Lap Detection
        if (this.state === 'RACING') {
          const cpResult = this.track.checkCheckpointProgress(
            { x: this.localCar.x, z: this.localCar.z },
            this.currentCheckpoint
          );

          if (cpResult.passed) {
            this.currentCheckpoint = cpResult.newIndex;
            if (window.soundEngine) window.soundEngine.playCheckpoint();

            if (cpResult.isLapComplete) {
              const currentLapTime = now - this.lapStartTime;
              if (currentLapTime < this.bestLapTime) {
                this.bestLapTime = currentLapTime;
              }
              this.lapStartTime = now;

              if (this.currentLap >= this.lapsTotal) {
                // Completed final lap!
                this.totalRaceTime = now - this.raceStartTime;
                this.state = 'FINISHED';
                window.inputController.lock();
                if (this.localCar) {
                  this.localCar.speed = 0;
                  this.localCar.isNitro = false;
                }

                this.showHudAlert('🏁 FINISH! POYGA YAKUNLANDI!', 'nitro');
                window.networkManager.sendRaceFinish(this.totalRaceTime, this.bestLapTime);

                this.onRaceFinish({
                  isWinner: true,
                  rank: 1,
                  totalTime: this.totalRaceTime,
                  bestLap: this.bestLapTime,
                  isSolo: this.isSolo
                });
                return;
              } else {
                this.currentLap++;
                this.showHudAlert(`🚩 DAVRA ${this.currentLap}/${this.lapsTotal}!`, 'nitro');
              }
            }

            window.networkManager.sendCheckpointPass(this.currentCheckpoint, this.currentLap);
          }
        }

        // Network telemetry relay (25Hz)
        if (this.state === 'RACING' && !this.isSolo && (now - this.lastNetSendTime >= this.netSendInterval * 1000)) {
          this.lastNetSendTime = now;
          window.networkManager.sendCarUpdate([
            Math.round(this.localCar.x * 100) / 100,
            Math.round(this.localCar.y * 100) / 100,
            Math.round(this.localCar.z * 100) / 100,
            Math.round(this.localCar.rotY * 1000) / 1000,
            Math.round(this.localCar.steerAngle * 100) / 100,
            Math.round(this.localCar.speed * 10) / 10,
            this.localCar.isDrifting ? 1 : 0,
            this.localCar.isNitro ? 1 : 0
          ]);
        }
      }

      if (this.remoteCar) {
        this.remoteCar.update(dt, null);
      }

      // Smooth Dynamic Chase Camera
      if (this.localCar) {
        const carX = this.localCar.x;
        const carZ = this.localCar.z;
        const rotY = this.localCar.rotY;

        // Camera distance & height with speed dynamic FOV
        const speedRatio = Math.abs(this.localCar.speed) / this.localCar.maxSpeed;
        const camDistance = 8.5 + speedRatio * 1.5;
        const camHeight = 3.6 + speedRatio * 0.5;

        const targetCamX = carX - Math.sin(rotY) * camDistance;
        const targetCamZ = carZ - Math.cos(rotY) * camDistance;
        const targetCamY = camHeight;

        // Smooth camera damping
        const camLerp = Math.min(1.0, 10.0 * dt);
        this.camera.position.x += (targetCamX - this.camera.position.x) * camLerp;
        this.camera.position.y += (targetCamY - this.camera.position.y) * camLerp;
        this.camera.position.z += (targetCamZ - this.camera.position.z) * camLerp;

        // Look slightly ahead of car
        const lookAhead = 7.0;
        const lookTarget = new THREE.Vector3(
          carX + Math.sin(rotY) * lookAhead,
          0.8,
          carZ + Math.cos(rotY) * lookAhead
        );
        this.camera.lookAt(lookTarget);

        // Apply camera shake if any
        if (this.cameraShake > 0) {
          const shakeAmp = this.cameraShake * 0.45;
          this.camera.position.x += (Math.random() - 0.5) * shakeAmp;
          this.camera.position.y += (Math.random() - 0.5) * shakeAmp;
          this.camera.position.z += (Math.random() - 0.5) * shakeAmp;
          this.cameraShake = Math.max(0, this.cameraShake - dt * 3.0);
        }

        // Speed dynamic FOV (widened during Nitro for warp sensation)
        const baseFov = this.localCar.isNitro ? 78 : 60;
        const targetFov = baseFov + speedRatio * 14;
        this.camera.fov += (targetFov - this.camera.fov) * 6.0 * dt;
        this.camera.updateProjectionMatrix();
      }

      // Update HUD Elements
      this.updateHUD();
    }

    this.renderer.render(this.scene, this.camera);
  }

  showHudAlert(text, type) {
    const alertEl = document.getElementById('hud-alert-banner');
    if (!alertEl) return;
    alertEl.textContent = text;
    alertEl.className = `hud-alert-banner active ${type}`;
    if (this.alertTimeout) clearTimeout(this.alertTimeout);
    this.alertTimeout = setTimeout(() => {
      alertEl.className = 'hud-alert-banner hidden';
    }, 1400);
  }

  updateHUD() {
    if (!this.localCar) return;

    // Speedometer
    const speedKmh = Math.round(Math.abs(this.localCar.speed * 3.6));
    const speedEl = document.getElementById('hud-speed-val');
    const gearEl = document.getElementById('hud-gear-val');
    if (speedEl) speedEl.textContent = speedKmh;

    if (gearEl) {
      if (this.localCar.speed < -0.5) gearEl.textContent = 'GEAR: R';
      else if (this.localCar.isNitro) gearEl.textContent = 'NITRO 🔥';
      else if (speedKmh < 4) gearEl.textContent = 'GEAR: N';
      else if (speedKmh < 42) gearEl.textContent = 'GEAR: 1';
      else if (speedKmh < 82) gearEl.textContent = 'GEAR: 2';
      else if (speedKmh < 125) gearEl.textContent = 'GEAR: 3';
      else if (speedKmh < 175) gearEl.textContent = 'GEAR: 4';
      else gearEl.textContent = 'GEAR: 5';
    }

    // Nitro Gauge & Controls State
    const nitroFill = document.getElementById('hud-nitro-fill');
    const nitroWrap = document.getElementById('hud-nitro-wrap');
    const nitroLabel = document.getElementById('hud-nitro-label');
    const touchNitroBtn = document.getElementById('touch-nitro');

    if (this.localCar.isNitro) {
      const ratio = Math.max(0, Math.min(1.0, this.localCar.nitroTimer / this.localCar.nitroDuration));
      if (nitroFill) nitroFill.style.width = `${(ratio * 100).toFixed(1)}%`;
      if (nitroWrap) {
        nitroWrap.classList.add('active');
        nitroWrap.classList.remove('ready');
      }
      if (nitroLabel) nitroLabel.textContent = '🔥 NITRO BOOSTER!';
      if (touchNitroBtn) {
        touchNitroBtn.classList.remove('ready');
        touchNitroBtn.classList.add('active');
      }
    } else {
      const ratio = this.localCar.nitroCharges / this.localCar.maxNitroCharges;
      if (nitroFill) nitroFill.style.width = `${(ratio * 100).toFixed(1)}%`;
      if (nitroWrap) {
        nitroWrap.classList.remove('active');
        if (this.localCar.nitroCharges > 0) nitroWrap.classList.add('ready');
        else nitroWrap.classList.remove('ready');
      }
      if (nitroLabel) {
        nitroLabel.textContent = this.localCar.nitroCharges > 0
          ? `⚡ NITRO (${this.localCar.nitroCharges}/${this.localCar.maxNitroCharges}) [SHIFT / 🚀]`
          : `⚡ NITRO (0/${this.localCar.maxNitroCharges}) [PADLARDAN OLING]`;
      }
      if (touchNitroBtn) {
        touchNitroBtn.classList.remove('active');
        if (this.localCar.nitroCharges > 0) touchNitroBtn.classList.add('ready');
        else touchNitroBtn.classList.remove('ready');
      }
    }

    // Lap Badge
    const lapEl = document.getElementById('hud-lap-badge');
    if (lapEl) {
      lapEl.textContent = `LAP ${Math.min(this.currentLap, this.lapsTotal)} / ${this.lapsTotal}`;
    }

    // Position Calculation (1st vs 2nd)
    const posBadge = document.getElementById('hud-position-badge');
    if (posBadge) {
      if (this.isSolo) {
        posBadge.textContent = 'SOLO';
      } else {
        const myScore = this.currentLap * 100 + this.currentCheckpoint;
        const oppScore = this.opponentLap * 100 + this.opponentCheckpoint;
        const isFirst = myScore >= oppScore;
        posBadge.textContent = isFirst ? '1ST' : '2ND';
        posBadge.style.color = isFirst ? '#ffbe0b' : '#00f0ff';
        posBadge.style.borderColor = isFirst ? '#ffbe0b' : '#00f0ff';
      }
    }

    // Render Minimap
    const mapCanvas = document.getElementById('minimap-canvas');
    if (mapCanvas && this.track) {
      this.track.renderMinimap(mapCanvas, this.localCar, this.remoteCar);
    }
  }
}

// Bootstrap on DOM Load
window.addEventListener('DOMContentLoaded', () => {
  window.gameApp = new GameApp();
  window.networkManager.connect();
});
