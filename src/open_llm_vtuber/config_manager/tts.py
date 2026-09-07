# config_manager/tts.py
from pydantic import ValidationInfo, Field, model_validator
from typing import Literal, Optional, Dict, ClassVar
from ..tts.indextts2_emotion import (
    DEFAULT_QUIET_COMPANION_VECTOR,
    clamp_quiet_companion_alpha,
    normalize_emotion_vector,
)
from .i18n import I18nMixin, Description


class AzureTTSConfig(I18nMixin):
    """Configuration for Azure TTS service."""

    api_key: str = Field(..., alias="api_key")
    region: str = Field(..., alias="region")
    voice: str = Field(..., alias="voice")
    pitch: str = Field(..., alias="pitch")
    rate: str = Field(..., alias="rate")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Azure TTS service", zh="Azure TTS 服务的 API 密钥"
        ),
        "region": Description(
            en="Azure region (e.g., eastus)", zh="Azure 区域（如 eastus）"
        ),
        "voice": Description(
            en="Voice name to use for Azure TTS", zh="Azure TTS 使用的语音名称"
        ),
        "pitch": Description(en="Pitch adjustment percentage", zh="音高调整百分比"),
        "rate": Description(en="Speaking rate adjustment", zh="语速调整"),
    }


class BarkTTSConfig(I18nMixin):
    """Configuration for Bark TTS."""

    voice: str = Field(..., alias="voice")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "voice": Description(
            en="Voice name to use for Bark TTS", zh="Bark TTS 使用的语音名称"
        ),
    }


class EdgeTTSConfig(I18nMixin):
    """Configuration for Edge TTS."""

    voice: str = Field(..., alias="voice")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "voice": Description(
            en="Voice name to use for Edge TTS (use 'edge-tts --list-voices' to list available voices)",
            zh="Edge TTS 使用的语音名称（使用 'edge-tts --list-voices' 列出可用语音）",
        ),
    }


class CosyvoiceTTSConfig(I18nMixin):
    """Configuration for Cosyvoice TTS."""

    client_url: str = Field(..., alias="client_url")
    mode_checkbox_group: str = Field(..., alias="mode_checkbox_group")
    sft_dropdown: str = Field(..., alias="sft_dropdown")
    prompt_text: str = Field(..., alias="prompt_text")
    prompt_wav_upload_url: str = Field(..., alias="prompt_wav_upload_url")
    prompt_wav_record_url: str = Field(..., alias="prompt_wav_record_url")
    instruct_text: str = Field(..., alias="instruct_text")
    seed: int = Field(..., alias="seed")
    api_name: str = Field(..., alias="api_name")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "client_url": Description(
            en="URL of the CosyVoice Gradio web UI", zh="CosyVoice Gradio Web UI 的 URL"
        ),
        "mode_checkbox_group": Description(
            en="Mode checkbox group value", zh="模式复选框组值"
        ),
        "sft_dropdown": Description(en="SFT dropdown value", zh="SFT 下拉框值"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "prompt_wav_upload_url": Description(
            en="URL for prompt WAV file upload", zh="提示音频文件上传 URL"
        ),
        "prompt_wav_record_url": Description(
            en="URL for prompt WAV file recording", zh="提示音频文件录制 URL"
        ),
        "instruct_text": Description(en="Instruction text", zh="指令文本"),
        "seed": Description(en="Random seed", zh="随机种子"),
        "api_name": Description(en="API endpoint name", zh="API 端点名称"),
    }


