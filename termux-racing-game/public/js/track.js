/**
 * APEX SPEED 3D - Procedural 3D Race Circuit & Multi-Map Engine
 * Supports 3 Diverse Themed Tracks:
 * 1. 'neon_city'      - Cyberpunk Metropolis with skyscrapers, highway gantries & neon billboards
 * 2. 'desert_canyon'  - Red Sandstone Cliffs, natural stone arches & desert sunset mesas
 * 3. 'arctic_glacier' - Crystalline Ice Spire Peaks, frozen road & aurora atmosphere
 */

class RaceTrack {
  constructor(scene, trackId = 'neon_city') {
    this.scene = scene;
    this.trackId = trackId || 'neon_city';
    this.trackGroup = new THREE.Group();
    this.scene.add(this.trackGroup);

    this.roadWidth = 22;
    this.checkpoints = [];
    this.startPositions = [];
    this.nitroPads = [];
    this.obstacles = [];
    this.rotatingHazards = [];
    this.oilSlicks = [];

    // Define 3D Track Layout Curves based on Selected Map
    this.curvePoints = this.getTrackCurvePoints(this.trackId);
    this.curve = new THREE.CatmullRomCurve3(this.curvePoints, true, 'centripetal');

    // Generate Track Architecture
    this.buildRoad();
    this.buildEnvironment();
    this.buildStartGantry();
    this.generateCheckpoints();
    this.buildNitroPads();
    this.buildObstacles();
    this.buildRotatingHazards();
    this.buildOilSlicks();
  }

  getTrackCurvePoints(trackId) {
    if (trackId === 'desert_canyon') {
      // Sweeping high-speed canyon circuit with undulating canyon sweepers
      return [
        new THREE.Vector3(0, 0, 0),        // Main Canyon Straight
        new THREE.Vector3(0, 0, 90),       // Approach to canyon pass
        new THREE.Vector3(45, 0, 140),     // Sweeping Red Mesa turn
        new THREE.Vector3(105, 0, 120),    // Canyon Ridge curve
        new THREE.Vector3(140, 0, 50),     // Sand Dune straight
        new THREE.Vector3(155, 0, -35),    // Canyon Chicane 1
        new THREE.Vector3(120, 0, -100),   // Canyon Chicane 2
        new THREE.Vector3(40, 0, -135),    // Fast back sweeper
        new THREE.Vector3(-45, 0, -125),   // Rock archway approach
        new THREE.Vector3(-110, 0, -70),   // Mesa hairpin entry
        new THREE.Vector3(-115, 0, 15),    // Mesa hairpin exit
        new THREE.Vector3(-65, 0, 55),     // Turn onto start straight
        new THREE.Vector3(-15, 0, 10)      // Final straight
      ];
    } else if (trackId === 'arctic_glacier') {
      // Technical frozen glacier circuit with switchbacks & frozen lake bridge
      return [
        new THREE.Vector3(0, 0, 0),        // Start glacier straight
        new THREE.Vector3(0, 0, 75),       // Ice Bridge
        new THREE.Vector3(30, 0, 115),     // Turn 1 frozen wall
        new THREE.Vector3(75, 0, 125),     // Turn 2 ice cavern
        new THREE.Vector3(105, 0, 80),     // Glacier hairpin entry
        new THREE.Vector3(75, 0, 40),      // Glacier hairpin exit
        new THREE.Vector3(125, 0, -5),     // Mountain ice pass
        new THREE.Vector3(135, 0, -65),    // Fast snow drift
        new THREE.Vector3(85, 0, -115),    // Ice spire chicane
        new THREE.Vector3(25, 0, -105),    // Frozen lake straight
        new THREE.Vector3(-35, 0, -120),   // Glacier ridge turn
        new THREE.Vector3(-90, 0, -75),    // Back mountain curve
        new THREE.Vector3(-95, 0, -15),    // Final hairpin entry
        new THREE.Vector3(-55, 0, 25),     // Final turn
        new THREE.Vector3(-15, 0, 15)      // Start line alignment
      ];
    } else {
      // 'neon_city' - Cyberpunk Metropolis Street Circuit
      return [
        new THREE.Vector3(0, 0, 0),        // Start / Finish straight
        new THREE.Vector3(0, 0, 80),       // Main straight end
        new THREE.Vector3(30, 0, 130),     // Turn 1 sweeping right
        new THREE.Vector3(80, 0, 140),     // Turn 2
        new THREE.Vector3(120, 0, 100),    // Hairpin exit
        new THREE.Vector3(110, 0, 30),     // Short straight
        new THREE.Vector3(140, 0, -30),    // Chicane entry right
        new THREE.Vector3(110, 0, -80),    // Chicane exit left
        new THREE.Vector3(50, 0, -120),    // Fast sweeper
        new THREE.Vector3(-40, 0, -110),   // Turn onto back straight
        new THREE.Vector3(-90, 0, -60),    // Back sweeper
        new THREE.Vector3(-80, 0, 10),     // Final hairpin entry
        new THREE.Vector3(-40, 0, 30),     // Final turn onto main straight
        new THREE.Vector3(-10, 0, -10)     // Final straight alignment
      ];
    }
  }

