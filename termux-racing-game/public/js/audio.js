/**
 * APEX SPEED 3D - Web Audio Synthesizer
 * Zero audio assets needed - 100% procedurally synthesized in browser
 */

class SoundEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
    this.engineOsc = null;
    this.engineGain = null;
    this.screechNode = null;
    this.screechGain = null;
    this.initialized = false;
  }

  init() {
    if (this.initialized) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();
      this.initEngineSound();
      this.initTireScreech();
      this.initialized = true;
    } catch (e) {
      console.warn('Web Audio not supported or blocked:', e);
    }
  }

  unlock() {
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  initEngineSound() {
    if (!this.ctx) return;
    
    // Primary Sawtooth Engine Tone
    this.engineOsc = this.ctx.createOscillator();
    this.engineOsc.type = 'sawtooth';
    this.engineOsc.frequency.value = 55; // Idle RPM

    // Sub-harmonic Triangle for deep growl & throttle resonance
    this.engineSubOsc = this.ctx.createOscillator();
    this.engineSubOsc.type = 'triangle';
    this.engineSubOsc.frequency.value = 27.5; // One octave lower

    // Dynamic Low-Pass Filter (opens up on throttle)
    this.engineFilter = this.ctx.createBiquadFilter();
    this.engineFilter.type = 'lowpass';
    this.engineFilter.frequency.value = 400;

    // Master Engine Gain
    this.engineGain = this.ctx.createGain();
    this.engineGain.gain.value = 0.0; // Starts quiet

    this.engineOsc.connect(this.engineFilter);
    this.engineSubOsc.connect(this.engineFilter);
    this.engineFilter.connect(this.engineGain);
    this.engineGain.connect(this.ctx.destination);

    this.engineOsc.start();
    this.engineSubOsc.start();

    this.currentGear = 1;
    this.lastGear = 1;
  }

  initTireScreech() {
    if (!this.ctx) return;
    const bufferSize = this.ctx.sampleRate * 2;
    const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    const bandpass = this.ctx.createBiquadFilter();
    bandpass.type = 'bandpass';
    bandpass.frequency.value = 1200;
    bandpass.Q.value = 3.0;

    this.screechGain = this.ctx.createGain();
    this.screechGain.gain.value = 0.0;

    whiteNoise.connect(bandpass);
    bandpass.connect(this.screechGain);
    this.screechGain.connect(this.ctx.destination);

    whiteNoise.start();
  }

  updateEngine(speed, maxSpeed, isAccelerating) {
    if (!this.enabled || !this.initialized || !this.engineOsc || !this.ctx) return;

    const speedKmh = Math.abs(speed * 3.6);
    
    // 5-Gear Transmission Simulation
    const gearTiers = [
      { gear: 1, min: 0,   max: 42,  minRpm: 55,  maxRpm: 160 },
      { gear: 2, min: 38,  max: 82,  minRpm: 75,  maxRpm: 170 },
      { gear: 3, min: 76,  max: 125, minRpm: 88,  maxRpm: 180 },
      { gear: 4, min: 118, max: 175, minRpm: 98,  maxRpm: 195 },
      { gear: 5, min: 168, max: 280, minRpm: 112, maxRpm: 220 }
    ];

    let activeTier = gearTiers[0];
    for (let i = gearTiers.length - 1; i >= 0; i--) {
      if (speedKmh >= gearTiers[i].min) {
        activeTier = gearTiers[i];
        break;
      }
    }

    const currentGearNum = activeTier.gear;
    const gearRange = activeTier.max - activeTier.min;
    const gearProgress = Math.max(0, Math.min(1.0, (speedKmh - activeTier.min) / gearRange));

    // Dynamic Gear Shifting: RPM rev-up then drops upon shift!
    let targetFreq = activeTier.minRpm + Math.pow(gearProgress, 1.25) * (activeTier.maxRpm - activeTier.minRpm);
    if (isAccelerating) targetFreq += 18;

    // Detect Gear Shift Event
    if (currentGearNum !== this.lastGear) {
      this.lastGear = currentGearNum;
      // Quick momentary throttle dip & gear shift pop
      if (this.engineGain && speedKmh > 20) {
        this.engineGain.gain.setValueAtTime(0.04, this.ctx.currentTime);
        this.engineGain.gain.exponentialRampToValueAtTime(0.16, this.ctx.currentTime + 0.08);
      }
    }

    // Filter Cutoff: opens wide on acceleration for an aggressive roar, drops on idle
    const filterTarget = isAccelerating
      ? 600 + gearProgress * 1200
      : 320 + gearProgress * 250;

    // Gain volume
    const targetGain = (speedKmh < 1.0)
      ? 0.05 // Soft idle rumble
      : 0.10 + Math.min(0.12, (speedKmh / 220) * 0.12);

    const now = this.ctx.currentTime;
    this.engineOsc.frequency.setTargetAtTime(targetFreq, now, 0.04);
    if (this.engineSubOsc) {
      this.engineSubOsc.frequency.setTargetAtTime(targetFreq * 0.5, now, 0.04);
    }
    this.engineFilter.frequency.setTargetAtTime(filterTarget, now, 0.06);
    this.engineGain.gain.setTargetAtTime(targetGain, now, 0.05);
  }

  stopEngine() {
    if (this.engineGain && this.ctx) {
      this.engineGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1);
    }
  }

  setTireScreech(isDrifting, speedRatio) {
    if (!this.enabled || !this.initialized || !this.screechGain) return;
    const targetGain = (isDrifting && speedRatio > 0.3) ? 0.15 : 0.0;
    this.screechGain.gain.setTargetAtTime(targetGain, this.ctx.currentTime, 0.04);
  }

  playCountdown(count) {
    if (!this.enabled || !this.ctx) return;
    this.unlock();

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    if (count > 0) {
      // 3, 2, 1 tone
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, this.ctx.currentTime); // A4
      gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.3);
    } else {
      // GO tone
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(880, this.ctx.currentTime); // A5 high
      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.6);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.6);
    }
  }

  playCheckpoint() {
    if (!this.enabled || !this.ctx) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, this.ctx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880, this.ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.2);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.2);
  }

  playWin() {
    if (!this.enabled || !this.ctx) return;
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C E G C
    notes.forEach((freq, i) => {
      setTimeout(() => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.4);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.4);
      }, i * 140);
    });
  }

  playNitro() {
    if (!this.enabled || !this.ctx) return;
    this.unlock();
    const t = this.ctx.currentTime;

    // 1. Sci-fi synth power surge
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(240, t);
    osc.frequency.exponentialRampToValueAtTime(960, t + 0.45);

    gain.gain.setValueAtTime(0.3, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.6);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.6);

    // 2. High-speed whoosh / turbine noise
    try {
      const bufferSize = Math.floor(this.ctx.sampleRate * 0.55);
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(900, t);
      filter.frequency.exponentialRampToValueAtTime(3600, t + 0.35);
      filter.Q.value = 2.5;

      const nGain = this.ctx.createGain();
      nGain.gain.setValueAtTime(0.4, t);
      nGain.gain.exponentialRampToValueAtTime(0.001, t + 0.55);

      noise.connect(filter);
      filter.connect(nGain);
      nGain.connect(this.ctx.destination);
      noise.start(t);
    } catch (e) {}
  }

  playCrash() {
    if (!this.enabled || !this.ctx) return;
    this.unlock();
    const t = this.ctx.currentTime;

    // Heavy bass thud
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(180, t);
    osc.frequency.exponentialRampToValueAtTime(35, t + 0.35);

    gain.gain.setValueAtTime(0.45, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.4);

    // Impact crunch noise
    try {
      const bufferSize = Math.floor(this.ctx.sampleRate * 0.3);
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.25));
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buffer;
      const nGain = this.ctx.createGain();
      nGain.gain.setValueAtTime(0.35, t);
      nGain.gain.exponentialRampToValueAtTime(0.01, t + 0.3);
      noise.connect(nGain);
      nGain.connect(this.ctx.destination);
      noise.start(t);
    } catch (e) {}
  }

  playOilSpin() {
    if (!this.enabled || !this.ctx) return;
    this.unlock();
    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(550, t);
    osc.frequency.linearRampToValueAtTime(320, t + 0.2);
    osc.frequency.linearRampToValueAtTime(680, t + 0.4);
    osc.frequency.linearRampToValueAtTime(220, t + 0.65);

    gain.gain.setValueAtTime(0.22, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.65);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.65);
  }

  // ============================================================
  // PROCEDURAL ARCADE BACKGROUND MUSIC SEQUENCER (SYNTHWAVE)
  // 100% Web Audio API - Zero External Audio Files
  // ============================================================
  initMusic() {
    if (!this.ctx || this.musicMasterGain) return;
    this.musicMasterGain = this.ctx.createGain();
    this.musicMasterGain.gain.value = this.musicEnabled ? 0.22 : 0.0;
    this.musicMasterGain.connect(this.ctx.destination);

    // Speed wind noise node
    this.initSpeedWind();
  }

  initSpeedWind() {
    if (!this.ctx) return;
    const bufferSize = this.ctx.sampleRate * 2;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;

    this.windFilter = this.ctx.createBiquadFilter();
    this.windFilter.type = 'lowpass';
    this.windFilter.frequency.value = 300;

    this.windGain = this.ctx.createGain();
    this.windGain.gain.value = 0.0;

    noise.connect(this.windFilter);
    this.windFilter.connect(this.windGain);
    this.windGain.connect(this.ctx.destination);
    noise.start();
  }

  updateWind(speedRatio) {
    if (!this.enabled || !this.windGain) return;
    if (speedRatio > 0.5) {
      const vol = (speedRatio - 0.5) * 0.18;
      this.windGain.gain.setTargetAtTime(vol, this.ctx.currentTime, 0.08);
      this.windFilter.frequency.setTargetAtTime(300 + speedRatio * 800, this.ctx.currentTime, 0.08);
    } else {
      this.windGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1);
    }
  }

  startMusic() {
    this.init();
    this.initMusic();
    this.unlock();

    if (this.musicPlaying) return;
    this.musicPlaying = true;
    this.musicStep = 0;

    const stepInterval = 120; // ~125 BPM (16th notes)
    this.musicTimer = setInterval(() => this.tickMusicSequence(), stepInterval);
  }

  stopMusic() {
    this.musicPlaying = false;
    if (this.musicTimer) {
      clearInterval(this.musicTimer);
      this.musicTimer = null;
    }
  }

  toggleMusic() {
    this.musicEnabled = !this.musicEnabled;
    try {
      localStorage.setItem('apex_music', this.musicEnabled ? 'true' : 'false');
    } catch (e) {}

    if (this.musicMasterGain && this.ctx) {
      this.musicMasterGain.gain.setTargetAtTime(this.musicEnabled ? 0.22 : 0.0, this.ctx.currentTime, 0.1);
    }

    if (this.musicEnabled && !this.musicPlaying) {
      this.startMusic();
    }
    return this.musicEnabled;
  }

  tickMusicSequence() {
    if (!this.enabled || !this.ctx || !this.musicMasterGain) return;
    const t = this.ctx.currentTime;
    const step = this.musicStep % 16;
    const bar = Math.floor(this.musicStep / 16) % 4;

    // 1. Synth Bassline (Electro Drive)
    // A minor progression: Bar 0-1: A, Bar 2: F, Bar 3: G
    const bassFrequencies = [
      55.00,  // A1
      55.00,  // A1
      65.41,  // C2
      82.41,  // E2
      43.65,  // F1
      48.99   // G1
    ];
    let rootFreq = 55.00;
    if (bar === 2) rootFreq = 43.65; // F
    else if (bar === 3) rootFreq = 48.99; // G

    // Pumping 16th-note bass pattern
    if (step % 2 === 0 || step === 7 || step === 15) {
      const osc = this.ctx.createOscillator();
      const bFilter = this.ctx.createBiquadFilter();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      const octaveMult = (step === 6 || step === 14) ? 2 : 1;
      osc.frequency.setValueAtTime(rootFreq * octaveMult, t);

      bFilter.type = 'lowpass';
      bFilter.frequency.setValueAtTime(350 + (step % 4) * 150, t);
      bFilter.Q.value = 3.5;

      gain.gain.setValueAtTime(0.35, t);
      gain.gain.exponentialRampToValueAtTime(0.01, t + 0.11);

      osc.connect(bFilter);
      bFilter.connect(gain);
      gain.connect(this.musicMasterGain);

      osc.start(t);
      osc.stop(t + 0.12);
    }

    // 2. Cyberpunk Arpeggio (Upper Lead Chords)
    const arpNotes = [220, 261.63, 329.63, 392, 440, 523.25, 659.25, 783.99]; // A, C, E, G scale
    if (step % 2 === 1) {
      const noteIdx = (step + bar * 2) % arpNotes.length;
      const arpOsc = this.ctx.createOscillator();
      const arpGain = this.ctx.createGain();

      arpOsc.type = 'sine';
      arpOsc.frequency.setValueAtTime(arpNotes[noteIdx], t);

      arpGain.gain.setValueAtTime(0.12, t);
      arpGain.gain.exponentialRampToValueAtTime(0.001, t + 0.15);

      arpOsc.connect(arpGain);
      arpGain.connect(this.musicMasterGain);

      arpOsc.start(t);
      arpOsc.stop(t + 0.16);
    }

    // 3. Drums: Kick on beats 0, 4, 8, 12
    if (step % 4 === 0) {
      const kickOsc = this.ctx.createOscillator();
      const kickGain = this.ctx.createGain();

      kickOsc.type = 'sine';
      kickOsc.frequency.setValueAtTime(140, t);
      kickOsc.frequency.exponentialRampToValueAtTime(32, t + 0.15);

      kickGain.gain.setValueAtTime(0.65, t);
      kickGain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);

      kickOsc.connect(kickGain);
      kickGain.connect(this.musicMasterGain);

      kickOsc.start(t);
      kickOsc.stop(t + 0.19);
    }

    // 4. Drums: Snare / Clap on beats 4, 12
    if (step === 4 || step === 12) {
      try {
        const bufferSize = Math.floor(this.ctx.sampleRate * 0.12);
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
          data[i] = Math.random() * 2 - 1;
        }
        const sNoise = this.ctx.createBufferSource();
        sNoise.buffer = buffer;

        const sFilter = this.ctx.createBiquadFilter();
        sFilter.type = 'bandpass';
        sFilter.frequency.setValueAtTime(1400, t);
        sFilter.Q.value = 2.0;

        const sGain = this.ctx.createGain();
        sGain.gain.setValueAtTime(0.3, t);
        sGain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);

        sNoise.connect(sFilter);
        sFilter.connect(sGain);
        sGain.connect(this.musicMasterGain);

        sNoise.start(t);
      } catch (e) {}
    }

    // 5. Drums: Hi-Hat on off-beats 2, 6, 10, 14
    if (step % 2 === 0) {
      try {
        const bufferSize = Math.floor(this.ctx.sampleRate * 0.04);
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
          data[i] = Math.random() * 2 - 1;
        }
        const hNoise = this.ctx.createBufferSource();
        hNoise.buffer = buffer;

        const hFilter = this.ctx.createBiquadFilter();
        hFilter.type = 'highpass';
        hFilter.frequency.setValueAtTime(7000, t);

        const hGain = this.ctx.createGain();
        hGain.gain.setValueAtTime(step % 4 === 2 ? 0.15 : 0.08, t);
        hGain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);

        hNoise.connect(hFilter);
        hFilter.connect(hGain);
        hGain.connect(this.musicMasterGain);

        hNoise.start(t);
      } catch (e) {}
    }

    this.musicStep++;
  }
}

window.soundEngine = new SoundEngine();