class Cosyvoice2TTSConfig(I18nMixin):
    """Configuration for Cosyvoice2 TTS."""

    client_url: str = Field(..., alias="client_url")
    mode_checkbox_group: str = Field(..., alias="mode_checkbox_group")
    sft_dropdown: str = Field(..., alias="sft_dropdown")
    prompt_text: str = Field(..., alias="prompt_text")
    prompt_wav_upload_url: str = Field(..., alias="prompt_wav_upload_url")
    prompt_wav_record_url: str = Field(..., alias="prompt_wav_record_url")
    instruct_text: str = Field(..., alias="instruct_text")
    stream: bool = Field(..., alias="stream")
    seed: int = Field(..., alias="seed")
    speed: float = Field(..., alias="speed")
    api_name: str = Field(..., alias="api_name")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "client_url": Description(
            en="URL of the CosyVoice Gradio web UI", zh="CosyVoice Gradio Web UI 的 URL"
        ),
        "mode_checkbox_group": Description(
            en="Mode checkbox group value", zh="模式复选框组值"
        ),
        "sft_dropdown": Description(en="SFT dropdown value", zh="SFT 下拉框值"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "prompt_wav_upload_url": Description(
            en="URL for prompt WAV file upload", zh="提示音频文件上传 URL"
        ),
        "prompt_wav_record_url": Description(
            en="URL for prompt WAV file recording", zh="提示音频文件录制 URL"
        ),
        "instruct_text": Description(en="Instruction text", zh="指令文本"),
        "stream": Description(en="Streaming inference", zh="流式推理"),
        "seed": Description(en="Random seed", zh="随机种子"),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
        "api_name": Description(en="API endpoint name", zh="API 端点名称"),
    }


class MeloTTSConfig(I18nMixin):
    """Configuration for Melo TTS."""

    speaker: str = Field(..., alias="speaker")
    language: str = Field(..., alias="language")
    device: str = Field("auto", alias="device")
    speed: float = Field(1.0, alias="speed")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "speaker": Description(
            en="Speaker name (e.g., EN-Default, ZH)",
            zh="说话人名称（如 EN-Default、ZH）",
        ),
        "language": Description(
            en="Language code (e.g., EN, ZH)", zh="语言代码（如 EN、ZH）"
        ),
        "device": Description(
            en="Device to use (auto, cpu, cuda, cuda:0, mps)",
            zh="使用的设备（auto、cpu、cuda、cuda:0、mps）",
        ),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
    }


class XTTSConfig(I18nMixin):
    """Configuration for XTTS."""

    api_url: str = Field(..., alias="api_url")
    speaker_wav: str = Field(..., alias="speaker_wav")
    language: str = Field(..., alias="language")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_url": Description(
            en="URL of the XTTS API endpoint", zh="XTTS API 端点的 URL"
        ),
        "speaker_wav": Description(
            en="Speaker reference WAV file", zh="说话人参考音频文件"
        ),
        "language": Description(
            en="Language code (e.g., en, zh)", zh="语言代码（如 en、zh）"
        ),
    }


class GPTSoVITSConfig(I18nMixin):
    """Configuration for GPT-SoVITS."""

    api_url: str = Field(..., alias="api_url")
    text_lang: str = Field(..., alias="text_lang")
    ref_audio_path: str = Field(..., alias="ref_audio_path")
    prompt_lang: str = Field(..., alias="prompt_lang")
    prompt_text: str = Field(..., alias="prompt_text")
    text_split_method: str = Field(..., alias="text_split_method")
    batch_size: str = Field(..., alias="batch_size")
    media_type: str = Field(..., alias="media_type")
    streaming_mode: str = Field(..., alias="streaming_mode")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_url": Description(
            en="URL of the GPT-SoVITS API endpoint", zh="GPT-SoVITS API 端点的 URL"
        ),
        "text_lang": Description(en="Language of the input text", zh="输入文本的语言"),
        "ref_audio_path": Description(
            en="Path to reference audio file", zh="参考音频文件路径"
        ),
        "prompt_lang": Description(en="Language of the prompt", zh="提示词语言"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "text_split_method": Description(
            en="Method for splitting text", zh="文本分割方法"
        ),
        "batch_size": Description(en="Batch size for processing", zh="处理批次大小"),
        "media_type": Description(en="Output media type", zh="输出媒体类型"),
        "streaming_mode": Description(en="Enable streaming mode", zh="启用流式模式"),
    }


class FishAPITTSConfig(I18nMixin):
    """Configuration for Fish API TTS."""

    api_key: str = Field(..., alias="api_key")
    reference_id: str = Field(..., alias="reference_id")
    latency: Literal["normal", "balanced"] = Field(..., alias="latency")
    base_url: str = Field(..., alias="base_url")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Fish TTS service", zh="Fish TTS 服务的 API 密钥"
        ),
        "reference_id": Description(
            en="Voice reference ID from Fish Audio website",
            zh="来自 Fish Audio 网站的语音参考 ID",
        ),
        "latency": Description(
            en="Latency mode (normal or balanced)", zh="延迟模式（normal 或 balanced）"
        ),
        "base_url": Description(
            en="Base URL for Fish TTS API", zh="Fish TTS API 的基础 URL"
        ),
    }


