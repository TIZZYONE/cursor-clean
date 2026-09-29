# Cursor 把 C 盘吃掉 20GB？我写了个开源清理工具 cursor-clean

> 适用：微信公众号 / CSDN。可直接复制，按需改作者名与 GitHub 链接。

---

## 开头（痛点）

用 Cursor 写代码越久，C 盘越慌。

有一天我用磁盘分析工具扫了一眼，发现：

**`C:\Users\...\AppData\Roaming\Cursor` 居然将近 20GB。**

第一反应：是不是缓存炸了？项目索引？扩展？

点进去一看，真正的大头其实是这些：

| 内容 | 大约占用 | 是什么 |
|------|----------|--------|
| `state.vscdb` | ~11GB | 本地状态库：聊天、Agent、Composer 历史 |
| `state.vscdb.backup` | ~4GB | 上面的备份 |
| `cursor-agent` 多版本 | ~2GB | 历史版本的 Agent CLI 安装包 |
| 其他缓存/日志 | 少量 | CachedData、logs 等 |

结论很明确：

> **不是项目文件占空间，是 Cursor 自己把聊天和 Agent 历史越堆越多。**

几个月前的对话，对我来说基本没用，但它一直躺在 SSD 里。

官方设置里又没有「只保留最近 90 天」这种开关。于是我写了个小工具。

---

## 工具介绍：cursor-clean

**cursor-clean** 是一个轻量 Python 命令行工具：

- 扫描 Cursor Roaming 目录，告诉你哪些能删
- 默认只保留最近 **90 天**聊天（可改）
- 旧的 `cursor-agent` 版本只留最新一份
- **不删** `state.vscdb.backup`（备份保留）
- **零第三方依赖**，不建自己的数据库
- 支持中文 / 英文界面
- 先扫描、再确认，避免误删

PyPI：https://pypi.org/project/cursor-clean/

（开源仓库：把你的 GitHub 地址贴这里）

---

## 一分钟上手

环境：Windows + Python 3.9+

```bash
pip install -U cursor-clean
```

**重要：清理前先完全退出 Cursor**  
（任务管理器里确认没有 `Cursor.exe`，否则压缩数据库可能卡住。）

```bash
# 先看能清什么（可选手动选中文）
cursor-clean scan --lang zh

# 确认后清理
cursor-clean clean --lang zh
```

常用参数：

```bash
# 只保留 60 天
cursor-clean clean --lang zh --keep-days 60

# 非交互一键清
cursor-clean clean -y --lang zh

# 只删旧 agent 版本 / 只压缩数据库
cursor-clean clean-agents -y --lang zh
cursor-clean vacuum --lang zh
```

---

## 它到底删什么、不删什么

**会处理：**

1. 超过保留期的 Composer / Agent 会话数据  
2. 除最新版以外的 `cursor-agent` 安装目录  
3. （可选）CachedData、logs  

**刻意不碰：**

- `state.vscdb.backup`  
- 你的项目代码  
- Cursor 的设置文件（正常情况下）

聊天是否过期，按会话的「最后更新时间 / 创建时间」判断。

---

## 我实测时踩过的坑（帮你避雷）

### 1. 点了 Y 之后「卡住」

其实多半在干活，尤其是最后一步 **VACUUM（压缩数据库）**。

11GB 的 SQLite 压缩可能要好几分钟，而且：

> **Cursor 没退干净时，VACUUM 会抢不到锁，看起来像死机。**

正确姿势：任务管理器清掉所有 Cursor 进程，再跑 `cursor-clean vacuum`。

### 2. 聊天删了，磁盘却没变小

DELETE 只是把记录标删了，文件大小要靠 **VACUUM** 才会掉下来。  
所以工具会默认做 VACUUM；若中途失败，单独执行：

```bash
cursor-clean vacuum --lang zh
```

### 3. 备份要不要删？

我建议 **先不删**。  
几 GB 的 backup 换一点安全感，值。工具默认也保留。

---

## 为什么做成开源 pip 包？

- 希望别人装完就能用：`pip install cursor-clean`
- 逻辑简单，方便审计：就是扫目录 + 改 Cursor 自己的 `state.vscdb` + 删旧文件夹
- 不想引入一堆依赖，也不想再搞一个「清理工具自己的数据库」

技术栈很朴素：Python 标准库 + SQLite（只用来读写 Cursor 已有的库）。

---

## 写在最后

Cursor 很强，但本地状态也会悄悄长大。

如果你也发现 Roaming\Cursor 动辄十几 GB：

1. 先 `scan` 看清楚  
2. 退出 Cursor  
3. 再 `clean`  

腾出的往往不是几百 MB，而是数 GB。

欢迎 Star、提 Issue，也欢迎把你的清理前后对比发在评论区。

---

**安装：**

```bash
pip install -U cursor-clean
```

**项目页：**

- PyPI：https://pypi.org/project/cursor-clean/  
- GitHub：（发布后填写）

#Cursor #Python #磁盘清理 #开发者工具 #开源
