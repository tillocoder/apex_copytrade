# 🏎️ APEX SPEED 3D - Termux Multiplayer Racing Game

Termux (Android) serverlari uchun maxsus optimallashtirilgan, o'ta yengil (**ultra-lightweight**) real-time 3D multiplayer poyga o'yini.

---

## ⚡ Asosiy Afzalliklari va Xususiyatlari

1. **Brauzerda ishlaydi**: Hech qanday ilova yoki plugin o'rnatish shart emas. Har qanday telefon (Chrome, Safari) yoki kompyuter brauzerida ishlaydi.
2. **2 kishilik Real-Time Multiplayer**:
   - Lobbyda online foydalanuvchilar ro'yxati ko'rinadi.
   - Do'stingizga **⚔️ Challenge** tugmasi orqali taklif yuborasiz (15 soniyalik modal).
   - Taklif yuborishda va qabul qilishda tanlangan trassa hamda mashina turi ko'rsatiladi.
   - Do'stingiz qabul qilishi bilan ikkalangiz bir vaqtda 3D trassaga tushasiz.
3. **🚗 4 Xil Mashina Tanlash (Showroom)**:
   - **Apex GT (Hypercar)**: Muvozanatli tezlik, barqaror boshqaruv va zamonaviy aerodinamika.
   - **V8 Beast (Muscle GT)**: Yuqori tezlanish, kuchli supercharger va orqa g'ildirak quvvati.
   - **Cyber Armor (4x4 Truck)**: Og'ir bronelangan korpus, to'siqlarga chidamli (obstacle hitdan kamroq tezlik yo'qotadi).
   - **Aero GP (Formula 1)**: Maksimal tezlik va o'ta chaqqon boshqaruv, ochiq g'ildirakli halo dizayni.
4. **🏁 3 Xil Tematik Trassa (Poyga Kartalari)**:
   - **Neon Metropolis**: 48 ta osmono'par bino, neon chiroqlar, kiber gantry va neon billboardlar.
   - **Desert Canyon**: Qizil tosh kanyonlar, tosh arkali tunnel, kaktuslar va sahro shafaq nuri.
   - **Arctic Glacier**: Muz cho'qqilari, ko'k kristall muzliklar, muzlagan silliq yo'l va shimol shafag'i.
5. **🎵 Protsessual Synthwave Musiqa va Ovozlar**:
   - Web Audio API orqali brauzerda 100% real-time sintezlanadigan 16-bosqichli elektro musiqa (drums, pumping bass, arp).
   - Dvigatel ovozi, drift chiyillashi, nitro portlashi, crash/to'siq urilishi, moy sirpanishi va shamol shovqini (0 bayt tashqi audio yuklama!).
   - Lobby va o'yin ichida musiqa yoqish/o'chirish (ON/OFF) tugmasi.
6. **💥 Dinamik To'siqlar, Keng Yo'l va Boshqariladigan Nitro**:
   - **Keng Yo'l (22 metr)**: Yo'l kengligi 14m dan 22m gacha kengaytirildi (~57% kengroq!), mashinalar erkin manyovr qilishi va to'siqlardan o'tib ketishi ancha osonlashdi.
   - **To'xtab Qolmaslik (Arcade Smooth Collisions)**: Yo'l chetlariga (bordyurlarga) yoki to'siqlarga urilganda mashina qotib to'xtab qolmaydi! Tezlikning 90-98% saqlanadi, to'siqlar yorib o'tiladi va mashina trassa yo'nalishiga moslashib harakatni davom ettiradi.
   - **⚡ Zaxira Nitro (Manual Boost)**: Nitro pad ustidan o'tganda nitro birdaniga o'z-o'zidan yonib ketmaydi. Mashinaga 1 dan 3 tagacha nitro zaryadi to'planadi. O'yinchi xohlagan paytida (`Shift`, `E`, `N` yoki telefonda `🚀` tugmasi orqali) o'zi bosib ishlatadi!
   - **⚠️ To'siq bochkalari & Gologramma**: Ogohlantiruvchi neon mayoqchalar, urilganda bochkalar chetga uchib ketadi, ekranda yengil qizil zarba xiralashishi va kamera silkinishi bo'ladi.
   - **🚨 Aylanuvchi Lazer Darvozalari**: Yo'l bo'ylab aylanib turuvchi xavfli to'siqlar.
   - **🛢️ Moy To'siqlari**: Mashinani 360° drift bilan aylantirib yuboradigan moy sirpanishi va binafsha smudge effekti (saqlab qolingan).
   - **🌀 Yuqori Tezlik Blur**: 120+ km/h da ekranning chekkalarida dinamik harakat xiralashishi (motion blur).
7. **Termux uchun O'ta Kam Resurs Sarfi**:
   - **RAM**: ~30 MB Node.js xotirasi.
   - **CPU**: 0.05% - 0.2% (Serverda og'ir fizika yoki 3D rendering hisoblanmaydi!).
   - Fizika to'liq client-side (brauzerda) ishlaydi, server faqat tezkor holat almashinuvi (state relay) va matchmaking bilan shug'ullanadi.
8. **Desktop va Mobil Boshqaruv**:
   - **Kompyuterda**: WASD yoki Yo'nalish tugmalari (▲ ▼ ◀ ▶), Bo'shliq (Drift), **Shift / E / N (Nitro)**, R (Trassaga qayta qo'yish).
   - **Telefonda**: Ekranda sensorli tugmalar (Gaz, Tormoz, Chap, O'ng, Drift, **🚀 Nitro**, Reset).


---

## 📁 Loyiha Tuzilmasi

```text
termux-racing-game/
├── server.js              # Ultra-yengil HTTP + WebSocket server
├── package.json           # Faqat bitta dependency: "ws"
├── ecosystem.config.js    # PM2 orqali Termuxda 24/7 orqa fonda yurgizish
├── start.sh               # Tezkor ishga tushirish skripti
├── install-termux.sh      # 1-klikli Termux o'rnatish skripti
├── nginx.conf             # Nginx Reverse Proxy konfiguratsiyasi
└── public/
    ├── index.html         # Asosiy HTML (Lobby, HUD, Modallar, Touch UI)
    ├── css/
    │   └── style.css      # Cyberpunk & Glassmorphism dizayn
    └── js/
        ├── lib/
        │   └── three.min.js  # Offline Three.js (Termuxdan to'g'ridan-to'g'ri beriladi)
        ├── audio.js       # Web Audio API protsessual tovush generatori
        ├── input.js       # Klaviatura va sensorli tugmalar boshqaruvi
        ├── car.js         # 3D avtomobil modeli va arkada fizikasi
        ├── track.js       # 3D trassa, bordyurlar, minimap va chekpointlar
        ├── network.js     # WebSocket mijoz va ping o'lchagich
        └── game.js        # Three.js render tsikli, kamera va UI boshqaruvi
```

---

## 🚀 Termux Serverga O'rnatish va Ishga Tushirish

### 1-Qadam: Termux'ga yuklash
Loyiha papkasini (`termux-racing-game`) Termux serveringizga nusxalang (masalan, git, scp yoki tar/zip orqali):
```bash
cd termux-racing-game
```

### 2-Qadam: O'rnatish
Agar Node.js bo'lmasa yoki yangi o'rnatayotgan bo'lsangiz:
```bash
chmod +x install-termux.sh start.sh
./install-termux.sh
```

Yoki qo'lda:
```bash
pkg install nodejs-lts -y
npm install --omit=dev
```

### 3-Qadam: Ishga tushirish
Standart tarzda **5050** portda ishga tushadi:
```bash
./start.sh
# yoki
node server.js
```

Agar boshqa port tanlamoqchi bo'lsangiz:
```bash
PORT=4000 node server.js
```

### 4-Qadam: Orqa fonda (24/7 PM2) ishlatish
Termux ilovasi yopilganda ham server to'xtab qolmasligi uchun:
```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
```
Holatni tekshirish:
```bash
pm2 status
pm2 logs apex-speed-3d
```

---

## 🌐 Brauzer orqali Kirish va O'ynash

1. **Mahalliy Wi-Fi / Hotspot orqali**:
   - Termux serverining IP manzilini bilish uchun: `ifconfig` (masalan, `192.168.1.15`).
   - Ikkala telefon ham bir xil Wi-Fi tarmog'iga ulangan bo'lsa:
     `http://192.168.1.15:5050`
   - **Internet bo'lmasa ham ishlaydi** — barcha 3D kutubxonalar va tovushlar to'liq oflayn yuklanadi!

2. **Cloudflare Tunnel orqali (Tashqi internet uchun eng oson yo'l)**:
   ```bash
   pkg install cloudflared -y
   cloudflared tunnel --url http://localhost:5050
   ```
   Sizga `https://tasodifiy-nom.trycloudflare.com` havolasini beradi. Do'stingizga shu havolani berasiz!

3. **Nginx Reverse Proxy orqali (O'z domeningiz bo'lsa)**:
   Mavjud domeningiz yoki subdomeningiz uchun `nginx.conf` faylidagi sozlamani Nginx konfiguratsiyasiga qo'shing:
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:5050;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
   }
   ```
   So'ng `nginx -s reload` qiling.

---

## 🎮 O'yin Jarayoni

1. Brauzerda sahifani ochasiz. Taxallus (ism) avtomatik saqlanadi (`localStorage`).
2. Do'stingiz ham xuddi shu havolani ochadi.
3. Lobbyda ikkovingiz ham paydo bo'lasiz.
4. Do'stingiz yonidagi **⚔️ Challenge** tugmasini bosing.
5. Do'stingiz telefonida chiroyli taklif modali chiqadi. U **QABUL QILISH** tugmasini bosadi.
6. 3D poyga maydoni yuklanadi, **3 → 2 → 1 → GO!** sanoq tugagach poyga boshlanadi!
7. 2 davra tugagach g'olib e'lon qilinadi va **Rematch** tugmasi orqali cheksiz davom ettirish mumkin.