class CoquiTTSConfig(I18nMixin):
    """Configuration for Coqui TTS."""

    model_name: str = Field(..., alias="model_name")
    speaker_wav: str = Field("", alias="speaker_wav")
    language: str = Field(..., alias="language")
    device: str = Field("", alias="device")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_name": Description(
            en="Name of the TTS model to use", zh="要使用的 TTS 模型名称"
        ),
        "speaker_wav": Description(
            en="Path to speaker WAV file for voice cloning",
            zh="用于声音克隆的说话人音频文件路径",
        ),
        "language": Description(
            en="Language code (e.g., en, zh)", zh="语言代码（如 en、zh）"
        ),
        "device": Description(
            en="Device to use (cuda, cpu, or empty for auto)",
            zh="使用的设备（cuda、cpu 或留空以自动选择）",
        ),
    }


class SherpaOnnxTTSConfig(I18nMixin):
    """Configuration for Sherpa Onnx TTS."""

    vits_model: str = Field(..., alias="vits_model")
    vits_lexicon: Optional[str] = Field(None, alias="vits_lexicon")
    vits_tokens: str = Field(..., alias="vits_tokens")
    vits_data_dir: Optional[str] = Field(None, alias="vits_data_dir")
    vits_dict_dir: Optional[str] = Field(None, alias="vits_dict_dir")
    tts_rule_fsts: Optional[str] = Field(None, alias="tts_rule_fsts")
    max_num_sentences: int = Field(2, alias="max_num_sentences")
    sid: int = Field(1, alias="sid")
    provider: Literal["cpu", "cuda", "coreml"] = Field("cpu", alias="provider")
    num_threads: int = Field(1, alias="num_threads")
    speed: float = Field(1.0, alias="speed")
    debug: bool = Field(False, alias="debug")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "vits_model": Description(en="Path to VITS model file", zh="VITS 模型文件路径"),
        "vits_lexicon": Description(
            en="Path to lexicon file (optional)", zh="词典文件路径（可选）"
        ),
        "vits_tokens": Description(en="Path to tokens file", zh="词元文件路径"),
        "vits_data_dir": Description(
            en="Path to espeak-ng data directory (optional)",
            zh="espeak-ng 数据目录路径（可选）",
        ),
        "vits_dict_dir": Description(
            en="Path to Jieba dictionary directory (optional)",
            zh="结巴词典目录路径（可选）",
        ),
        "tts_rule_fsts": Description(
            en="Path to rule FSTs file (optional)", zh="规则 FST 文件路径（可选）"
        ),
        "max_num_sentences": Description(
            en="Maximum number of sentences per batch", zh="每批次最大句子数"
        ),
        "sid": Description(
            en="Speaker ID for multi-speaker models", zh="多说话人模型的说话人 ID"
        ),
        "provider": Description(
            en="Computation provider (cpu, cuda, or coreml)",
            zh="计算提供者（cpu、cuda 或 coreml）",
        ),
        "num_threads": Description(en="Number of computation threads", zh="计算线程数"),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
        "debug": Description(en="Enable debug mode", zh="启用调试模式"),
    }


class SiliconFlowTTSConfig(I18nMixin):
    """Configuration for SiliconFlow TTS."""

    api_url: str = Field("https://api.siliconflow.cn/v1/audio/speech", alias="api_url")
    api_key: str = Field(..., alias="api_key")
    default_model: str = Field("FunAudioLLM/CosyVoice2-0.5B", alias="default_model")
    default_voice: str = Field(
        "speech:Dreamflowers:5bdstvc39i:xkqldnpasqmoqbakubom", alias="default_voice"
    )
    sample_rate: int = Field(32000, alias="sample_rate")
    response_format: str = Field("mp3", alias="response_format")
    stream: bool = Field(True, alias="stream")
    speed: float = Field(1, alias="speed")
    gain: int = Field(0, alias="gain")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for SiliconFlow TTS service",
            zh="SiliconFlow TTS 服务的 API 密钥",
        ),
        "url": Description(
            en="API endpoint URL for SiliconFlow TTS",
            zh="SiliconFlow TTS 的 API 端点 URL",
        ),
        "model": Description(
            en="Model to use for SiliconFlow TTS", zh="SiliconFlow TTS 使用的模型"
        ),
        "voice": Description(
            en="Voice name to use for SiliconFlow TTS",
            zh="SiliconFlow TTS 使用的语音名称",
        ),
        "sample_rate": Description(
            en="Sample rate of the output audio", zh="输出音频的采样率"
        ),
        "stream": Description(en="Enable streaming mode", zh="启用流式模式"),
        "speed": Description(en="Speaking speed multiplier", zh="语速倍数"),
        "gain": Description(en="Audio gain adjustment", zh="音频增益调整"),
    }


