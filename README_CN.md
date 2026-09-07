# Rikka-Live

![Rikka-Live](./assets/banner.cn.jpg)

一个以弥生月六花为中心的语音交互 AI 伴侣。启动服务后，可以在浏览器中与六花文字或语音交流，并通过 Live2D、字幕和桌面 Overlay 看到她的回应。

## 功能

- 文字聊天：输入消息，与角色进行连续对话。
- 语音对话：使用麦克风讲话，接收语音回复；也支持打断正在播放的回复。
- Live2D 互动：显示角色表情、动作和口型，并支持鼠标交互。
- Overlay 桌宠：打开透明 Overlay，将角色放在桌面或直播画面上，并显示字幕气泡。
- 角色定制：修改角色名称、称呼、人设提示词、头像和 Live2D 模型。
- 多种音色：可以使用在线语音，也可以接入云端 IndexTTS2 等服务使用自定义音色。
- 画面感知：可选捕获摄像头、屏幕或窗口画面，让角色根据画面内容回应。
- 主动交流：允许角色在空闲时主动说话，也可以通过测试台手动触发。
- 聊天记录：保留历史对话，方便继续之前的交流。
- 直播互动：可选连接 Bilibili 房间，接收弹幕并让角色回应。
- 调试工具：查看服务状态、事件流、日志，并单独测试语音、Live2D、麦克风和画面捕获。

## 运行前准备

需要准备：

