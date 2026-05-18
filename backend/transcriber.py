import os
import threading
from faster_whisper import WhisperModel
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Transcriber:
    """音频转录器，使用Faster-Whisper进行语音转文字"""
    
    def __init__(self, model_size: str = "base"):
        """
        初始化转录器
        
        Args:
            model_size: Whisper模型大小 (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self._model_lock = threading.Lock()
        self.last_detected_language = None
        
    def _load_model(self):
        """延迟加载模型"""
        if self.model is not None:
            return
        with self._model_lock:
            if self.model is not None:
                return
            logger.info(f"正在加载Whisper模型: {self.model_size}")
            try:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info("模型加载完成")
            except Exception as e:
                logger.error(f"模型加载失败: {str(e)}")
                raise Exception(f"模型加载失败: {str(e)}")

    def is_model_loaded(self) -> bool:
        """返回 Whisper 模型是否已加载到当前进程。"""
        return self.model is not None

    async def ensure_model_loaded(self):
        """在线程中准备模型，避免首次下载/加载阻塞事件循环。"""
        import asyncio
        await asyncio.to_thread(self._load_model)
    
    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言（可选，如果不指定则自动检测）
            
        Returns:
            转录文本（Markdown格式）
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                raise Exception(f"音频文件不存在: {audio_path}")
            
            logger.info(f"开始转录音频: {audio_path}")
            
            # 模型首次下载/加载与 segments 迭代都会阻塞，整体放入线程避免卡住状态查询。
            import asyncio
            def _do_transcribe():
                self._load_model()
                segments, info = self.model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=5,
                    best_of=5,
                    temperature=[0.0, 0.2, 0.4],  # 使用温度递增策略
                    # 更稳健：开启VAD与阈值，降低静音/噪音导致的重复
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 900,  # 静音检测时长
                        "speech_pad_ms": 300  # 语音填充
                    },
                    no_speech_threshold=0.7,  # 无语音阈值
                    compression_ratio_threshold=2.3,  # 压缩比阈值，检测重复
                    log_prob_threshold=-1.0,  # 日志概率阈值
                    # 避免错误累积导致的连环重复
                    condition_on_previous_text=False
                )
                detected_language = info.language
                logger.info(f"检测到的语言: {detected_language}")
                logger.info(f"语言检测概率: {info.language_probability:.2f}")

                transcript_lines = [
                    "# Video Transcription",
                    "",
                    f"**Detected Language:** {detected_language}",
                    f"**Language Probability:** {info.language_probability:.2f}",
                    "",
                    "## Transcription Content",
                    "",
                ]

                for segment in segments:
                    start_time = self._format_time(segment.start)
                    end_time = self._format_time(segment.end)
                    text = segment.text.strip()

                    transcript_lines.append(f"**[{start_time} - {end_time}]**")
                    transcript_lines.append("")
                    transcript_lines.append(text)
                    transcript_lines.append("")

                return detected_language, "\n".join(transcript_lines)

            detected_language, transcript_text = await asyncio.to_thread(_do_transcribe)
            self.last_detected_language = detected_language  # 保存检测到的语言
            logger.info("转录完成")
            
            return transcript_text
            
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            raise Exception(f"转录失败: {str(e)}")
    
    def _format_time(self, seconds: float) -> str:
        """
        将秒数转换为时分秒格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_supported_languages(self) -> list:
        """
        获取支持的语言列表
        """
        return [
            "zh", "en", "ja", "ko", "es", "fr", "de", "it", "pt", "ru",
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no"
        ]
    
    def get_detected_language(self, transcript_text: Optional[str] = None) -> Optional[str]:
        """
        获取检测到的语言
        
        Args:
            transcript_text: 转录文本（可选，用于从文本中提取语言信息）
            
        Returns:
            检测到的语言代码
        """
        # 如果有保存的语言，直接返回
        if self.last_detected_language:
            return self.last_detected_language
        
        # 如果提供了转录文本，尝试从中提取语言信息
        if transcript_text and "**Detected Language:**" in transcript_text:
            lines = transcript_text.split('\n')
            for line in lines:
                if "**Detected Language:**" in line:
                    lang = line.split(":")[-1].strip()
                    return lang if lang else None
        
        return None