class OpenAITTSConfig(I18nMixin):
    """Configuration for OpenAI-compatible TTS client."""

    model: Optional[str] = Field(None, alias="model")
    voice: Optional[str] = Field(None, alias="voice")
    api_key: Optional[str] = Field(None, alias="api_key")
    base_url: Optional[str] = Field(None, alias="base_url")
    file_extension: Literal["mp3", "wav"] = Field("mp3", alias="file_extension")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model": Description(
            en="Model name for the TTS server (overrides default)",
            zh="TTS 服务器的模型名称（覆盖默认值）",
        ),
        "voice": Description(
            en="Voice name(s) for the TTS server (overrides default)",
            zh="TTS 服务器的语音名称（覆盖默认值）",
        ),
        "api_key": Description(
            en="API key if required by the TTS server (overrides default)",
            zh="TTS 服务器所需的 API 密钥（覆盖默认值）",
        ),
        "base_url": Description(
            en="Base URL of the TTS server (overrides default)",
            zh="TTS 服务器的基础 URL（覆盖默认值）",
        ),
        "file_extension": Description(
            en="Audio file format (mp3 or wav, defaults to mp3)",
            zh="音频文件格式（mp3 或 wav，默认为 mp3）",
        ),
    }


class SparkTTSConfig(I18nMixin):
    """Configuration for Spark TTS."""

    api_url: str = Field(..., alias="api_url")
    prompt_wav_upload: str = Field(..., alias="prompt_wav_upload")
    api_name: str = Field(..., alias="api_name")
    gender: str = Field(..., alias="gender")
    pitch: int = Field(..., alias="pitch")
    speed: int = Field(..., alias="speed")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "prompt_wav_upload": Description(
            en="Reference audio (used when using voice cloning)",
            zh="参考音频（使用语音克隆时候使用）",
        ),
        "api_url": Description(
            en="API address of the spark tts gradio web frontend. For example: http://127.0.0.1:7860/voice_clone",
            zh="你的API地址。举例：http://127.0.0.1:7860/voice_clone",
        ),
        "api_name": Description(
            en="The API endpoint name. For example: voice_clone,voice_creation",
            zh="你的API名称。举例：voice_clone，voice_creation",
        ),
        "gender": Description(
            en="Gender of the voice (male or female)", zh="声音性别（男或女）"
        ),
        "pitch": Description(
            en="Pitch shift (in semitones) default 3,range 1-5.",
            zh="音高（以半音为单位）默认3，范围1-5",
        ),
        "speed": Description(
            en="Speed of the voice (in percent) default 3,range 1-5.",
            zh="声音速度（以百分比为单位）默认3，范围1-5",
        ),
    }


class MinimaxTTSConfig(I18nMixin):
    """Configuration for Minimax TTS."""

    group_id: str = Field(..., alias="group_id")
    api_key: str = Field(..., alias="api_key")
    model: str = Field("speech-02-turbo", alias="model")
    voice_id: str = Field("male-qn-qingse", alias="voice_id")
    pronunciation_dict: str = Field("", alias="pronunciation_dict")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "group_id": Description(en="Minimax group_id", zh="Minimax 的 group_id"),
        "api_key": Description(en="Minimax API key", zh="Minimax 的 API key"),
        "model": Description(en="Minimax model name", zh="Minimax 模型名称"),
        "voice_id": Description(en="Minimax voice id", zh="Minimax 语音 id"),
        "pronunciation_dict": Description(
            en="Custom pronunciation dictionary (string)", zh="自定义发音字典（字符串）"
        ),
    }


