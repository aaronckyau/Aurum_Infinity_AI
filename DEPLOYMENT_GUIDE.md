# 🚀 K博士投研站 - REST API 部署指南

**適用於**: IT 部門 / DevOps 團隊
**版本**: v1.0
**日期**: 2026-03-11

---

## 📋 部署清單

- [ ] 檢查系統要求
- [ ] 準備運行環境
- [ ] 配置 API 服務
- [ ] 啟動伺服器
- [ ] 驗證 API 正常運作
- [ ] 配置監控和日誌
- [ ] 備份和恢復計劃

---

## 🔧 系統要求

### **硬體要求**

| 項目 | 最低要求 | 推薦配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 記憶體 | 2 GB | 8 GB |
| 儲存空間 | 10 GB | 50+ GB（快取） |
| 網路 | 1 Mbps | 10+ Mbps |

### **軟體要求**

| 軟體 | 版本 | 說明 |
|------|------|------|
| Python | 3.8+ | 必需 |
| pip | 最新 | Python 套件管理 |
| Nginx | 1.18+ | 反向代理 |
| Gunicorn | 20.0+ | WSGI 伺服器 |
| systemd | - | 服務管理（Linux） |

### **網路要求**

```
外部訪問:
  ├── HTTP  (80)   → HTTPS 重定向
  ├── HTTPS (443)  → Nginx 反向代理
  └── SSH  (22)    → 管理連接

內部訪問:
  └── Gunicorn (127.0.0.1:5000)  → 僅本機
```

---

## 📦 檔案清單

部署時需要以下檔案：

```
Aurum_Infinity_AI/
├── app.py                    ✅ Flask 主程式
├── file_cache.py             ✅ 快取管理
├── prompt_manager.py         ✅ Prompt 管理
├── requirements.txt          ✅ Python 依賴
├── cache/                    ✅ 分析快取目錄
├── prompts/                  ✅ Prompt 配置
├── templates/                ✅ HTML 模板
├── static/                   ✅ 靜態資源
├── API_DOCUMENTATION.md      ✅ API 文檔
└── .env                      ✅ 環境配置（不包含在版本控制）
```

---

## ⚙️ 部署步驟

### **步驟 1️⃣：準備運行環境（Linux/Ubuntu）**

```bash
# 以 root 或 sudo 執行

# 1. 更新系統
sudo apt update && sudo apt upgrade -y

# 2. 安裝 Python 和必要工具
sudo apt install -y python3.11 python3.11-venv python3-pip \
  nginx curl wget git

# 3. 創建應用使用者（建議）
sudo useradd -m -s /bin/bash aurum

# 4. 創建應用目錄
sudo mkdir -p /opt/aurum_infinity_ai
sudo chown -R aurum:aurum /opt/aurum_infinity_ai
cd /opt/aurum_infinity_ai
```

### **步驟 2️⃣：複製應用檔案**

```bash
# 方式 A：使用 Git
sudo -u aurum git clone https://github.com/aaronckyau/Aurum_Infinity_AI.git .

# 方式 B：使用 SCP（從本地上傳）
scp -r ./Aurum_Infinity_AI/* aurum@server:/opt/aurum_infinity_ai/
```

### **步驟 3️⃣：配置虛擬環境**

```bash
# 切換到應用使用者
sudo -u aurum -i

# 建立虛擬環境
cd /opt/aurum_infinity_ai
python3.11 -m venv venv

# 啟用虛擬環境
source venv/bin/activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt
```

### **步驟 4️⃣：配置環境變數**

```bash
# 建立 .env 檔案（注意：包含敏感資訊，需要保護）
sudo nano /opt/aurum_infinity_ai/.env
```

**填入以下內容**:
```env
# Gemini API
GEMINI_API_KEY=your-api-key-here

# Flask
FLASK_ENV=production
SECRET_KEY=your-random-secret-key-32-chars

# 其他配置
DEBUG=False
```

**設定檔案權限**:
```bash
sudo chmod 600 /opt/aurum_infinity_ai/.env
sudo chown aurum:aurum /opt/aurum_infinity_ai/.env
```

### **步驟 5️⃣：配置 Gunicorn**

建立 systemd 服務檔案：

```bash
sudo nano /etc/systemd/system/aurum.service
```

**複製以下內容**:
```ini
[Unit]
Description=K博士投研站 - REST API 服務
After=network.target

[Service]
User=aurum
Group=aurum
WorkingDirectory=/opt/aurum_infinity_ai
Environment="PATH=/opt/aurum_infinity_ai/venv/bin"
EnvironmentFile=/opt/aurum_infinity_ai/.env
ExecStart=/opt/aurum_infinity_ai/venv/bin/gunicorn \
  --workers 4 \
  --worker-class sync \
  --bind 127.0.0.1:5000 \
  --timeout 120 \
  --access-logfile /var/log/aurum/access.log \
  --error-logfile /var/log/aurum/error.log \
  app:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**啟用服務**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aurum
sudo systemctl start aurum
sudo systemctl status aurum
```

### **步驟 6️⃣：配置 Nginx**

