/**
 * APEX SPEED 3D - Procedural Low-Poly Car & Arcade Physics Engine
 * Client-side physics with smooth visual effects (headlights, brake glow, drift smoke, steering wheels)
 */

class Car {
  constructor(scene, color = 'red', isRemote = false, carType = 'hypercar') {
    this.scene = scene;
    this.color = color;
    this.isRemote = isRemote;
    this.carType = carType || 'hypercar';

    // Physics parameters tailored by vehicle archetype
    this.x = 0;
    this.y = 0;
    this.z = 0;
    this.rotY = 0; // Heading angle in radians
    this.speed = 0; // Current velocity
    this.steerAngle = 0; // Front wheel steer angle

    if (this.carType === 'muscle') {
      this.baseMaxSpeed = 43; // High torque American V8
      this.nitroMaxSpeed = 62;
      this.accel = 29;
      this.brakeDecel = 30;
      this.drag = 6.2;
      this.maxSteer = 0.52;
      this.steerSpeed = 3.2;
    } else if (this.carType === 'truck') {
      this.baseMaxSpeed = 40; // Heavy Armored Cyber-Truck
      this.nitroMaxSpeed = 58;
      this.accel = 22;
      this.brakeDecel = 35;
      this.drag = 5.6;
      this.maxSteer = 0.48;
      this.steerSpeed = 2.9;
    } else if (this.carType === 'formula') {
      this.baseMaxSpeed = 48; // Apex Formula 1
      this.nitroMaxSpeed = 68;
      this.accel = 31;
      this.brakeDecel = 38;
      this.drag = 6.6;
      this.maxSteer = 0.65;
      this.steerSpeed = 4.3;
    } else {
      // Hypercar (Balanced Apex GT)
      this.baseMaxSpeed = 45;
      this.nitroMaxSpeed = 65;
      this.accel = 25;
      this.brakeDecel = 32;
      this.drag = 6.0;
      this.maxSteer = 0.55;
      this.steerSpeed = 3.5;
    }

    this.maxSpeed = this.baseMaxSpeed;
    this.isDrifting = false;
    this.driftFactor = 0;

    // Nitro & Obstacle state
    this.nitroCharges = 1; // 1 starting charge ready to boost!
    this.maxNitroCharges = 3;
    this.nitroTimer = 0;
    this.nitroDuration = 2.5; // 2.5s duration
    this.isNitro = false;
    this.oilSpinTimer = 0;
    this.oilCooldown = 0;
    this.flameL = null;
    this.flameR = null;

    // Suspension tilts
    this.pitch = 0;
    this.roll = 0;

    // Remote interpolation buffer
    this.targetX = 0;
    this.targetY = 0;
    this.targetZ = 0;
    this.targetRotY = 0;
    this.targetSteer = 0;
    this.targetSpeed = 0;

    // Particle system for drift smoke & exhaust
    this.particles = [];

    // Create 3D Mesh
    this.mesh = this.createCarMesh(color);
    this.scene.add(this.mesh);
  }

  createCarMesh(colorType) {
    const carGroup = new THREE.Group();

    // Color definitions
    const isRed = colorType === 'red';
    const primaryColor = isRed ? 0xe6223b : 0x00d2ff;
    const accentColor = isRed ? 0xff6b08 : 0x0066ff;
    const glassColor = 0x111c2e;

    // Materials
    const bodyMat = new THREE.MeshStandardMaterial({
      color: primaryColor,
      roughness: 0.3,
      metalness: 0.6
    });

    const accentMat = new THREE.MeshStandardMaterial({
      color: accentColor,
      roughness: 0.4,
      metalness: 0.4
    });

    const darkMat = new THREE.MeshStandardMaterial({
      color: 0x181a20,
      roughness: 0.7,
      metalness: 0.2
    });

    const glassMat = new THREE.MeshStandardMaterial({
      color: glassColor,
      roughness: 0.1,
      metalness: 0.9,
      transparent: true,
      opacity: 0.85
    });

    const chromeMat = new THREE.MeshStandardMaterial({
      color: 0xdde4f0,
      roughness: 0.2,
      metalness: 0.8
    });

    // BUILD VEHICLE BODY ARCHETYPE
    if (this.carType === 'muscle') {
      // 1. Muscle Car: Boxy low chassis, bulging hood blower, rear ducktail spoiler
      const chassis = new THREE.Mesh(new THREE.BoxGeometry(1.86, 0.5, 4.1), bodyMat);
      chassis.position.y = 0.48;
      carGroup.add(chassis);

      // Chrome Bumper
      const bumperF = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.22, 0.4), chromeMat);
      bumperF.position.set(0, 0.28, 2.05);
      carGroup.add(bumperF);