class XiaomiMimoTTSConfig(I18nMixin):
    """Configuration for Xiaomi MiMo V2.5 TTS."""

    api_key: str = Field("", alias="api_key")
    base_url: str = Field("https://api.xiaomimimo.com/v1", alias="base_url")
    model: str = Field("mimo-v2.5-tts", alias="model")
    voice: str = Field("mimo_default", alias="voice")
    voice_design_prompt: str = Field(
        "A young Chinese woman with a clear, gentle, slightly cool voice; "
        "soft but lively, suitable for a virtual livestream companion.",
        alias="voice_design_prompt",
    )
    voice_audio_path: str = Field("", alias="voice_audio_path")
    voice_audio_base64: str = Field("", alias="voice_audio_base64")
    voice_mime_type: Literal["audio/mpeg", "audio/mp3", "audio/wav"] = Field(
        "audio/mpeg",
        alias="voice_mime_type",
    )
    style_prompt: str = Field(
        "温柔、克制、清澈，语速略慢，像在直播中轻轻回应观众。",
        alias="style_prompt",
    )
    audio_format: Literal["wav", "mp3"] = Field("wav", alias="audio_format")
    optimize_text_preview: bool = Field(False, alias="optimize_text_preview")
    timeout_seconds: float = Field(45.0, alias="timeout_seconds")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(en="Xiaomi MiMo API key", zh="小米 MiMo API 密钥"),
        "base_url": Description(
            en="Xiaomi MiMo OpenAI-compatible base URL",
            zh="小米 MiMo OpenAI 兼容接口基础 URL",
        ),
        "model": Description(
            en="MiMo V2.5 TTS model id", zh="MiMo V2.5 TTS 模型 ID"
        ),
        "voice": Description(
            en="Preset voice id for mimo-v2.5-tts",
            zh="mimo-v2.5-tts 预设音色 ID",
        ),
        "voice_design_prompt": Description(
            en="Voice description used by mimo-v2.5-tts-voicedesign",
            zh="mimo-v2.5-tts-voicedesign 使用的音色描述",
        ),
        "voice_audio_path": Description(
            en="Local mp3/wav voice sample path for voice cloning",
            zh="用于音色复刻的本地 mp3/wav 参考音频路径",
        ),
        "voice_audio_base64": Description(
            en="Raw base64 voice sample. If no data URI prefix is present, one is added.",
            zh="参考音频 base64。未带 data URI 前缀时会自动补齐。",
        ),
        "voice_mime_type": Description(
            en="MIME type for the voice sample", zh="参考音频 MIME 类型"
        ),
        "style_prompt": Description(
            en="Natural-language style prompt sent as the user message",
            zh="作为 user 消息发送的自然语言风格控制提示词",
        ),
        "audio_format": Description(
            en="Generated audio format", zh="生成音频格式"
        ),
        "optimize_text_preview": Description(
            en="Whether MiMo should optimize text preview for voice design",
            zh="是否让 MiMo 在音色设计模式优化试听文本",
        ),
        "timeout_seconds": Description(
            en="Request timeout for a single MiMo TTS generation call",
            zh="单次 MiMo TTS 生成请求的超时时间",
        ),
    }