  // --- ROAD & TRACK SURFACE GENERATION ---
  buildRoad() {
    const numSegments = 200;
    const roadPoints = this.curve.getSpacedPoints(numSegments);

    const roadVertices = [];
    const roadUvs = [];
    const roadIndices = [];

    const curbLVertices = [];
    const curbRVertices = [];
    const curbIndices = [];

    const halfWidth = this.roadWidth / 2;
    const curbWidth = 1.0;

    for (let i = 0; i <= numSegments; i++) {
      const u = i / numSegments;
      const pt = roadPoints[i % numSegments];
      const tangent = this.curve.getTangentAt(u).normalize();
      const up = new THREE.Vector3(0, 1, 0);
      const normal = new THREE.Vector3().crossVectors(tangent, up).normalize();

      // Road Edges
      const left = new THREE.Vector3().copy(pt).addScaledVector(normal, -halfWidth);
      const right = new THREE.Vector3().copy(pt).addScaledVector(normal, halfWidth);
      left.y = 0.05;
      right.y = 0.05;

      roadVertices.push(left.x, left.y, left.z);
      roadVertices.push(right.x, right.y, right.z);

      roadUvs.push(0, u * 50);
      roadUvs.push(1, u * 50);

      // Curbs (Rumble strips)
      const curbLeftOuter = new THREE.Vector3().copy(left).addScaledVector(normal, -curbWidth);
      const curbRightOuter = new THREE.Vector3().copy(right).addScaledVector(normal, curbWidth);
      curbLeftOuter.y = 0.12;
      curbRightOuter.y = 0.12;

      curbLVertices.push(curbLeftOuter.x, curbLeftOuter.y, curbLeftOuter.z);
      curbLVertices.push(left.x, left.y, left.z);

      curbRVertices.push(right.x, right.y, right.z);
      curbRVertices.push(curbRightOuter.x, curbRightOuter.y, curbRightOuter.z);

      if (i < numSegments) {
        const vIdx = i * 2;
        roadIndices.push(vIdx, vIdx + 1, vIdx + 2);
        roadIndices.push(vIdx + 1, vIdx + 3, vIdx + 2);

        curbIndices.push(vIdx, vIdx + 1, vIdx + 2);
        curbIndices.push(vIdx + 1, vIdx + 3, vIdx + 2);
      }
    }

    // Road Mesh Material configured by map theme
    let roadColor = 0x141822;
    let roadRoughness = 0.8;
    let roadMetalness = 0.1;

    if (this.trackId === 'desert_canyon') {
      roadColor = 0x221a16;
      roadRoughness = 0.85;
    } else if (this.trackId === 'arctic_glacier') {
      roadColor = 0x182c40;
      roadRoughness = 0.25;
      roadMetalness = 0.6; // Slippery glossy ice sheen
    }

    const roadGeo = new THREE.BufferGeometry();
    roadGeo.setAttribute('position', new THREE.Float32BufferAttribute(roadVertices, 3));
    roadGeo.setAttribute('uv', new THREE.Float32BufferAttribute(roadUvs, 2));
    roadGeo.setIndex(roadIndices);
    roadGeo.computeVertexNormals();

    const roadMat = new THREE.MeshStandardMaterial({
      color: roadColor,
      roughness: roadRoughness,
      metalness: roadMetalness
    });

    const roadMesh = new THREE.Mesh(roadGeo, roadMat);
    roadMesh.receiveShadow = true;
    this.trackGroup.add(roadMesh);

    // Kerbs (Striped rumble borders)
    this.createStripedKerb(curbLVertices, curbIndices);
    this.createStripedKerb(curbRVertices, curbIndices);

    // Perimeter Guardrail Barrier Posts
    this.buildGuardrails(roadPoints, halfWidth + curbWidth + 0.5);
  }

  createStripedKerb(vertices, indices) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    const numVerts = vertices.length / 3;
    const colors = [];

    // Distinct curb colors per map theme
    for (let i = 0; i < numVerts; i += 2) {
      const isAlt = Math.floor(i / 8) % 2 === 0;
      let r, g, b;

      if (this.trackId === 'desert_canyon') {
        r = isAlt ? 0.95 : 0.15;
        g = isAlt ? 0.75 : 0.15;
        b = isAlt ? 0.10 : 0.15; // Yellow and dark grey hazard stripes
      } else if (this.trackId === 'arctic_glacier') {
        r = isAlt ? 0.0 : 0.95;
        g = isAlt ? 0.85 : 0.95;
        b = isAlt ? 1.0 : 0.95;  // Cyan and snow white stripes
      } else {
        r = isAlt ? 0.95 : 0.95;
        g = isAlt ? 0.15 : 0.95;
        b = isAlt ? 0.25 : 0.95;  // Red and white racing curbs
      }

      colors.push(r, g, b);
      colors.push(r, g, b);
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.6
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.receiveShadow = true;
    this.trackGroup.add(mesh);
  }

