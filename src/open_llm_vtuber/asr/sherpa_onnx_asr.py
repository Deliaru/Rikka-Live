import os
import asyncio
import numpy as np
import sherpa_onnx
from loguru import logger
from .asr_interface import ASRInterface, StreamingASRResult
from .utils import download_and_extract, check_and_extract_local_file
import onnxruntime


class SherpaOnnxStreamingSession:
    def __init__(self, recognizer, sample_rate: int):
        self.recognizer = recognizer
        self.sample_rate = sample_rate
        self.stream = recognizer.create_stream()
        self._last_partial = ""
        self._lock = asyncio.Lock()

    async def accept_audio(self, audio: np.ndarray) -> StreamingASRResult:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        async with self._lock:
            return await asyncio.to_thread(self._accept_audio_sync, audio)

    async def finish(self) -> StreamingASRResult:
        async with self._lock:
            return await asyncio.to_thread(self._finish_sync)

    def _accept_audio_sync(self, audio: np.ndarray) -> StreamingASRResult:
        self.stream.accept_waveform(self.sample_rate, audio)
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        text = (self.recognizer.get_result(self.stream) or "").strip()
        endpoint = bool(self.recognizer.is_endpoint(self.stream))
        final = ""
        if endpoint:
            final = text
            self.recognizer.reset(self.stream)
            self._last_partial = ""
        elif text == self._last_partial:
            text = ""
        else:
            self._last_partial = text
        return StreamingASRResult(partial=text, final=final, endpoint=endpoint)

    def _finish_sync(self) -> StreamingASRResult:
        self.stream.input_finished()
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        final = (self.recognizer.get_result(self.stream) or "").strip()
        self.recognizer.reset(self.stream)
        self._last_partial = ""
        return StreamingASRResult(final=final, endpoint=bool(final))


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        model_type: str = "paraformer",  # or "transducer", "nemo_ctc", "wenet_ctc", "whisper", "tdnn_ctc", "sense_voice"
        encoder: str = None,  # Path to the encoder model, used with transducer
        decoder: str = None,  # Path to the decoder model, used with transducer
        joiner: str = None,  # Path to the joiner model, used with transducer
        paraformer: str = None,  # Path to the model.onnx from Paraformer
        nemo_ctc: str = None,  # Path to the model.onnx from NeMo CTC
        wenet_ctc: str = None,  # Path to the model.onnx from WeNet CTC
        tdnn_model: str = None,  # Path to the model.onnx for the tdnn model of the yesno recipe
        whisper_encoder: str = None,  # Path to whisper encoder model
        whisper_decoder: str = None,  # Path to whisper decoder model
        sense_voice: str = None,  # Path to the model.onnx from SenseVoice
        tokens: str = None,  # Path to tokens.txt
        hotwords_file: str = "",  # Path to hotwords file
        hotwords_score: float = 1.5,  # Hotwords score
        modeling_unit: str = "",  # Modeling unit for hotwords
        bpe_vocab: str = "",  # Path to bpe vocabulary, used with hotwords
        num_threads: int = 1,  # Number of threads for neural network computation
        whisper_language: str = "",  # Language for whisper model
        whisper_task: str = "transcribe",  # Task for whisper model (transcribe or translate)
        whisper_tail_paddings: int = -1,  # Tail padding frames for whisper model
        blank_penalty: float = 0.0,  # Penalty for blank symbol
        decoding_method: str = "greedy_search",  # Decoding method (greedy_search or modified_beam_search)
        debug: bool = False,  # Show debug messages
        sample_rate: int = 16000,  # Sample rate
        feature_dim: int = 80,  # Feature dimension
        use_itn: bool = True,  # Use ITN for SenseVoice models
        provider: str = "cpu",  # Provider for inference (cpu or cuda)
        streaming: dict | None = None,  # Dedicated streaming recognizer config
    ) -> None:
        self.model_type = model_type
        self.encoder = encoder
        self.decoder = decoder
        self.joiner = joiner
        self.paraformer = paraformer
        self.nemo_ctc = nemo_ctc
        self.wenet_ctc = wenet_ctc
        self.tdnn_model = tdnn_model
        self.whisper_encoder = whisper_encoder
        self.whisper_decoder = whisper_decoder
        self.sense_voice: str = sense_voice
        self.tokens = tokens
        self.hotwords_file = hotwords_file
        self.hotwords_score = hotwords_score
        self.modeling_unit = modeling_unit
        self.bpe_vocab = bpe_vocab
        self.num_threads = num_threads
        self.whisper_language = whisper_language
        self.whisper_task = whisper_task
        self.whisper_tail_paddings = whisper_tail_paddings
        self.blank_penalty = blank_penalty
        self.decoding_method = decoding_method
        self.debug = debug
        self.SAMPLE_RATE = sample_rate
        self.feature_dim = feature_dim
        self.use_itn = use_itn
        self.streaming = streaming or None
        self.is_streaming_capable = bool(self.streaming)
        self._streaming_recognizer = None

        # we need to find a way to get cuda version of sherpa-onnx before we can
        # use the gpu provider.
        self.provider = provider
        if self.provider == "cuda":
            try:
                if "CUDAExecutionProvider" not in onnxruntime.get_available_providers():
                    logger.warning(
                        "CUDA provider not available for ONNX. Falling back to CPU."
                    )
                    self.provider = "cpu"
            except ImportError:
                logger.warning("ONNX Runtime not installed. Falling back to CPU.")
                self.provider = "cpu"
        logger.info(f"Sherpa-Onnx-ASR: Using {self.provider} for inference")

        self.recognizer = self._create_recognizer()

    def streaming_status(self) -> str:
        if not self.streaming:
            return "streaming_config_missing"
        if self._missing_streaming_files():
            return "streaming_model_missing"
        return "streaming_ready"

    def _missing_streaming_files(self) -> list[str]:
        if not isinstance(self.streaming, dict):
            return ["streaming"]
        model_type = str(self.streaming.get("model_type") or "transducer")
        required_by_type = {
            "transducer": ("encoder", "decoder", "joiner", "tokens"),
            "paraformer": ("encoder", "decoder", "tokens"),
            "zipformer": ("encoder", "decoder", "joiner", "tokens"),
            "zipformer2_ctc": ("model", "tokens"),
        }
        required = required_by_type.get(model_type, ("tokens",))
        missing = []
        for field in required:
            path = self.streaming.get(field)
            if not path or not os.path.isfile(str(path)):
                missing.append(field)
        return missing

    def create_streaming_session(self) -> SherpaOnnxStreamingSession:
        if self.streaming_status() != "streaming_ready":
            raise RuntimeError(f"Streaming ASR is not ready: {self.streaming_status()}")
        if self._streaming_recognizer is None:
            self._streaming_recognizer = self._create_streaming_recognizer()
        sample_rate = int(self.streaming.get("sample_rate") or self.SAMPLE_RATE)
        return SherpaOnnxStreamingSession(self._streaming_recognizer, sample_rate)

    def _create_streaming_recognizer(self):
        config = self.streaming or {}
        model_type = str(config.get("model_type") or "transducer")
        common = {
            "tokens": config.get("tokens"),
            "num_threads": int(config.get("num_threads") or self.num_threads),
            "sample_rate": int(config.get("sample_rate") or self.SAMPLE_RATE),
            "feature_dim": int(config.get("feature_dim") or self.feature_dim),
            "enable_endpoint_detection": bool(
                config.get("enable_endpoint_detection", True)
            ),
            "rule1_min_trailing_silence": float(
                config.get("rule1_min_trailing_silence", 1.2)
            ),
            "rule2_min_trailing_silence": float(
                config.get("rule2_min_trailing_silence", 0.8)
            ),
            "rule3_min_utterance_length": float(
                config.get("rule3_min_utterance_length", 20.0)
            ),
            "decoding_method": config.get("decoding_method") or self.decoding_method,
            "provider": config.get("provider") or self.provider,
            "debug": bool(config.get("debug", self.debug)),
        }
        if model_type in {"transducer", "zipformer"}:
            return sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=config.get("encoder"),
                decoder=config.get("decoder"),
                joiner=config.get("joiner"),
                **common,
            )
        if model_type == "paraformer":
            return sherpa_onnx.OnlineRecognizer.from_paraformer(
                encoder=config.get("encoder"),
                decoder=config.get("decoder"),
                **common,
            )
        if model_type == "zipformer2_ctc":
            return sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
                model=config.get("model"),
                **common,
            )
        raise RuntimeError(f"Unsupported sherpa-onnx streaming model type: {model_type}")

    def _create_recognizer(self):
        if self.model_type == "transducer":
            recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=self.encoder,
                decoder=self.decoder,
                joiner=self.joiner,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                hotwords_file=self.hotwords_file,
                hotwords_score=self.hotwords_score,
                modeling_unit=self.modeling_unit,
                bpe_vocab=self.bpe_vocab,
                blank_penalty=self.blank_penalty,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "paraformer":
            recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=self.paraformer,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "nemo_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=self.nemo_ctc,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "wenet_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_wenet_ctc(
                model=self.wenet_ctc,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "whisper":
            recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=self.whisper_encoder,
                decoder=self.whisper_decoder,
                tokens=self.tokens,
                num_threads=self.num_threads,
                decoding_method=self.decoding_method,
                debug=self.debug,
                language=self.whisper_language,
                task=self.whisper_task,
                tail_paddings=self.whisper_tail_paddings,
                provider=self.provider,
            )
        elif self.model_type == "tdnn_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_tdnn_ctc(
                model=self.tdnn_model,
                tokens=self.tokens,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                num_threads=self.num_threads,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "sense_voice":
            if not self.sense_voice or not os.path.isfile(self.sense_voice):
                if self.sense_voice.startswith(
                    "./models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
                ):
                    logger.warning(
                        "SenseVoice model not found. Downloading the model..."
                    )

                    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
                    output_dir = "./models"
                    # check the local file first before download
                    local_result = check_and_extract_local_file(url, output_dir)

                    if local_result is None:
                        logger.info("Local file not found. Downloading...")
                        download_and_extract(url, output_dir)
                    else:
                        logger.info("Local file found. Using existing file.")
                    # download_and_extract(
                    #     url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2",
                    #     output_dir="./models",
                    # )
                else:
                    logger.critical(
                        "The SenseVoice model is missing. Please provide the path to the model.onnx file."
                    )
            recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=self.sense_voice,
                tokens=self.tokens,
                num_threads=self.num_threads,
                use_itn=self.use_itn,
                debug=self.debug,
                provider=self.provider,
            )
        else:
            raise ValueError(f"Invalid model type: {self.model_type}")

        return recognizer

    def transcribe_np(self, audio: np.ndarray) -> str:
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.SAMPLE_RATE, audio)
        self.recognizer.decode_streams([stream])
        return stream.result.text
