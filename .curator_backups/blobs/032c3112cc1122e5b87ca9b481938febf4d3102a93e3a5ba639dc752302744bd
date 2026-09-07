# Docker 网络模式排查

容器内开的端口宿主机收不到时，先确认实际网络模式：

## 判断方法

```bash
cat /sys/class/net/eth0/address
# 02:42:ac:12:00:02  → Docker bridge 模式（虚拟网卡）
# 宿主机真实 MAC     → host 模式
```

Docker bridge 模式下容器的 IP 段通常是 `172.17-18.x.x`，MAC 地址以 `02:42` 开头。

## 症状对照

| 现象 | 原因 |
|:----|:----|
| `docker-compose.yml` 写着 `network_mode: host` 但 eth0 是 02:42 MAC | compose 修改后未重建容器，实际仍用旧配置 |
| 容器内 `curl localhost:8080` 返回 200，但宿主机 IP:8080 不通 | bridge 模式，端口未映射到宿主机 |
| `hostname -I` 返回 172.x.x.x | 容器的内部 IP，非宿主机 LAN IP |

## 修复方案

### 方案 A：端口映射（推荐）
修改 `docker-compose.yml`，改 `network_mode: bridge` 并添加 `ports`：

```yaml
services:
  your-service:
    # network_mode: host   ← 注释掉或改为 bridge
    ports:
      - "23456:23456"
      - "23457:23457"
```

然后重建：
```bash
docker compose down && docker compose up -d
```

### 方案 B：SSH 隧道（无需改容器）
在客户端电脑上：
```bash
ssh -L 23457:localhost:23457 -L 23456:localhost:23456 user@host_ip
```
然后浏览器打开 `http://localhost:23457`