      // Supercharger Hood Blower
      const blower = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.3, 0.9), chromeMat);
      blower.position.set(0, 0.82, 0.9);
      carGroup.add(blower);

      const airIntakes = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.7, 8), darkMat);
      airIntakes.rotation.z = Math.PI / 2;
      airIntakes.position.set(0, 0.92, 1.35);
      carGroup.add(airIntakes);

      // Cabin (Fastback muscle profile)
      const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.52, 1.8), glassMat);
      cabin.position.set(0, 0.9, -0.2);
      carGroup.add(cabin);

      const roof = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.08, 1.3), bodyMat);
      roof.position.set(0, 1.18, -0.3);
      carGroup.add(roof);

      // Ducktail spoiler
      const ducktail = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.18, 0.25), accentMat);
      ducktail.position.set(0, 0.8, -1.95);
      ducktail.rotation.x = -0.25;
      carGroup.add(ducktail);

    } else if (this.carType === 'truck') {
      // 2. Cyber-Truck: Angular armored SUV, high stance, roof rally lightbar
      const chassis = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.6, 4.3), bodyMat);
      chassis.position.y = 0.55;
      carGroup.add(chassis);

      // Heavy Bullbar Bumper
      const bullbar = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.35, 0.5), darkMat);
      bullbar.position.set(0, 0.35, 2.15);
      carGroup.add(bullbar);

      // Angular Cabin & Slanted Bed
      const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.65, 2.0), glassMat);
      cabin.position.set(0, 1.05, 0.0);
      carGroup.add(cabin);

      const roof = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.1, 1.8), bodyMat);
      roof.position.set(0, 1.4, -0.1);
      carGroup.add(roof);

      // Roof Rally LED Lightbar
      const lightbar = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.12, 0.2), new THREE.MeshBasicMaterial({ color: 0xffff00 }));
      lightbar.position.set(0, 1.5, 0.5);
      carGroup.add(lightbar);

      // Open truck bed walls
      const bedWallL = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.4, 1.5), bodyMat);
      bedWallL.position.set(-0.85, 0.95, -1.3);
      const bedWallR = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.4, 1.5), bodyMat);
      bedWallR.position.set(0.85, 0.95, -1.3);
      carGroup.add(bedWallL);
      carGroup.add(bedWallR);

    } else if (this.carType === 'formula') {
      // 3. Formula Racer: Open cockpit, needle nosecone, front dual-tier wing, giant rear wing
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.35, 3.8), bodyMat);
      body.position.y = 0.38;
      carGroup.add(body);

      // Nosecone
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.2, 4), accentMat);
      nose.rotation.x = Math.PI / 2;
      nose.position.set(0, 0.35, 2.3);
      carGroup.add(nose);

      // Front Aerodynamic Wing
      const frontWing = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.06, 0.5), accentMat);
      frontWing.position.set(0, 0.18, 2.35);
      carGroup.add(frontWing);

      // Open Cockpit with Driver Helmet & Halo Bar
      const cockpit = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.25, 0.9), darkMat);
      cockpit.position.set(0, 0.55, 0.1);
      carGroup.add(cockpit);

      const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.2, 8, 8), new THREE.MeshStandardMaterial({ color: 0xffee00, metalness: 0.8 }));
      helmet.position.set(0, 0.72, 0.05);
      carGroup.add(helmet);

      const halo = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.04, 6, 12), darkMat);
      halo.rotation.x = Math.PI / 2;
      halo.position.set(0, 0.76, 0.12);
      carGroup.add(halo);

      // Engine Airbox Intake behind driver
      const airbox = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.4, 0.8), bodyMat);
      airbox.position.set(0, 0.75, -0.6);
      carGroup.add(airbox);

      // Giant High Rear Wing
      const rearWing = new THREE.Mesh(new THREE.BoxGeometry(1.85, 0.08, 0.5), accentMat);
      rearWing.position.set(0, 1.15, -1.9);
      carGroup.add(rearWing);

      const strutL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.6, 0.2), darkMat);
      strutL.position.set(-0.55, 0.85, -1.85);
      const strutR = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.6, 0.2), darkMat);
      strutR.position.set(0.55, 0.85, -1.85);
      carGroup.add(strutL);
      carGroup.add(strutR);

    } else {
      // Default: Hypercar (Apex GT)
      const chassisGeo = new THREE.BoxGeometry(1.8, 0.45, 4.0);
      const chassis = new THREE.Mesh(chassisGeo, bodyMat);
      chassis.position.y = 0.45;
      carGroup.add(chassis);

      const bumperGeo = new THREE.BoxGeometry(1.82, 0.2, 0.6);
      const bumper = new THREE.Mesh(bumperGeo, darkMat);
      bumper.position.set(0, 0.25, 2.05);
      carGroup.add(bumper);

      const hoodGeo = new THREE.BoxGeometry(1.4, 0.15, 1.4);
      const hood = new THREE.Mesh(hoodGeo, accentMat);
      hood.position.set(0, 0.68, 0.9);
      carGroup.add(hood);

      const cabinGeo = new THREE.BoxGeometry(1.4, 0.55, 1.9);
      const cabin = new THREE.Mesh(cabinGeo, glassMat);
      cabin.position.set(0, 0.88, -0.2);
      carGroup.add(cabin);

      const roofGeo = new THREE.BoxGeometry(1.3, 0.08, 1.4);
      const roof = new THREE.Mesh(roofGeo, bodyMat);
      roof.position.set(0, 1.18, -0.3);
      carGroup.add(roof);

      const wingGeo = new THREE.BoxGeometry(1.9, 0.08, 0.4);
      const wing = new THREE.Mesh(wingGeo, accentMat);
      wing.position.set(0, 1.05, -1.9);
      wing.rotation.x = -0.05;
      carGroup.add(wing);

      const strutGeo = new THREE.BoxGeometry(0.08, 0.4, 0.15);
      const strutL = new THREE.Mesh(strutGeo, darkMat);
      strutL.position.set(-0.6, 0.85, -1.88);
      const strutR = new THREE.Mesh(strutGeo, darkMat);
      strutR.position.set(0.6, 0.85, -1.88);
      carGroup.add(strutL);
      carGroup.add(strutR);
    }

    // 4. Headlights (with real light illumination on track)
    const lightMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const headlightL = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.12, 0.05), lightMat);
    headlightL.position.set(-0.65, 0.5, 2.02);
    const headlightR = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.12, 0.05), lightMat);
    headlightR.position.set(0.65, 0.5, 2.02);
    carGroup.add(headlightL);
    carGroup.add(headlightR);

    // Front spot projector
    const headSpot = new THREE.SpotLight(0xffffff, 1.5, 30, Math.PI / 5, 0.4);
    headSpot.position.set(0, 0.6, 2.1);
    headSpot.target.position.set(0, 0, 12);
    carGroup.add(headSpot);
    carGroup.add(headSpot.target);

    // 5. Taillights (glows brighter when braking)
    this.taillightMat = new THREE.MeshBasicMaterial({ color: 0xaa0022 });
    const taillightL = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.1, 0.05), this.taillightMat);
    taillightL.position.set(-0.6, 0.55, -2.02);
    const taillightR = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.1, 0.05), this.taillightMat);
    taillightR.position.set(0.6, 0.55, -2.02);
    carGroup.add(taillightL);
    carGroup.add(taillightR);

    // 6. Dual Exhausts
    const exhaustGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.2, 8);
    const exhaustL = new THREE.Mesh(exhaustGeo, chromeMat);
    exhaustL.rotation.x = Math.PI / 2;
    exhaustL.position.set(-0.4, 0.25, -2.05);
    const exhaustR = new THREE.Mesh(exhaustGeo, chromeMat);
    exhaustR.rotation.x = Math.PI / 2;
    exhaustR.position.set(0.4, 0.25, -2.05);
    carGroup.add(exhaustL);
    carGroup.add(exhaustR);

    // Nitro Jet Turbo Flames
    const flameGeo = new THREE.ConeGeometry(0.12, 0.7, 6);
    flameGeo.rotateX(-Math.PI / 2);
    flameGeo.translate(0, 0, -0.35);
    const flameMatL = new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.9 });
    const flameMatR = new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.9 });

    this.flameL = new THREE.Mesh(flameGeo, flameMatL);
    this.flameL.position.set(-0.4, 0.25, -2.15);
    this.flameL.visible = false;
    carGroup.add(this.flameL);

    this.flameR = new THREE.Mesh(flameGeo, flameMatR);
    this.flameR.position.set(0.4, 0.25, -2.15);
    this.flameR.visible = false;
    carGroup.add(this.flameR);

    // 7. Wheels & Rims
    this.wheels = [];
    const wheelRadius = 0.38;
    const wheelWidth = 0.32;
    const wheelPositions = [
      { x: -0.92, y: wheelRadius, z: 1.25, isFront: true },  // Front Left
      { x: 0.92, y: wheelRadius, z: 1.25, isFront: true },   // Front Right
      { x: -0.92, y: wheelRadius, z: -1.25, isFront: false },// Rear Left
      { x: 0.92, y: wheelRadius, z: -1.25, isFront: false }  // Rear Right
    ];

    const tireMat = new THREE.MeshStandardMaterial({
      color: 0x121418,
      roughness: 0.9,
      metalness: 0.1
    });

    const rimMat = new THREE.MeshStandardMaterial({
      color: isRed ? 0xff9100 : 0x00f0ff,
      roughness: 0.2,
      metalness: 0.9
    });

    wheelPositions.forEach((pos) => {
      // Wheel Pivot for steering
      const steerPivot = new THREE.Group();
      steerPivot.position.set(pos.x, pos.y, pos.z);

      // Wheel Axis for rolling
      const rollAxis = new THREE.Group();

      // Tire cylinder
      const tireGeo = new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelWidth, 16);
      const tire = new THREE.Mesh(tireGeo, tireMat);
      tire.rotation.z = Math.PI / 2;
      tire.castShadow = true;
      rollAxis.add(tire);

      // Rim Hub
      const rimGeo = new THREE.CylinderGeometry(wheelRadius * 0.65, wheelRadius * 0.65, wheelWidth + 0.02, 8);
      const rim = new THREE.Mesh(rimGeo, rimMat);
      rim.rotation.z = Math.PI / 2;
      rollAxis.add(rim);

      steerPivot.add(rollAxis);
      carGroup.add(steerPivot);

      this.wheels.push({
        steerPivot,
        rollAxis,
        isFront: pos.isFront,
        basePos: pos
      });
    });

    // Particle Group for Drift Smoke
    this.particleGroup = new THREE.Group();
    this.scene.add(this.particleGroup);

    return carGroup;
  }

  collectNitro() {
    if (this.nitroCharges < this.maxNitroCharges) {
      this.nitroCharges++;
      return true;
    }
    return false;
  }

  triggerNitro() {
    if (this.isNitro) return false;
    if (this.nitroCharges <= 0) return false;

    this.nitroCharges--;
    this.isNitro = true;
    this.nitroTimer = this.nitroDuration;
    this.speed = Math.max(this.speed + 16, this.baseMaxSpeed * 1.08);
    return true;
  }

  applyNitro() {
    this.triggerNitro();
  }

  applyObstacleHit() {
    // Smashes through obstacles without coming to a stop!
    const damp = this.carType === 'truck' ? 0.94 : 0.88;
    const minSpeed = this.carType === 'truck' ? 26 : 20;
    this.speed = Math.max(this.speed * damp, minSpeed);

    // Minor jolt
    this.pitch = -0.06;
    this.steerAngle *= 0.7;
  }

  applyOilSlick() {
    this.oilSpinTimer = 1.0;
    this.isDrifting = true;
    this.driftFactor = 1.0;
    this.speed = Math.max(this.speed * 0.9, 18);
  }

  spawnNitroParticle() {
    const pGeo = new THREE.SphereGeometry(0.18, 6, 6);
    const pMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.85
    });
    const p = new THREE.Mesh(pGeo, pMat);
    const offsetZ = -2.3;
    const pX = this.x - Math.sin(this.rotY) * offsetZ + (Math.random() - 0.5) * 0.5;
    const pZ = this.z - Math.cos(this.rotY) * offsetZ + (Math.random() - 0.5) * 0.5;
    p.position.set(pX, 0.25 + Math.random() * 0.2, pZ);
    this.particleGroup.add(p);
    this.particles.push({
      mesh: p,
      life: 0.25,
      maxLife: 0.25,
      growRate: 1.2
    });
  }

  resetPosition(x, y, z, rotY) {
    this.x = x;
    this.y = y;
    this.z = z;
    this.rotY = rotY;
    this.speed = 0;
    this.steerAngle = 0;
    this.pitch = 0;
    this.roll = 0;
    this.isDrifting = false;

    // Reset nitro & obstacle state
    this.nitroTimer = 0;
    this.isNitro = false;
    this.oilSpinTimer = 0;
    this.oilCooldown = 0;
    if (this.flameL) this.flameL.visible = false;
    if (this.flameR) this.flameR.visible = false;

    this.mesh.position.set(x, y, z);
    this.mesh.rotation.set(0, rotY, 0);

    this.targetX = x;
    this.targetY = y;
    this.targetZ = z;
    this.targetRotY = rotY;
  }

  update(dt, input) {
    if (this.isRemote) {
      this.updateRemoteInterpolation(dt);
      return;
    }

    // --- TIMERS UPDATE ---
    if (this.oilCooldown > 0) {
      this.oilCooldown -= dt;
    }

    if (this.nitroTimer > 0) {
      this.nitroTimer -= dt;
      this.isNitro = true;
      this.maxSpeed = this.nitroMaxSpeed;
      // High-thrust boost acceleration
      this.speed += 36 * dt;
      if (this.speed > this.maxSpeed) this.speed = this.maxSpeed;
    } else {
      this.isNitro = false;
      this.maxSpeed = this.baseMaxSpeed;
    }

    // --- LOCAL PLAYER PHYSICS ---
    const isGas = input ? input.gas : false;
    const isBrake = input ? input.brake : false;
    const isLeft = input ? input.left : false;
    const isRight = input ? input.right : false;
    const isDrift = input ? input.drift : false;
    const isNitroKey = input ? input.nitro : false;

    // Manual Nitro triggering on command
    if (isNitroKey) {
      if (this.triggerNitro()) {
        if (window.soundEngine) window.soundEngine.playNitro();
        if (window.gameApp) {
          window.gameApp.showHudAlert('🔥 NITRO ISHLATILDI! +160 KM/H', 'nitro');
          window.gameApp.cameraShake = Math.max(window.gameApp.cameraShake, 0.5);
        }
      }
    }

    // Steering input
    let targetSteer = 0;
    if (isLeft) targetSteer += this.maxSteer;
    if (isRight) targetSteer -= this.maxSteer;

    // Speed-sensitive steering (sharper at medium speed, stable at high speed)
    const speedRatio = Math.abs(this.speed) / this.maxSpeed;
    const steerFactor = 1.0 - speedRatio * 0.45;
    targetSteer *= steerFactor;

    this.steerAngle += (targetSteer - this.steerAngle) * this.steerSpeed * dt;

    // Acceleration & Braking
    if (isGas) {
      if (this.speed < 0) {
        this.speed += this.brakeDecel * dt;
      } else {
        // Power curve (enhanced during nitro)
        const powerCurve = this.isNitro ? 1.4 : Math.max(0.2, 1.0 - (this.speed / this.maxSpeed) * 0.7);
        this.speed += this.accel * powerCurve * dt;
        if (this.speed > this.maxSpeed) this.speed = this.maxSpeed;
      }
    } else if (isBrake) {
      if (this.speed > 0.5) {
        this.speed -= this.brakeDecel * dt;
      } else {
        // Reverse
        this.speed -= this.accel * 0.6 * dt;
        if (this.speed < -14) this.speed = -14;
      }
    } else {
      // Natural engine brake / air resistance drag
      if (Math.abs(this.speed) < 0.2) {
        this.speed = 0;
      } else {
        const dragDir = Math.sign(this.speed);
        this.speed -= dragDir * this.drag * dt;
      }
    }

    // Drift / Handbrake logic (forced during oil slick)
    if (this.oilSpinTimer > 0) {
      this.oilSpinTimer -= dt;
      this.isDrifting = true;
      this.driftFactor = 1.0;
      this.rotY += Math.sin(this.oilSpinTimer * 14) * 2.2 * dt;
    } else {
      this.isDrifting = (isDrift && Math.abs(this.speed) > 12) || (Math.abs(this.steerAngle) > 0.4 && speedRatio > 0.75);
      if (this.isDrifting) {
        this.driftFactor = Math.min(1.0, this.driftFactor + dt * 4.0);
        // Slight speed bleed during heavy drift
        this.speed -= Math.sign(this.speed) * 4.0 * dt;
      } else {
        this.driftFactor = Math.max(0.0, this.driftFactor - dt * 5.0);
      }
    }

    // Vehicle heading rotation
    if (Math.abs(this.speed) > 0.1) {
      const turnMultiplier = 1.0 + this.driftFactor * 0.6;
      const turnRate = this.steerAngle * (this.speed / 14) * turnMultiplier;
      this.rotY += turnRate * dt;
    }

    // Forward displacement with drift slide vector
    const forwardX = Math.sin(this.rotY);
    const forwardZ = Math.cos(this.rotY);

    this.x += forwardX * this.speed * dt;
    this.z += forwardZ * this.speed * dt;

    // Taillights brake glow
    if (this.taillightMat) {
      if (isBrake && this.speed > 0) {
        this.taillightMat.color.setHex(0xff0033);
      } else {
        this.taillightMat.color.setHex(0x550011);
      }
    }

    // Nitro exhaust flames
    if (this.flameL && this.flameR) {
      if (this.isNitro) {
        this.flameL.visible = true;
        this.flameR.visible = true;
        const flk = 0.85 + Math.random() * 0.45;
        this.flameL.scale.set(flk, flk, flk * 1.5);
        this.flameR.scale.set(flk, flk, flk * 1.5);
        if (Math.random() < 0.6) {
          this.spawnNitroParticle();
        }
      } else {
        this.flameL.visible = false;
        this.flameR.visible = false;
      }
    }

    // Suspension tilts (pitch on accel/brake, roll on cornering)
    const targetPitch = isGas ? -0.04 : (isBrake ? 0.06 : 0.0);
    const targetRoll = -this.steerAngle * speedRatio * 0.15;
    this.pitch += (targetPitch - this.pitch) * 6.0 * dt;
    this.roll += (targetRoll - this.roll) * 6.0 * dt;

    // Update 3D transforms
    this.mesh.position.set(this.x, this.y, this.z);
    this.mesh.rotation.set(this.pitch, this.rotY, this.roll);

    // Animate wheels
    this.animateWheels(dt);

    // Spawn drift smoke
    if (this.isDrifting && Math.abs(this.speed) > 10) {
      this.spawnDriftSmoke();
    }

    this.updateParticles(dt);

    // Audio update
    if (window.soundEngine) {
      window.soundEngine.updateEngine(this.speed, this.maxSpeed, isGas);
      window.soundEngine.setTireScreech(this.isDrifting, speedRatio);
    }
  }

  animateWheels(dt) {
    const rollSpeed = (this.speed / 0.38) * dt; // radians = v / r
    this.wheels.forEach(w => {
      // Steer front wheels
      if (w.isFront) {
        w.steerPivot.rotation.y = this.steerAngle;
      }
      // Roll wheels
      w.rollAxis.rotation.x += rollSpeed;
    });
  }

  // Smooth client-side dead-reckoning interpolation for remote opponent car
  setRemoteState(x, y, z, rotY, steer, speed, isDrift, isNitro) {
    // If car resets or teleports (> 18m), snap directly to avoid dragging across the world
    const distSq = (x - this.x) * (x - this.x) + (z - this.z) * (z - this.z);
    if (distSq > 324 || isNaN(this.x)) {
      this.x = x;
      this.y = y;
      this.z = z;
      this.rotY = rotY;
    }

    this.targetX = x;
    this.targetY = y;
    this.targetZ = z;
    this.targetRotY = rotY;
    this.targetSteer = steer || 0;
    this.targetSpeed = speed || 0;
    this.isDrifting = !!isDrift;
    this.isNitro = !!isNitro;
  }

  updateRemoteInterpolation(dt) {
    // Continuous Predictive Dead-Reckoning: keep moving target forward along heading
    if (Math.abs(this.targetSpeed) > 0.1) {
      this.targetX += Math.sin(this.targetRotY) * this.targetSpeed * dt;
      this.targetZ += Math.cos(this.targetRotY) * this.targetSpeed * dt;
    }

    // Exponential smoothing towards predicted target
    const posLerp = Math.min(1.0, 10.0 * dt);
    this.x += (this.targetX - this.x) * posLerp;
    this.y += (this.targetY - this.y) * posLerp;
    this.z += (this.targetZ - this.z) * posLerp;

    // Shortest-angle interpolation for rotation
    let angleDiff = (this.targetRotY - this.rotY) % (Math.PI * 2);
    if (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
    if (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
    this.rotY += angleDiff * Math.min(1.0, 12.0 * dt);

    this.steerAngle += (this.targetSteer - this.steerAngle) * Math.min(1.0, 8.0 * dt);
    this.speed += (this.targetSpeed - this.speed) * Math.min(1.0, 8.0 * dt);

    this.mesh.position.set(this.x, this.y, this.z);
    this.mesh.rotation.set(0, this.rotY, 0);

    // Remote flames
    if (this.flameL && this.flameR) {
      if (this.isNitro) {
        this.flameL.visible = true;
        this.flameR.visible = true;
        const flk = 0.85 + Math.random() * 0.45;
        this.flameL.scale.set(flk, flk, flk * 1.5);
        this.flameR.scale.set(flk, flk, flk * 1.5);
      } else {
        this.flameL.visible = false;
        this.flameR.visible = false;
      }
    }

    this.animateWheels(dt);

    if (this.isDrifting && Math.abs(this.speed) > 10) {
      this.spawnDriftSmoke();
    }
    this.updateParticles(dt);
  }

  spawnDriftSmoke() {
    // Create smoke puff behind rear tires
    const smokeGeo = new THREE.SphereGeometry(0.25, 6, 6);
    const smokeMat = new THREE.MeshBasicMaterial({
      color: 0xcccccc,
      transparent: true,
      opacity: 0.5
    });

    const puff = new THREE.Mesh(smokeGeo, smokeMat);
    // Position near rear tires
    const offsetZ = -1.2;
    const puffX = this.x - Math.sin(this.rotY) * offsetZ + (Math.random() - 0.5) * 0.8;
    const puffZ = this.z - Math.cos(this.rotY) * offsetZ + (Math.random() - 0.5) * 0.8;

    puff.position.set(puffX, 0.2, puffZ);
    this.particleGroup.add(puff);

    this.particles.push({
      mesh: puff,
      life: 0.5, // 0.5 second lifetime
      maxLife: 0.5,
      growRate: 1.8
    });
  }

  updateParticles(dt) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life -= dt;
      if (p.life <= 0) {
        this.particleGroup.remove(p.mesh);
        p.mesh.geometry.dispose();
        p.mesh.material.dispose();
        this.particles.splice(i, 1);
      } else {
        const scale = 1.0 + (1.0 - p.life / p.maxLife) * p.growRate;
        p.mesh.scale.set(scale, scale, scale);
        p.mesh.material.opacity = (p.life / p.maxLife) * 0.4;
        p.mesh.position.y += dt * 0.8;
      }
    }
  }

  dispose() {
    if (this.mesh) this.scene.remove(this.mesh);
    if (this.particleGroup) this.scene.remove(this.particleGroup);
    this.particles.forEach(p => {
      p.mesh.geometry.dispose();
      p.mesh.material.dispose();
    });
    this.particles = [];
  }
}

window.Car = Car;