class IndexTTS2Config(I18nMixin):
    """Configuration for IndexTTS2 cloud or local HTTP service."""

    mode: Literal["cloud", "local"] = Field("cloud", alias="mode")
    api_key: str = Field("", alias="api_key")
    base_url: str = Field("https://api.modelverse.cn/v1", alias="base_url")
    model: str = Field("IndexTeam/IndexTTS-2", alias="model")
    voice_id: str = Field("", alias="voice_id")
    default_tts_style: Literal["default", "quiet_companion"] = Field(
        "default",
        alias="default_tts_style",
    )
    quiet_companion_emo_alpha: float = Field(
        1.0,
        alias="quiet_companion_emo_alpha",
    )
    quiet_companion_emo_vec: list[float] = Field(
        default_factory=lambda: list(DEFAULT_QUIET_COMPANION_VECTOR),
        alias="quiet_companion_emo_vec",
    )
    api_url: str = Field("http://127.0.0.1:7861/tts", alias="api_url")
    speaker_audio_path: str = Field(
        "private/voice/rikka_voice_clone.wav",
        alias="speaker_audio_path",
    )
    emo_audio_path: str = Field("", alias="emo_audio_path")
    emo_alpha: float = Field(0.6, alias="emo_alpha")
    use_emo_text: bool = Field(False, alias="use_emo_text")
    emo_text: str = Field("", alias="emo_text")
    use_random: bool = Field(False, alias="use_random")
    audio_format: Literal["wav", "mp3"] = Field("wav", alias="audio_format")
    timeout_seconds: float = Field(180.0, alias="timeout_seconds")
    sentence_split_enabled: bool = Field(False, alias="sentence_split_enabled")
    sentence_split_method: Literal["regex", "pysbd"] = Field(
        "regex",
        alias="sentence_split_method",
    )
    max_text_tokens_per_segment: int = Field(
        80,
        alias="max_text_tokens_per_segment",
        ge=10,
        le=400,
    )
    sentence_interval_ms: int = Field(0, alias="sentence_interval_ms", ge=0, le=3000)

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "mode": Description(
            en="IndexTTS2 provider mode: cloud ModelVerse by default, or local service",
            zh="IndexTTS2 提供者模式：默认云端 ModelVerse，或本地服务",
        ),
        "api_key": Description(
            en="ModelVerse API key for cloud IndexTTS2",
            zh="云端 IndexTTS2 的 ModelVerse API 密钥",
        ),
        "base_url": Description(
            en="ModelVerse API base URL for cloud IndexTTS2",
            zh="云端 IndexTTS2 的 ModelVerse API 基础地址",
        ),
        "model": Description(
            en="Cloud IndexTTS2 model id",
            zh="云端 IndexTTS2 模型 ID",
        ),
        "voice_id": Description(
            en="Temporary ModelVerse custom voice id such as uspeech:<uuid>",
            zh="ModelVerse 临时自定义音色 ID，例如 uspeech:<uuid>",
        ),
        "default_tts_style": Description(
            en="Default cloud speech style",
            zh="默认云端语音风格",
        ),
        "quiet_companion_emo_alpha": Description(
            en="Cloud quiet companion emotion vector strength",
            zh="云端 quiet_companion 情绪向量强度",
        ),
        "quiet_companion_emo_vec": Description(
            en="Cloud quiet companion 8D vector: happy, angry, sad, fear, disgust, melancholy, surprise, calm",
            zh="云端 quiet_companion 8 维向量：happy、angry、sad、fear、disgust、melancholy、surprise、calm",
        ),
        "api_url": Description(
            en="Local IndexTTS2 service /tts endpoint",
            zh="本地 IndexTTS2 服务 /tts 接口地址",
        ),
        "speaker_audio_path": Description(
            en="Speaker reference audio path for zero-shot voice cloning",
            zh="零样本音色克隆参考音频路径",
        ),
        "emo_audio_path": Description(
            en="Optional emotion reference audio path",
            zh="可选的情感参考音频路径",
        ),
        "emo_alpha": Description(
            en="Emotion reference strength from 0.0 to 1.0",
            zh="情感参考强度，范围 0.0 到 1.0",
        ),
        "use_emo_text": Description(
            en="Use text-driven emotion control",
            zh="启用文本情感控制",
        ),
        "emo_text": Description(
            en="Optional text emotion description",
            zh="可选情感描述文本",
        ),
        "use_random": Description(
            en="Allow stochastic emotion sampling",
            zh="允许随机情感采样",
        ),
        "audio_format": Description(
            en="Generated audio format",
            zh="生成音频格式",
        ),
        "timeout_seconds": Description(
            en="Request timeout for one local IndexTTS2 generation call",
            zh="单次本地 IndexTTS2 生成请求超时时间",
        ),
        "sentence_split_enabled": Description(
            en="Whether local IndexTTS2 sentence splitting is enabled",
            zh="是否启用本地 IndexTTS2 分句",
        ),
        "sentence_split_method": Description(
            en="Sentence splitting method for local IndexTTS2",
            zh="本地 IndexTTS2 分句方法",
        ),
        "max_text_tokens_per_segment": Description(
            en="Maximum IndexTTS2 text tokens per synthesis segment",
            zh="IndexTTS2 单个合成分句的最大文本 token 数",
        ),
        "sentence_interval_ms": Description(
            en="Delay between generated sentence audio payloads",
            zh="分句音频包之间的间隔毫秒数",
        ),
    }

    @model_validator(mode="after")
    def normalize_cloud_emotion_config(self):
        self.quiet_companion_emo_alpha = clamp_quiet_companion_alpha(
            self.quiet_companion_emo_alpha
        )
        self.quiet_companion_emo_vec = normalize_emotion_vector(
            self.quiet_companion_emo_vec,
            default=DEFAULT_QUIET_COMPANION_VECTOR,
        )
        return self