建立 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/allin.auincap.com
```

**複製以下內容**:
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name allin.auincap.com;

    # HTTP → HTTPS 重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name allin.auincap.com;

    # SSL 證書配置（使用 Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/allin.auincap.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/allin.auincap.com/privkey.pem;

    # SSL 安全設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 安全標頭
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # 日誌
    access_log /var/log/nginx/allin_access.log;
    error_log /var/log/nginx/allin_error.log;

    # 代理到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # API 端點特別配置
    location /api/markdown/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

**啟用配置**:
```bash
sudo ln -s /etc/nginx/sites-available/allin.auincap.com \
  /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx
```

### **步驟 7️⃣：配置 SSL（Let's Encrypt）**

```bash
# 安裝 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 獲取證書
sudo certbot certonly --nginx -d allin.auincap.com

# 自動續期
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 🔍 驗證部署

### **檢查服務狀態**

```bash
# 檢查 Gunicorn 服務
sudo systemctl status aurum

# 檢查 Nginx
sudo systemctl status nginx

# 檢查監聽端口
sudo netstat -tlnp | grep 5000
sudo netstat -tlnp | grep 80
sudo netstat -tlnp | grep 443
```

### **測試 API 連接**

```bash
# 測試本機 API
curl http://localhost:5000/api/markdown/NVDA/biz

# 測試外部 HTTPS API
curl https://allin.auincap.com/api/markdown/NVDA/biz

# 驗證 SSL 證書
curl -vI https://allin.auincap.com
```

### **檢查日誌**

```bash
# Gunicorn 日誌
sudo journalctl -u aurum -f

# Nginx 訪問日誌
sudo tail -f /var/log/nginx/allin_access.log

# Nginx 錯誤日誌
sudo tail -f /var/log/nginx/allin_error.log
```

---

## 📊 監控和日誌

### **配置日誌文件夾**

```bash
sudo mkdir -p /var/log/aurum
sudo chown aurum:aurum /var/log/aurum
```

### **檢查磁盤使用**

```bash
# 監控快取大小
du -sh /opt/aurum_infinity_ai/cache/

# 設定磁盤清理策略（可選）
# 每週清理 30 天以前的快取
crontab -e
```

新增：
```
0 3 * * 0 find /opt/aurum_infinity_ai/cache -type f -mtime +30 -delete
```

---

## 🔄 常見操作

### **重啟服務**

```bash
sudo systemctl restart aurum
sudo systemctl reload nginx
```

### **檢查服務日誌**

```bash
sudo journalctl -u aurum -n 50 -f
```

### **更新應用代碼**

```bash
cd /opt/aurum_infinity_ai
sudo -u aurum git pull origin main
sudo systemctl restart aurum
```

### **備份快取**

```bash
# 備份快取到 S3
aws s3 sync /opt/aurum_infinity_ai/cache/ \
  s3://your-bucket/aurum_cache_$(date +%Y%m%d)/

# 或使用本地備份
sudo tar -czf /backup/aurum_cache_$(date +%Y%m%d).tar.gz \
  /opt/aurum_infinity_ai/cache/
```

---

## ⚠️ 故障排查

### **API 返回 404**

```
原因: 快取檔案不存在
解決: 訪問網頁 UI 觸發分析以生成快取
```

### **503 Service Unavailable**

```
原因: Gunicorn 服務未啟動或當機
解決:
  sudo systemctl restart aurum
  sudo journalctl -u aurum -f （檢查日誌）
```

### **SSL 證書過期**

```
解決:
  sudo certbot renew --force-renewal
  sudo systemctl reload nginx
```

### **磁盤空間不足**

```
解決:
  find /opt/aurum_infinity_ai/cache -type f -mtime +60 -delete
  或手動刪除舊快取
```

---

## 📈 性能優化

### **增加 Gunicorn 工作進程**

編輯 `/etc/systemd/system/aurum.service`：
```ini
ExecStart=/opt/aurum_infinity_ai/venv/bin/gunicorn \
  --workers 8 \  # 根據 CPU 核心數調整
  ...
```

### **啟用 Nginx 快取**

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=aurum:10m;

location /api/markdown/ {
    proxy_cache aurum;
    proxy_cache_valid 200 1h;
    proxy_cache_use_stale error timeout updating;
}
```

---

## 🔐 安全檢查清單

- [ ] `.env` 檔案權限設為 600（只有所有者可讀寫）
- [ ] 使用 HTTPS（SSL/TLS 已啟用）
- [ ] Nginx 加入安全標頭
- [ ] 防火牆只開放必要端口（80, 443, 22）
- [ ] 定期更新系統和依賴
- [ ] 配置 fail2ban 防止暴力破解（可選）
- [ ] 備份 API Key 和敏感配置

---

## 📞 技術支援

| 項目 | 聯絡資訊 |
|------|----------|
| 緊急問題 | 致電 Aaron |
| 功能請求 | aaron@auincap.com |
| 文檔更新 | GitHub Issues |

---

**部署完成日期**: _______________
**負責人**: _______________
**驗證人**: _______________