  buildGuardrails(points, offsetDistance) {
    const numPts = points.length;
    let postColor = 0x3d4b63;
    if (this.trackId === 'desert_canyon') postColor = 0x614838;
    else if (this.trackId === 'arctic_glacier') postColor = 0x274a63;

    const railMat = new THREE.MeshStandardMaterial({
      color: postColor,
      metalness: 0.7,
      roughness: 0.3
    });

    const neonMat = new THREE.MeshBasicMaterial({
      color: this.trackId === 'desert_canyon' ? 0xffaa00 : (this.trackId === 'arctic_glacier' ? 0x00f0ff : 0x00d2ff)
    });

    for (let i = 0; i < numPts; i += 6) {
      const u = i / numPts;
      const pt = points[i];
      const tangent = this.curve.getTangentAt(u).normalize();
      const normal = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();

      [-offsetDistance, offsetDistance].forEach((offset) => {
        const postPos = new THREE.Vector3().copy(pt).addScaledVector(normal, offset);
        const post = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.2, 0.3), railMat);
        post.position.set(postPos.x, 0.6, postPos.z);
        post.castShadow = true;
        this.trackGroup.add(post);

        // LED Reflector on post
        const reflector = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.15, 0.15), neonMat);
        reflector.position.set(postPos.x, 0.95, postPos.z);
        this.trackGroup.add(reflector);
      });
    }
  }

  // --- ENVIRONMENT & 3D SCENERY ARCHITECTURE ---
  isPointTooCloseToRoad(x, z, minClearance) {
    if (!this.denseCurveSamples) {
      this.denseCurveSamples = this.curve.getSpacedPoints(300);
    }
    const minSq = minClearance * minClearance;
    for (let i = 0; i < this.denseCurveSamples.length; i++) {
      const pt = this.denseCurveSamples[i];
      const dx = x - pt.x;
      const dz = z - pt.z;
      if (dx * dx + dz * dz < minSq) {
        return true; // Point intersects road or is inside the safety buffer!
      }
    }
    return false;
  }

  getSafeSceneryPosition(targetAngle, baseRadius, minClearance, maxAttempts = 12) {
    let r = baseRadius;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const x = Math.cos(targetAngle) * r;
      const z = Math.sin(targetAngle) * r;
      if (!this.isPointTooCloseToRoad(x, z, minClearance)) {
        return { x, z };
      }
      r += 25; // Nudge outward until completely outside the road!
    }
    return null;
  }

  buildEnvironment() {
    if (this.trackId === 'desert_canyon') {
      this.buildCanyonScenery();
    } else if (this.trackId === 'arctic_glacier') {
      this.buildArcticScenery();
    } else {
      this.buildCyberCityScenery();
    }
  }

  // 1. NEON CITY: Cyberpunk Skyscrapers, Gantries & Street Lamps (Zero Road Intrusion, High FPS)
  buildCyberCityScenery() {
    // Cyber Tarmac Floor
    const groundGeo = new THREE.PlaneGeometry(800, 800);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x080c14, roughness: 0.95, metalness: 0.1 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = false;
    this.trackGroup.add(ground);

    const buildingColors = [0x101626, 0x161e33, 0x1a243d, 0x121a2c];
    const windowColors = [0x00f0ff, 0xffbe0b, 0xff0055, 0x00ff88];

    // Procedural Skyscrapers - 20 landmark buildings, guaranteed outside road
    const numBuildings = 20;
    for (let i = 0; i < numBuildings; i++) {
      const angle = (i / numBuildings) * Math.PI * 2 + (Math.random() - 0.5) * 0.15;
      const w = 12 + Math.random() * 12;
      const d = 12 + Math.random() * 12;
      const h = 25 + Math.random() * 45;

      const objRadius = Math.hypot(w, d) / 2;
      const requiredClearance = (this.roadWidth / 2) + objRadius + 12; // Min 30m away from road center
      const pos = this.getSafeSceneryPosition(angle, 105 + Math.random() * 90, requiredClearance);
      if (!pos) continue;

      const bMat = new THREE.MeshStandardMaterial({
        color: buildingColors[i % buildingColors.length],
        roughness: 0.5,
        metalness: 0.7
      });

      const building = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), bMat);
      building.position.set(pos.x, h / 2, pos.z);
      building.castShadow = false;
      this.trackGroup.add(building);

      // Glowing Neon Window Strips
      const winCount = 2 + Math.floor(Math.random() * 3);
      for (let k = 0; k < winCount; k++) {
        const winMat = new THREE.MeshBasicMaterial({
          color: windowColors[(i + k) % windowColors.length]
        });
        const strip = new THREE.Mesh(new THREE.BoxGeometry(w + 0.2, 0.4, d + 0.2), winMat);
        strip.position.set(pos.x, (k + 1) * (h / (winCount + 1)), pos.z);
        this.trackGroup.add(strip);
      }
    }

    // Street light poles along track - placed safely outside the 22m road (+3.5m beyond curb)
    const poleOffset = (this.roadWidth / 2) + 3.5;
    for (let i = 0; i < 14; i++) {
      const u = i / 14;
      const pt = this.curve.getPointAt(u);
      const tangent = this.curve.getTangentAt(u).normalize();
      const normal = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
      const pos = new THREE.Vector3().copy(pt).addScaledVector(normal, poleOffset);

      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 6.5, 6), new THREE.MeshStandardMaterial({ color: 0x222e44 }));
      pole.position.set(pos.x, 3.25, pos.z);
      this.trackGroup.add(pole);

      const head = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.25, 0.5), new THREE.MeshBasicMaterial({ color: 0x00f0ff }));
      head.position.set(pos.x, 6.6, pos.z);
      this.trackGroup.add(head);
    }
  }

  // 2. DESERT CANYON: Red Sandstone Mesas & Stone Archway (Zero Road Intrusion, High FPS)
  buildCanyonScenery() {
    // Red Sand Desert Floor
    const groundGeo = new THREE.PlaneGeometry(800, 800);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x6e371e, roughness: 0.95 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = false;
    this.trackGroup.add(ground);

    const mesaColors = [0x8f3c1d, 0xad522d, 0x6e2c14, 0xb86337];

    // Giant Sandstone Mesas - 18 landmark formations, guaranteed 100% outside the road!
    const numMesas = 18;
    for (let i = 0; i < numMesas; i++) {
      const angle = (i / numMesas) * Math.PI * 2 + (Math.random() - 0.5) * 0.2;
      const rTop = 7 + Math.random() * 8;
      const rBtm = rTop + 5 + Math.random() * 6; // Max 21m radius
      const h = 24 + Math.random() * 32;

      // Required clearance: road halfWidth (11m) + base radius + 12m safety margin
      const requiredClearance = (this.roadWidth / 2) + rBtm + 12;
      const pos = this.getSafeSceneryPosition(angle, 105 + Math.random() * 95, requiredClearance);
      if (!pos) continue;

      const rockMat = new THREE.MeshStandardMaterial({
        color: mesaColors[i % mesaColors.length],
        roughness: 0.9
      });

      const mesa = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBtm, h, 7), rockMat);
      mesa.position.set(pos.x, h / 2, pos.z);
      mesa.castShadow = false;
      this.trackGroup.add(mesa);
    }

    // Natural Stone Archway spanning over the track at u = 0.55
    const archU = 0.55;
    const archPt = this.curve.getPointAt(archU);
    const archTangent = this.curve.getTangentAt(archU).normalize();
    const rotY = Math.atan2(archTangent.x, archTangent.z);

    const archGroup = new THREE.Group();
    archGroup.position.set(archPt.x, 0, archPt.z);
    archGroup.rotation.y = rotY;

    const archMat = new THREE.MeshStandardMaterial({ color: 0x8f3c1d, roughness: 0.9 });

    // Left and Right Arch Pillars - placed safely 6m outside the 11m curb (+/-17m)
    const pillarOffset = (this.roadWidth / 2) + 6.0;
    const archL = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 3.5, 14, 8), archMat);
    archL.position.set(-pillarOffset, 7, 0);
    archGroup.add(archL);

    const archR = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 3.5, 14, 8), archMat);
    archR.position.set(pillarOffset, 7, 0);
    archGroup.add(archR);

    // Spanning Stone Arch Top
    const archTopWidth = (pillarOffset * 2) + 6.0;
    const archTop = new THREE.Mesh(new THREE.BoxGeometry(archTopWidth, 4.0, 5.5), archMat);
    archTop.position.set(0, 14.5, 0);
    archGroup.add(archTop);

    this.trackGroup.add(archGroup);
  }

  // 3. ARCTIC GLACIER: Ice Crystals & Snow Pines (Zero Road Intrusion, High FPS)
  buildArcticScenery() {
    // Frozen Snow Ground
    const groundGeo = new THREE.PlaneGeometry(800, 800);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x141e2e, roughness: 0.35, metalness: 0.5 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = false;
    this.trackGroup.add(ground);

    const iceMat = new THREE.MeshStandardMaterial({
      color: 0x70d6ff,
      roughness: 0.15,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85
    });

    const snowMat = new THREE.MeshStandardMaterial({ color: 0xe6f2ff, roughness: 0.7 });
    const pineMat = new THREE.MeshStandardMaterial({ color: 0x0f2922 });

    // Crystalline Glacier Peaks - 18 formations, guaranteed 100% outside the road!
    const numPeaks = 18;
    for (let i = 0; i < numPeaks; i++) {
      const angle = (i / numPeaks) * Math.PI * 2 + (Math.random() - 0.5) * 0.15;
      const h = 26 + Math.random() * 36;
      const r = 8 + Math.random() * 9;

      const requiredClearance = (this.roadWidth / 2) + r + 12;
      const pos = this.getSafeSceneryPosition(angle, 95 + Math.random() * 90, requiredClearance);
      if (!pos) continue;

      const glacier = new THREE.Mesh(new THREE.ConeGeometry(r, h, 6), (i % 2 === 0) ? iceMat : snowMat);
      glacier.position.set(pos.x, h / 2, pos.z);
      glacier.castShadow = false;
      this.trackGroup.add(glacier);

      // Snowy Pine Tree safely positioned behind the glacier peak away from the road
      const pineX = pos.x + (r + 4) * Math.cos(angle);
      const pineZ = pos.z + (r + 4) * Math.sin(angle);
      if (!this.isPointTooCloseToRoad(pineX, pineZ, (this.roadWidth / 2) + 6)) {
        const pine = new THREE.Mesh(new THREE.ConeGeometry(2.0, 6, 6), pineMat);
        pine.position.set(pineX, 3.0, pineZ);
        this.trackGroup.add(pine);
      }
    }
  }

  // --- START / FINISH GANTRY ARCH ---
  buildStartGantry() {
    const gantryGroup = new THREE.Group();
    gantryGroup.position.set(0, 0, 5);

    const metalMat = new THREE.MeshStandardMaterial({
      color: 0x222a38,
      metalness: 0.8,
      roughness: 0.2
    });

    // Left and Right Pillars
    const pillarL = new THREE.Mesh(new THREE.BoxGeometry(0.8, 6, 0.8), metalMat);
    pillarL.position.set(-this.roadWidth / 2 - 2, 3, 0);
    gantryGroup.add(pillarL);

    const pillarR = new THREE.Mesh(new THREE.BoxGeometry(0.8, 6, 0.8), metalMat);
    pillarR.position.set(this.roadWidth / 2 + 2, 3, 0);
    gantryGroup.add(pillarR);

    // Overhead Truss Bar
    const crossBeam = new THREE.Mesh(new THREE.BoxGeometry(this.roadWidth + 4.8, 0.9, 0.8), metalMat);
    crossBeam.position.set(0, 5.8, 0);
    gantryGroup.add(crossBeam);

    // Digital LED Billboard Sign
    const signMat = new THREE.MeshBasicMaterial({
      color: this.trackId === 'desert_canyon' ? 0xffaa00 : (this.trackId === 'arctic_glacier' ? 0x00f0ff : 0x00ffff)
    });
    const signBoard = new THREE.Mesh(new THREE.BoxGeometry(this.roadWidth - 2, 0.5, 0.1), signMat);
    signBoard.position.set(0, 6.8, 0);
    gantryGroup.add(signBoard);

    // Checkered Finish Line on Road
    const checkMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    for (let i = 0; i < 12; i++) {
      const x = -this.roadWidth / 2 + (i + 0.5) * (this.roadWidth / 12);
      if (i % 2 === 0) {
        const checker = new THREE.Mesh(new THREE.BoxGeometry(this.roadWidth / 12, 0.08, 1.4), checkMat);
        checker.position.set(x, 0.08, 5);
        this.trackGroup.add(checker);
      }
    }

    // Gantry Bulbs
    this.lightBulbs = [];
    const bulbPositions = [-2, 0, 2];
    bulbPositions.forEach((bx) => {
      const bulb = new THREE.Mesh(
        new THREE.SphereGeometry(0.35, 12, 12),
        new THREE.MeshBasicMaterial({ color: 0x330000 })
      );
      bulb.position.set(bx, 5.2, 0);
      gantryGroup.add(bulb);
      this.lightBulbs.push(bulb);
    });

    this.trackGroup.add(gantryGroup);
  }

  setGantryLights(state) {
    if (!this.lightBulbs || this.lightBulbs.length < 3) return;
    if (state === 'off') {
      this.lightBulbs.forEach(b => b.material.color.setHex(0x222222));
    } else if (state === '3') {
      this.lightBulbs[0].material.color.setHex(0xff0022);
      this.lightBulbs[1].material.color.setHex(0x222222);
      this.lightBulbs[2].material.color.setHex(0x222222);
    } else if (state === '2') {
      this.lightBulbs[0].material.color.setHex(0xff0022);
      this.lightBulbs[1].material.color.setHex(0xffbb00);
      this.lightBulbs[2].material.color.setHex(0x222222);
    } else if (state === '1') {
      this.lightBulbs[0].material.color.setHex(0xff0022);
      this.lightBulbs[1].material.color.setHex(0xffbb00);
      this.lightBulbs[2].material.color.setHex(0xffbb00);
    } else if (state === 'go') {
      this.lightBulbs.forEach(b => b.material.color.setHex(0x00ff88));
    }
  }

  generateCheckpoints() {
    const count = 12;
    this.checkpoints = [];

    for (let i = 0; i < count; i++) {
      const u = i / count;
      const pt = this.curve.getPointAt(u);
      const tangent = this.curve.getTangentAt(u).normalize();

      this.checkpoints.push({
        index: i,
        u: u,
        pos: pt,
        tangent: tangent,
        radius: 35
      });
    }

    const startU = 0.0;
    const startPt = this.curve.getPointAt(startU);
    const startTangent = this.curve.getTangentAt(startU).normalize();
    const startNormal = new THREE.Vector3().crossVectors(startTangent, new THREE.Vector3(0, 1, 0)).normalize();
    const rotY = Math.atan2(startTangent.x, startTangent.z);

    this.startPositions = [
      {
        slot: 1,
        pos: new THREE.Vector3().copy(startPt).addScaledVector(startNormal, -4.5).addScaledVector(startTangent, -3),
        rotY: rotY
      },
      {
        slot: 2,
        pos: new THREE.Vector3().copy(startPt).addScaledVector(startNormal, 4.5).addScaledVector(startTangent, -8),
        rotY: rotY
      }
    ];
  }

  // --- ⚡ NITRO BOOST PADS (SPEED PADS) ---
  buildNitroPads() {
    this.nitroPads = [];
    const configs = [
      { u: 0.08, offset: 0.0 },   // Start straight surge
      { u: 0.23, offset: 0.8 },   // Corner 1 exit
      { u: 0.39, offset: -0.8 },  // Mid straight
      { u: 0.58, offset: 0.0 },   // Fast straight
      { u: 0.75, offset: 0.0 },   // Back sweeper exit
      { u: 0.91, offset: -0.5 }   // Final sprint
    ];

    const padMat = new THREE.MeshStandardMaterial({
      color: 0x071e2e,
      emissive: 0x00d2ff,
      emissiveIntensity: 0.6,
      roughness: 0.3,
      metalness: 0.8
    });

    const arrowMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const canisterMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      emissive: 0x0088cc,
      emissiveIntensity: 0.7,
      roughness: 0.2,
      metalness: 0.9
    });

    configs.forEach((cfg, idx) => {
      const pt = this.curve.getPointAt(cfg.u);
      const tangent = this.curve.getTangentAt(cfg.u).normalize();
      const normal = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
      const rotY = Math.atan2(tangent.x, tangent.z);

      const pos = new THREE.Vector3().copy(pt).addScaledVector(normal, cfg.offset);
      pos.y = 0.07;

      const group = new THREE.Group();
      group.position.copy(pos);
      group.rotation.y = rotY;

      // 1. Tarmac Boost Chevron Pad
      const padMesh = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.06, 4.6), padMat);
      padMesh.receiveShadow = true;
      group.add(padMesh);

      // Chevron arrow strips
      [-1.0, 0.4, 1.6].forEach((zOff) => {
        const arrowL = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.08, 1.4), arrowMat);
        arrowL.position.set(-0.6, 0.04, zOff);
        arrowL.rotation.y = Math.PI / 4;
        group.add(arrowL);

        const arrowR = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.08, 1.4), arrowMat);
        arrowR.position.set(0.6, 0.04, zOff);
        arrowR.rotation.y = -Math.PI / 4;
        group.add(arrowR);
      });

      // 2. Floating Animated 3D Nitro Canister
      const floatGroup = new THREE.Group();
      floatGroup.position.set(0, 1.6, 0);

      const can = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 1.0, 12), canisterMat);
      floatGroup.add(can);

      const capMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.9, roughness: 0.1 });
      const topCap = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.15, 12), capMat);
      topCap.position.y = 0.52;
      floatGroup.add(topCap);

      const btmCap = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.15, 12), capMat);
      btmCap.position.y = -0.52;
      floatGroup.add(btmCap);

      // Orbiting Neon Rings
      const ring1 = new THREE.Mesh(new THREE.TorusGeometry(0.68, 0.04, 6, 18), ringMat);
      ring1.rotation.x = Math.PI / 3;
      floatGroup.add(ring1);

      const ring2 = new THREE.Mesh(new THREE.TorusGeometry(0.68, 0.04, 6, 18), ringMat);
      ring2.rotation.y = Math.PI / 3;
      floatGroup.add(ring2);

      group.add(floatGroup);
      this.trackGroup.add(group);

      this.nitroPads.push({
        id: `nitro_${idx}`,
        u: cfg.u,
        pos: pos,
        group: group,
        floatGroup: floatGroup,
        ring1: ring1,
        ring2: ring2,
        active: true,
        cooldownTimer: 0,
        radius: 2.8,
        time: Math.random() * 10
      });
    });
  }

  // --- ⚠️ HAZARD OBSTACLES (STRIPED BARRELS & HOLOGRAPHIC BEACONS) ---
  buildObstacles() {
    this.obstacles = [];
    const configs = [
      { u: 0.15, offset: 2.2 },   // Turn 1 right apex
      { u: 0.32, offset: -2.5 },  // Chicane entry left
      { u: 0.46, offset: 0.0 },   // Mid-chicane center road block
      { u: 0.65, offset: 2.4 },   // Fast sweeper outside
      { u: 0.83, offset: -2.0 }   // Hairpin entry left apex
    ];

    const barrelMat1 = new THREE.MeshStandardMaterial({ color: 0xff4400, roughness: 0.4, metalness: 0.4 });
    const barrelMat2 = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4, metalness: 0.2 });
    const beaconMat = new THREE.MeshBasicMaterial({ color: 0xff7700 });
    const holoMat = new THREE.MeshBasicMaterial({ color: 0xff3300, wireframe: true });

    configs.forEach((cfg, idx) => {
      const pt = this.curve.getPointAt(cfg.u);
      const tangent = this.curve.getTangentAt(cfg.u).normalize();
      const normal = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
      const rotY = Math.atan2(tangent.x, tangent.z);

      const pos = new THREE.Vector3().copy(pt).addScaledVector(normal, cfg.offset);

      const group = new THREE.Group();
      group.position.set(pos.x, 0, pos.z);
      group.rotation.y = rotY;

      // 3D Industrial Hazard Barrier Barrel
      const barrel = new THREE.Group();
      barrel.position.y = 0.6;

      const segH = 0.32;
      for (let s = 0; s < 4; s++) {
        const mat = (s % 2 === 0) ? barrelMat1 : barrelMat2;
        const tier = new THREE.Mesh(new THREE.CylinderGeometry(0.58 - s * 0.02, 0.62 - s * 0.02, segH, 12), mat);
        tier.position.y = (s - 1.5) * segH;
        tier.castShadow = true;
        tier.receiveShadow = true;
        barrel.add(tier);
      }

      // Flashing warning beacon
      const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.25, 8, 8), beaconMat);
      beacon.position.y = 0.85;
      barrel.add(beacon);

      // Floating Holographic Warning Diamond above barrel for high visibility
      const holoDiamond = new THREE.Mesh(new THREE.OctahedronGeometry(0.65, 0), holoMat);
      holoDiamond.position.y = 2.4;
      barrel.add(holoDiamond);

      // Base weight plate
      const basePlate = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.12, 12), barrelMat1);
      basePlate.position.y = -0.55;
      barrel.add(basePlate);

      group.add(barrel);
      this.trackGroup.add(group);

      this.obstacles.push({
        id: `obs_${idx}`,
        u: cfg.u,
        pos: pos,
        group: group,
        barrel: barrel,
        beacon: beacon,
        holoDiamond: holoDiamond,
        active: true,
        cooldownTimer: 0,
        radius: 2.2,
        baseY: 0.6
      });
    });
  }

  // --- ⚡ ROTATING LASER / HAZARD GATES (MOVING BARRIERS) ---
  buildRotatingHazards() {
    this.rotatingHazards = [];
    const configs = [
      { u: 0.28, rotSpeed: 1.6 },
      { u: 0.68, rotSpeed: -1.8 }
    ];

    const metalMat = new THREE.MeshStandardMaterial({ color: 0x222e3d, metalness: 0.8, roughness: 0.2 });
    const laserMat = new THREE.MeshBasicMaterial({ color: 0xff0044 });

    configs.forEach((cfg, idx) => {
      const pt = this.curve.getPointAt(cfg.u);
      const tangent = this.curve.getTangentAt(cfg.u).normalize();
      const rotY = Math.atan2(tangent.x, tangent.z);

      const group = new THREE.Group();
      group.position.set(pt.x, 0, pt.z);
      group.rotation.y = rotY;

      // Central Hub Pillar
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.55, 3.2, 10), metalMat);
      hub.position.y = 1.6;
      group.add(hub);

      // Rotating Laser Arm Assembly
      const rotatingArm = new THREE.Group();
      rotatingArm.position.y = 1.4;

      // Hazard beam
      const beamGeo = new THREE.BoxGeometry(6.5, 0.25, 0.35);
      const beam = new THREE.Mesh(beamGeo, laserMat);
      beam.position.x = 3.25; // Sweeps out from center hub
      rotatingArm.add(beam);

      // Warning tip
      const tip = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), new THREE.MeshBasicMaterial({ color: 0xffaa00 }));
      tip.position.x = 6.5;
      rotatingArm.add(tip);

      group.add(rotatingArm);
      this.trackGroup.add(group);

      this.rotatingHazards.push({
        id: `rot_${idx}`,
        u: cfg.u,
        pos: pt,
        arm: rotatingArm,
        rotSpeed: cfg.rotSpeed,
        angle: 0,
        radius: 5.5
      });
    });
  }

  // --- 🛢️ OIL & SLICK HAZARDS (MOY KO'LMAKLARI) ---
  buildOilSlicks() {
    this.oilSlicks = [];
    const configs = [
      { u: 0.22, offset: -1.6 }, // Turn 1 apex
      { u: 0.52, offset: 1.5 },  // Fast curve
      { u: 0.86, offset: 0.2 }   // Final hairpin
    ];

    const oilMat = new THREE.MeshStandardMaterial({
      color: 0x090614,
      roughness: 0.08,
      metalness: 0.95
    });

    configs.forEach((cfg, idx) => {
      const pt = this.curve.getPointAt(cfg.u);
      const tangent = this.curve.getTangentAt(cfg.u).normalize();
      const normal = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
      const rotY = Math.atan2(tangent.x, tangent.z);

      const pos = new THREE.Vector3().copy(pt).addScaledVector(normal, cfg.offset);
      pos.y = 0.06;

      const group = new THREE.Group();
      group.position.copy(pos);
      group.rotation.y = rotY;

      // Dark reflective puddle
      const puddle = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.7, 0.03, 14), oilMat);
      puddle.scale.set(1.0, 1.0, 1.5);
      puddle.receiveShadow = true;
      group.add(puddle);

      this.trackGroup.add(group);

      this.oilSlicks.push({
        id: `oil_${idx}`,
        u: cfg.u,
        pos: pos,
        radius: 2.8
      });
    });
  }

  // --- PER-FRAME ANIMATION TICK ---
  update(dt) {
    // 1. Animate Nitro Boost Pads
    if (this.nitroPads) {
      this.nitroPads.forEach(pad => {
        pad.time += dt;
        if (pad.active) {
          pad.floatGroup.visible = true;
          pad.floatGroup.position.y = 1.5 + Math.sin(pad.time * 3.5) * 0.25;
          pad.floatGroup.rotation.y += dt * 2.8;
          pad.ring1.rotation.x += dt * 3.0;
          pad.ring2.rotation.z += dt * 2.5;
        } else {
          pad.cooldownTimer -= dt;
          pad.floatGroup.visible = false;
          if (pad.cooldownTimer <= 0) {
            pad.active = true;
            pad.floatGroup.visible = true;
          }
        }
      });
    }

    // 2. Animate Obstacles (Beacons & Holograms)
    if (this.obstacles) {
      const now = performance.now();
      const blink = Math.sin(now * 0.009) > 0;
      this.obstacles.forEach(obs => {
        obs.beacon.material.color.setHex(blink ? 0xffaa00 : 0x441100);

        if (obs.holoDiamond) {
          obs.holoDiamond.rotation.y += dt * 2.0;
          obs.holoDiamond.rotation.x += dt * 1.0;
        }

        if (!obs.active) {
          obs.cooldownTimer -= dt;
          if (obs.cooldownTimer <= 0) {
            obs.active = true;
            obs.barrel.position.y = obs.baseY;
            obs.barrel.rotation.set(0, 0, 0);
          }
        }
      });
    }

    // 3. Animate Rotating Laser Hazard Gates
    if (this.rotatingHazards) {
      this.rotatingHazards.forEach(hazard => {
        hazard.angle += hazard.rotSpeed * dt;
        hazard.arm.rotation.y = hazard.angle;
      });
    }
  }

  // --- COLLISION & PICKUP INTERACTIONS ---
  checkCarInteractions(car) {
    if (!car) return [];
    const interactions = [];

    // 1. Check Nitro Pads
    if (this.nitroPads) {
      for (const pad of this.nitroPads) {
        if (!pad.active) continue;
        const dx = car.x - pad.pos.x;
        const dz = car.z - pad.pos.z;
        const distSq = dx * dx + dz * dz;
        if (distSq < pad.radius * pad.radius) {
          pad.active = false;
          pad.cooldownTimer = 4.0;
          interactions.push({ type: 'nitro', id: pad.id, pos: pad.pos });
        }
      }
    }

    // 2. Check Rotating Laser Hazard Gates
    if (this.rotatingHazards) {
      for (const hazard of this.rotatingHazards) {
        const dx = car.x - hazard.pos.x;
        const dz = car.z - hazard.pos.z;
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (dist < hazard.radius) {
          // Check if car angle aligns with rotating beam
          const carAngle = Math.atan2(dz, dx);
          let angleDiff = Math.abs((hazard.angle % (Math.PI * 2)) - (carAngle % (Math.PI * 2)));
          if (angleDiff > Math.PI) angleDiff = Math.PI * 2 - angleDiff;
          if (angleDiff < 0.45 && (!car.obstacleCooldown || car.obstacleCooldown <= 0)) {
            car.obstacleCooldown = 1.5;
            interactions.push({ type: 'obstacle', id: hazard.id, pos: hazard.pos, label: 'LASER' });
          }
        }
      }
    }

    // 3. Check Obstacle Barrels
    if (this.obstacles) {
      for (const obs of this.obstacles) {
        if (!obs.active) continue;
        const dx = car.x - obs.pos.x;
        const dz = car.z - obs.pos.z;
        const distSq = dx * dx + dz * dz;
        if (distSq < obs.radius * obs.radius) {
          obs.active = false;
          obs.cooldownTimer = 3.5;
          obs.barrel.position.y = 0.5;
          obs.barrel.rotation.x += 1.8;
          obs.barrel.rotation.z += 1.8;
          obs.pos.x += (Math.random() > 0.5 ? 2.5 : -2.5);
          interactions.push({ type: 'obstacle', id: obs.id, pos: obs.pos, label: 'BARREL' });
        }
      }
    }

    // 4. Check Oil Slicks
    if (this.oilSlicks && (!car.oilCooldown || car.oilCooldown <= 0)) {
      for (const oil of this.oilSlicks) {
        const dx = car.x - oil.pos.x;
        const dz = car.z - oil.pos.z;
        const distSq = dx * dx + dz * dz;
        if (distSq < oil.radius * oil.radius) {
          car.oilCooldown = 1.8;
          interactions.push({ type: 'oil', id: oil.id, pos: oil.pos });
          break;
        }
      }
    }

    return interactions;
  }

  // Barrier bounce and containment
  constrainCarToTrack(car) {
    let closestU = 0;
    let minDistanceSq = Infinity;
    const samples = 100;

    for (let i = 0; i < samples; i++) {
      const u = i / samples;
      const pt = this.curve.getPointAt(u);
      const dSq = (car.x - pt.x) ** 2 + (car.z - pt.z) ** 2;
      if (dSq < minDistanceSq) {
        minDistanceSq = dSq;
        closestU = u;
      }
    }

    const maxDist = this.roadWidth / 2 + 1.2;
    const currentDist = Math.sqrt(minDistanceSq);

    if (currentDist > maxDist) {
      const pt = this.curve.getPointAt(closestU);
      const toCenter = new THREE.Vector2(pt.x - car.x, pt.z - car.z).normalize();
      const penetration = currentDist - maxDist;

      // Keep car inside road bounds smoothly
      car.x += toCenter.x * penetration;
      car.z += toCenter.y * penetration;

      // DO NOT STOP! Retain 98% momentum without halting
      car.speed = Math.max(car.speed * 0.98, 14);

      // Deflect car heading smoothly along road tangent so it glances off
      const tangent = this.curve.getTangentAt(closestU).normalize();
      const roadHeading = Math.atan2(tangent.x, tangent.z);
      let diff = roadHeading - car.rotY;
      while (diff < -Math.PI) diff += Math.PI * 2;
      while (diff > Math.PI) diff -= Math.PI * 2;
      car.rotY += diff * 0.12;
    }
  }

  // Checkpoint progress check with robust drift & lap finish detection
  checkCheckpointProgress(carPos, currentCheckpointIdx) {
    const count = this.checkpoints.length;
    const targetIdx = (currentCheckpointIdx + 1) % count;
    const target = this.checkpoints[targetIdx];

    const dx = carPos.x - target.pos.x;
    const dz = carPos.z - target.pos.z;
    const distSq = dx * dx + dz * dz;
    const rad = target.radius || 35;

    if (distSq < rad * rad) {
      const isLapComplete = (targetIdx === 0 && currentCheckpointIdx >= count - 2);
      return {
        passed: true,
        newIndex: targetIdx,
        isLapComplete: isLapComplete
      };
    }

    // Secondary lookahead: allow passing next checkpoint if wide drift or apex cut occurred
    const nextPlusOne = (currentCheckpointIdx + 2) % count;
    if (nextPlusOne !== 0) {
      const altTarget = this.checkpoints[nextPlusOne];
      const adx = carPos.x - altTarget.pos.x;
      const adz = carPos.z - altTarget.pos.z;
      if (adx * adx + adz * adz < rad * rad) {
        return {
          passed: true,
          newIndex: nextPlusOne,
          isLapComplete: false
        };
      }
    }

    return { passed: false };
  }

  // Render 2D top-down minimap on HUD canvas with track theme styling
  renderMinimap(canvas, p1Car, p2Car) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    const minX = -130, maxX = 170;
    const minZ = -150, maxZ = 160;

    const mapX = (x) => ((x - minX) / (maxX - minX)) * (w - 24) + 12;
    const mapY = (z) => ((z - minZ) / (maxZ - minZ)) * (h - 24) + 12;

    // Track path color based on theme
    let trackStroke = '#00f0ff';
    if (this.trackId === 'desert_canyon') trackStroke = '#ff9e00';
    else if (this.trackId === 'arctic_glacier') trackStroke = '#48cae4';

    // Outer dark track body
    ctx.beginPath();
    ctx.strokeStyle = '#1a2436';
    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    const points = this.curve.getPoints(80);
    points.forEach((pt, i) => {
      const px = mapX(pt.x);
      const py = mapY(pt.z);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.closePath();
    ctx.stroke();

    // Inner glowing neon track line
    ctx.beginPath();
    ctx.strokeStyle = trackStroke;
    ctx.lineWidth = 2.5;
    points.forEach((pt, i) => {
      const px = mapX(pt.x);
      const py = mapY(pt.z);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.closePath();
    ctx.stroke();

    // Start / Finish Indicator
    const startPt = this.curve.getPointAt(0);
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(mapX(startPt.x), mapY(startPt.z), 3.5, 0, Math.PI * 2);
    ctx.fill();

    // Draw Nitro Pads (cyan glowing diamonds)
    if (this.nitroPads) {
      this.nitroPads.forEach(pad => {
        if (pad.active) {
          const nx = mapX(pad.pos.x);
          const ny = mapY(pad.pos.z);
          ctx.fillStyle = '#00f0ff';
          ctx.beginPath();
          ctx.moveTo(nx, ny - 3.5);
          ctx.lineTo(nx + 3.5, ny);
          ctx.lineTo(nx, ny + 3.5);
          ctx.lineTo(nx - 3.5, ny);
          ctx.closePath();
          ctx.fill();
        }
      });
    }

    // Draw Obstacles (orange warning dots)
    if (this.obstacles) {
      this.obstacles.forEach(obs => {
        if (obs.active) {
          const ox = mapX(obs.pos.x);
          const oy = mapY(obs.pos.z);
          ctx.fillStyle = '#ff5500';
          ctx.beginPath();
          ctx.arc(ox, oy, 2.5, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    // Draw Rotating Laser Gates (red lines)
    if (this.rotatingHazards) {
      this.rotatingHazards.forEach(hazard => {
        const hx = mapX(hazard.pos.x);
        const hy = mapY(hazard.pos.z);
        ctx.fillStyle = '#ff0055';
        ctx.beginPath();
        ctx.arc(hx, hy, 2.5, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // Draw Oil Slicks (purple dots)
    if (this.oilSlicks) {
      this.oilSlicks.forEach(oil => {
        const ox = mapX(oil.pos.x);
        const oy = mapY(oil.pos.z);
        ctx.fillStyle = '#9d4edd';
        ctx.beginPath();
        ctx.arc(ox, oy, 2.0, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // Draw Player 1 (Red dot)
    if (p1Car) {
      ctx.fillStyle = '#ff2b56';
      ctx.shadowColor = '#ff2b56';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(mapX(p1Car.x), mapY(p1Car.z), 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // Draw Player 2 (Cyan dot)
    if (p2Car) {
      ctx.fillStyle = '#00ff88';
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(mapX(p2Car.x), mapY(p2Car.z), 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  dispose() {
    if (this.trackGroup) {
      this.scene.remove(this.trackGroup);
    }
  }
}

window.RaceTrack = RaceTrack;
