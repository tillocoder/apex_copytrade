#!/data/data/com.termux/files/usr/bin/bash
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home

pkill -9 -f "cloudflared tunnel" || true
sleep 1

# Ensure resolv.conf has reliable nameservers
echo "nameserver 1.1.1.1" > $PREFIX/etc/resolv.conf
echo "nameserver 8.8.8.8" >> $PREFIX/etc/resolv.conf
echo "nameserver 192.168.1.1" >> $PREFIX/etc/resolv.conf

nohup $PREFIX/bin/proot \
  -b /system:/system \
  -b /vendor:/vendor \
  -b /data:/data \
  -b /sbin:/sbin \
  -b /root:/root \
  -b /property_contexts:/property_contexts \
  -b /storage:/storage \
  -b $PREFIX:/usr \
  -b $PREFIX/bin:/bin \
  -b $PREFIX/etc:/etc \
  -b $PREFIX/etc/resolv.conf:/system/etc/resolv.conf \
  -b $PREFIX/etc/resolv.conf:/etc/resolv.conf \
  -b $PREFIX/lib:/lib \
  -b $PREFIX/share:/share \
  -b $PREFIX/tmp:/tmp \
  -b $PREFIX/var:/var \
  -b /dev:/dev \
  -b /proc:/proc \
  --cwd=/home \
  -r $PREFIX/.. \
  --cwd=. \
  sh -c "$HOME/cloudflared tunnel --config $HOME/.cloudflared/config.yml run 6c07f140-d72a-41b8-b09c-c20353428851" > $HOME/cloudflared.log 2>&1 &

echo "[+] Cloudflared launched with proot"