class TTSConfig(I18nMixin):
    """Configuration for Text-to-Speech."""

    tts_model: Literal[
        "azure_tts",
        "bark_tts",
        "edge_tts",
        "cosyvoice_tts",
        "cosyvoice2_tts",
        "melo_tts",
        "coqui_tts",
        "x_tts",
        "gpt_sovits_tts",
        "fish_api_tts",
        "sherpa_onnx_tts",
        "siliconflow_tts",
        "openai_tts",  # Add openai_tts here
        "spark_tts",
        "minimax_tts",
        "xiaomi_mimo_tts",
        "indextts2_tts",
    ] = Field(..., alias="tts_model")

    azure_tts: Optional[AzureTTSConfig] = Field(None, alias="azure_tts")
    bark_tts: Optional[BarkTTSConfig] = Field(None, alias="bark_tts")
    edge_tts: Optional[EdgeTTSConfig] = Field(None, alias="edge_tts")
    cosyvoice_tts: Optional[CosyvoiceTTSConfig] = Field(None, alias="cosyvoice_tts")
    cosyvoice2_tts: Optional[Cosyvoice2TTSConfig] = Field(None, alias="cosyvoice2_tts")
    melo_tts: Optional[MeloTTSConfig] = Field(None, alias="melo_tts")
    coqui_tts: Optional[CoquiTTSConfig] = Field(None, alias="coqui_tts")
    x_tts: Optional[XTTSConfig] = Field(None, alias="x_tts")
    gpt_sovits_tts: Optional[GPTSoVITSConfig] = Field(None, alias="gpt_sovits")
    fish_api_tts: Optional[FishAPITTSConfig] = Field(None, alias="fish_api_tts")
    sherpa_onnx_tts: Optional[SherpaOnnxTTSConfig] = Field(
        None, alias="sherpa_onnx_tts"
    )
    siliconflow_tts: Optional[SiliconFlowTTSConfig] = Field(
        None, alias="siliconflow_tts"
    )
    openai_tts: Optional[OpenAITTSConfig] = Field(None, alias="openai_tts")
    spark_tts: Optional[SparkTTSConfig] = Field(None, alias="spark_tts")
    minimax_tts: Optional[MinimaxTTSConfig] = Field(None, alias="minimax_tts")
    xiaomi_mimo_tts: Optional[XiaomiMimoTTSConfig] = Field(
        None, alias="xiaomi_mimo_tts"
    )
    indextts2_tts: Optional[IndexTTS2Config] = Field(
        None, alias="indextts2_tts"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "tts_model": Description(
            en="Text-to-speech model to use", zh="要使用的文本转语音模型"
        ),
        "azure_tts": Description(en="Configuration for Azure TTS", zh="Azure TTS 配置"),
        "bark_tts": Description(en="Configuration for Bark TTS", zh="Bark TTS 配置"),
        "edge_tts": Description(en="Configuration for Edge TTS", zh="Edge TTS 配置"),
        "cosyvoice_tts": Description(
            en="Configuration for Cosyvoice TTS", zh="Cosyvoice TTS 配置"
        ),
        "cosyvoice2_tts": Description(
            en="Configuration for Cosyvoice2 TTS", zh="Cosyvoice2 TTS 配置"
        ),
        "melo_tts": Description(en="Configuration for Melo TTS", zh="Melo TTS 配置"),
        "coqui_tts": Description(en="Configuration for Coqui TTS", zh="Coqui TTS 配置"),
        "x_tts": Description(en="Configuration for XTTS", zh="XTTS 配置"),
        "gpt_sovits_tts": Description(
            en="Configuration for GPT-SoVITS", zh="GPT-SoVITS 配置"
        ),
        "fish_api_tts": Description(
            en="Configuration for Fish API TTS", zh="Fish API TTS 配置"
        ),
        "sherpa_onnx_tts": Description(
            en="Configuration for Sherpa Onnx TTS", zh="Sherpa Onnx TTS 配置"
        ),
        "siliconflow_tts": Description(
            en="Configuration for SiliconFlow TTS", zh="SiliconFlow TTS 配置"
        ),
        "openai_tts": Description(
            en="Configuration for OpenAI-compatible TTS", zh="OpenAI 兼容 TTS 配置"
        ),
        "spark_tts": Description(en="Configuration for Spark TTS", zh="Spark TTS 配置"),
        "minimax_tts": Description(
            en="Configuration for Minimax TTS", zh="Minimax TTS 配置"
        ),
        "xiaomi_mimo_tts": Description(
            en="Configuration for Xiaomi MiMo V2.5 TTS",
            zh="小米 MiMo V2.5 TTS 配置",
        ),
        "indextts2_tts": Description(
            en="Configuration for a local IndexTTS2 service",
            zh="本地 IndexTTS2 服务配置",
        ),
    }

    @model_validator(mode="after")
    def check_tts_config(cls, values: "TTSConfig", info: ValidationInfo):
        tts_model = values.tts_model

        # Only validate the selected TTS model
        if tts_model == "azure_tts" and values.azure_tts is not None:
            values.azure_tts.model_validate(values.azure_tts.model_dump())
        elif tts_model == "bark_tts" and values.bark_tts is not None:
            values.bark_tts.model_validate(values.bark_tts.model_dump())
        elif tts_model == "edge_tts" and values.edge_tts is not None:
            values.edge_tts.model_validate(values.edge_tts.model_dump())
        elif tts_model == "cosyvoice_tts" and values.cosyvoice_tts is not None:
            values.cosyvoice_tts.model_validate(values.cosyvoice_tts.model_dump())
        elif tts_model == "cosyvoice2_tts" and values.cosyvoice2_tts is not None:
            values.cosyvoice2_tts.model_validate(values.cosyvoice2_tts.model_dump())
        elif tts_model == "melo_tts" and values.melo_tts is not None:
            values.melo_tts.model_validate(values.melo_tts.model_dump())
        elif tts_model == "coqui_tts" and values.coqui_tts is not None:
            values.coqui_tts.model_validate(values.coqui_tts.model_dump())
        elif tts_model == "x_tts" and values.x_tts is not None:
            values.x_tts.model_validate(values.x_tts.model_dump())
        elif tts_model == "gpt_sovits_tts" and values.gpt_sovits_tts is not None:
            values.gpt_sovits_tts.model_validate(values.gpt_sovits_tts.model_dump())
        elif tts_model == "fish_api_tts" and values.fish_api_tts is not None:
            values.fish_api_tts.model_validate(values.fish_api_tts.model_dump())
        elif tts_model == "sherpa_onnx_tts" and values.sherpa_onnx_tts is not None:
            values.sherpa_onnx_tts.model_validate(values.sherpa_onnx_tts.model_dump())
        elif tts_model == "siliconflow_tts" and values.siliconflow_tts is not None:
            values.siliconflow_tts.model_validate(values.siliconflow_tts.model_dump())
        elif tts_model == "openai_tts" and values.openai_tts is not None:
            values.openai_tts.model_validate(values.openai_tts.model_dump())
        elif tts_model == "spark_tts" and values.spark_tts is not None:
            values.spark_tts.model_validate(values.spark_tts.model_dump())
        elif tts_model == "minimax_tts" and values.minimax_tts is not None:
            values.minimax_tts.model_validate(values.minimax_tts.model_dump())
        elif tts_model == "xiaomi_mimo_tts" and values.xiaomi_mimo_tts is not None:
            values.xiaomi_mimo_tts.model_validate(
                values.xiaomi_mimo_tts.model_dump()
            )
        elif tts_model == "indextts2_tts" and values.indextts2_tts is not None:
            values.indextts2_tts.model_validate(values.indextts2_tts.model_dump())

        return values
