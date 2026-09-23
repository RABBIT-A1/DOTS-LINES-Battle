# 点线大作战（DOTS & LINES Battle）

一款使用 Python + Pygame CE 制作的 2D 单人对 AI 回合制画线游戏。  
玩家控制一个点，通过按住鼠标画出轨迹；线条穿过对方的点即可击败对手。

## 游戏特点

- LoFi 日系动画插画风格界面
- 鼠标相对轨迹映射，点不会直接追赶光标绝对位置
- 自动检测方向反转，一次行动最多完成一次明显掉头
- 快速、连续画线检测；无效画线会回到回合起点重试
- 出击回合、地图边界回退与出生区域规则
- 内置 AI 对手，包含随机出击、寻敌、瞄准偏差和掉头行为
- 点碎裂、轻微屏幕震动、顶部消息反馈
- UI、画线、掉头、无效画线、击杀和胜利音效

## 环境要求

- Python 3.11 或更高版本
- Pygame CE 2.1.3 或更高版本
- Windows 优先支持，其他桌面系统理论上也可运行

## 安装

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 运行

推荐入口：

```powershell
python -m src.main
```

也可以运行兼容入口：

```powershell
python prototype.py
```

## 操作说明

### 标题与规则页面

- 点击“开始游戏”或按 `Enter` / `Space`：开始游戏
- 点击“查看规则”或按 `R`：打开规则页
- 规则页使用 `←` / `→` 切换章节
- `Esc`：返回标题或退出当前对局

### 对局操作

- 按住鼠标左键：开始画线，点跟随鼠标移动轨迹
- 松开鼠标左键：确认画线并结束当前行动
- 移动方向明显反转：自动判定为掉头
- 一次行动只允许一次明显掉头
- 第二次方向反转会立即停止并结算当前轨迹
- 画线过慢、停顿或不连续时，点会回到本回合起点，可继续尝试

## 项目结构

```text
.
├── README.md
├── requirements.txt
├── prototype.py
├── src/
│   ├── main.py
│   ├── game.py
│   ├── player.py
│   ├── line.py
│   ├── collision.py
│   ├── map.py
│   ├── ai.py
│   ├── renderer.py
│   ├── input_handler.py
│   ├── effects.py
│   ├── audio.py
│   ├── ui.py
│   ├── theme.py
│   ├── skill_system.py
│   ├── geometry.py
│   └── config.py
└── assets/
    └── audio/
```

## 音效

音效文件位于 `assets/audio/`。游戏在启动时自动加载；如果音频设备不可用，游戏仍可正常运行，只是不会播放声音。

## 安全说明

- 游戏本体不进行网络请求
- 不上传玩家数据，不包含遥测功能
- 不需要 API Key、账号或登录
- 仓库不包含 `.env`、私钥、凭据或个人本地路径

## 隐私与产物

构建产物、虚拟环境、缓存、日志、密钥文件和本地预览输出均已加入 `.gitignore`。  
公开仓库只包含可运行游戏所需源码、依赖说明和音频资源。