- Windows、macOS 或 Linux；
- Python 3.10–3.12；
- Git；
- [uv](https://docs.astral.sh/uv/getting-started/installation/)；
- 一个可用的对话服务配置；
- 一个可用的语音合成配置。

仓库中的 `frontend` 是子模块。建议克隆时直接初始化子模块，否则第一次打开网页时可能看不到前端页面。

## 安装与启动

### 1. 克隆项目

```bash
git clone --recurse-submodules <你的 GitHub 仓库地址>
cd <项目目录>
```

如果项目已经克隆但没有前端文件，执行：

```bash
git submodule update --init --recursive
```

### 2. 安装依赖

在项目根目录执行：

```bash
uv sync
```

### 3. 创建配置文件

Windows PowerShell：

```powershell
Copy-Item ./config_templates/conf.ZH.default.yaml ./conf.yaml
```

Linux 或 macOS：

```bash
cp config_templates/conf.ZH.default.yaml conf.yaml
```

`conf.yaml` 是本机配置文件，不要提交到 GitHub。项目启动时如果发现配置文件不存在，也会尝试从模板生成一份。

### 4. 启动服务

```bash
uv run run_server.py
```

需要查看详细日志时：

```bash
uv run run_server.py --verbose
```

请始终在包含 `run_server.py` 和 `conf.yaml` 的项目目录中启动服务。

## 配置说明

所有主要配置都在 `conf.yaml` 中。可以先修改下面几项，其他配置保持默认即可。

### 对话服务

在 `character_config.agent_config` 中选择对话服务，并填写对应的地址、模型和密钥。例如使用 OpenAI 兼容接口：

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: openai_compatible_llm
    llm_configs:
      openai_compatible_llm:
        base_url: https://你的服务地址/v1
        model: 你的模型名称
        llm_api_key: 你的 API Key
```

不同服务只需要切换 `llm_provider`，并填写模板中对应的配置段。

### 语音合成

选择一个 TTS 配置。无需额外密钥的快速试用可以使用在线语音：

```yaml
character_config:
  tts_config:
    tts_model: edge_tts
    edge_tts:
      voice: zh-CN-XiaoxiaoNeural
```

使用云端 IndexTTS2 自定义音色时：

```yaml
character_config:
  tts_config:
    tts_model: indextts2_tts
    indextts2_tts:
      mode: cloud
      api_key: 你的 ModelVerse API Key
      base_url: https://api.modelverse.cn/v1
      model: IndexTeam/IndexTTS-2
      voice_id: 你的云端音色 ID
```

音色 ID 和 API Key 要使用你自己账号下有权限的内容。参考音频、密钥和 `conf.yaml` 不会随仓库发布。

### 角色和 Live2D

```yaml
character_config:
  character_name: 弥生月六花
  human_name: 你的称呼
  live2d_model_name: mao_pro
  persona_prompt: 角色的人设和说话方式
```

`live2d_model_name` 必须对应 `live2d-models/` 下的模型目录。个人 Live2D 模型不包含在公开仓库中，需要自行复制到该目录后再修改名称。

### 语音识别

如果暂时只想使用文字聊天，可以关闭语音识别：

```yaml
character_config:
  asr_config:
    asr_model: null
```

需要使用麦克风时，将 `asr_model` 改为模板中可用的识别方案，并按该方案填写模型或 API 配置。

### 服务地址和端口

```yaml
system_config:
  host: localhost
  port: 12393
```

默认只允许本机访问。若需要让同一局域网的其他设备访问，可将 `host` 改为 `0.0.0.0`，但麦克风功能在远程访问时需要 HTTPS 安全环境。

## 页面地址

服务启动后，在浏览器打开：

| 页面 | 地址（默认端口） | 用途 |
| --- | --- | --- |
| 主交互页面 | <http://127.0.0.1:12393/> | 文字聊天、语音交流、Live2D 互动 |
| Rikka 配置与诊断页 | <http://127.0.0.1:12393/web-tool/rikka.html> | 修改运行配置、测试 TTS、查看状态和日志 |
| ASR / TTS 测试页 | <http://127.0.0.1:12393/web-tool/> | 单独测试语音识别和语音合成 |
| Overlay 页面 | <http://127.0.0.1:12393/overlay/> | 透明角色、字幕和桌宠显示 |

如果把 `system_config.port` 改成了 `12395`，将上面地址中的 `12393` 全部替换为 `12395`。

## 使用流程

1. 启动服务并打开主交互页面。
2. 在设置中确认角色和连接地址，输入一条消息测试对话。
3. 允许浏览器使用麦克风后，可以直接讲话；AI 播放语音时再次讲话即可尝试打断。
4. 打开摄像头或屏幕捕获后，可以询问角色“你能看到什么”。相关功能需要对话服务支持画面理解。
5. 打开 Overlay 页面，将角色和字幕放到桌面或直播软件中。
6. 打开 Rikka 配置与诊断页，在“测试台”中使用 `Debug Speak` 和“试听”确认 TTS、口型、动作和字幕是否正常。
7. 需要主动交流时，在配置页开启主动发言；需要直播互动时，填写房间号和登录信息后连接 Bilibili 弹幕。

## Rikka 配置页能做什么

配置页中的设置分为几组：

- **总览**：查看服务、前端、LLM、TTS、Overlay 和麦克风状态。
- **测试台**：测试完整播报、Live2D/Overlay、画面捕获、主动发言和麦克风。
- **事件与 Flow**：查看最近事件以及一轮对话经过的阶段。
- **配置**：调整 LLM、TTS、ASR、Overlay、画面捕获、主动发言和直播配置。
- **日志**：查看最近日志和错误信息。

配置页中的部分修改可以立即应用，涉及服务初始化的修改会提示重启服务后生效。密钥输入框留空表示不修改原有密钥。

## 常见问题

### 页面显示 `Not Found`

通常是前端子模块没有初始化：

```bash
git submodule update --init --recursive
```

然后重新启动服务。

### 能聊天但没有声音

检查 `character_config.tts_config.tts_model` 是否和实际填写的配置段一致，并确认 API Key、音色 ID 或本地服务地址可用。也可以先切换到 `edge_tts` 验证其他功能。

### 能发声但不能语音输入

检查 `asr_config.asr_model` 是否为 `null`，确认浏览器已经获得麦克风权限，并尽量使用 `localhost` 打开页面。远程访问时需要配置 HTTPS。

### 找不到自己的 Live2D

确认模型目录位于 `live2d-models/<模型名>`，并让 `live2d_model_name` 与目录名完全一致。个人模型不会随公开仓库提供。

### 端口被占用

修改 `system_config.port` 后重新启动，并使用新端口访问页面。

## 更新项目

```bash
git pull --recurse-submodules
git submodule update --init --recursive
uv sync
```

如果配置文件提示需要升级，先备份 `conf.yaml`，再按启动日志提示运行升级脚本：

```bash
uv run upgrade.py
```

## 安全与隐私

请不要把以下内容提交到 GitHub：

- `conf.yaml`；
- LLM、TTS、ASR 等 API Key；
- Bilibili `SESSDATA` 等登录凭据；
- 私人参考音频和自定义 Live2D；
- 本地日志、缓存和聊天记录。

这些内容已通过 `.gitignore` 排除，但提交前仍应检查 Git 状态和差异。

## 许可证

本项目代码沿用上游项目的许可证，详见 [`LICENSE`](./LICENSE)。仓库中的 Live2D 样本模型受 Live2D Inc. 的单独许可约束，不自动包含在代码许可证中。商业使用前请确认相关模型和音频资源的授权范围。

本项目基于 [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) 进行定制。
