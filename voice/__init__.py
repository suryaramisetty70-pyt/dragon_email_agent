# =============================================================================
# VOICE SYSTEM - Speech Recognition and Text-to-Speech
# =============================================================================

import os
import io
import threading
import queue
import time
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
import json

# Audio processing
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOG_AVAILABLE = True
except ImportError:
    sr = None  # type: ignore
    SPEECH_RECOG_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

from core import Config, DragonModule, logger, events


class VoiceCommand:
    """Voice command structure"""
    def __init__(
        self, 
        text: str, 
        confidence: float = 1.0,
        timestamp: Optional[datetime] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        source: str = "voice"  # "voice" or "text"
    ):
        self.text = text
        self.confidence = confidence
        self.timestamp = timestamp or datetime.utcnow()
        self.intent = intent
        self.entities = entities or {}
        self.source = source  # Track whether command came from voice or text
        
    def __str__(self):
        return f"{self.source.title()}Command(text='{self.text}', confidence={self.confidence:.2f})"


class TextCommand(VoiceCommand):
    """Text command structure (extends VoiceCommand for compatibility)"""
    def __init__(
        self, 
        text: str,
        confidence: float = 1.0,
        timestamp: Optional[datetime] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            text=text,
            confidence=confidence,
            timestamp=timestamp,
            intent=intent,
            entities=entities,
            source="text"
        )


class WakeWordDetector:
    """Detect wake word for voice activation"""
    
    # Simple wake word patterns - in production use Precise or Porcupine
    WAKE_PATTERNS = [
        "hey dragon",
        "dragon",
        "hey drago",
        "okay dragon",
        "hi dragon",
    ]
    
    def __init__(self, config: Config):
        self.config = config
        self.wake_word = config.wake_word.lower()
        self.wake_phrases = [self.wake_word] + self.WAKE_PATTERNS
        self._last_detection = None
        self._cooldown = 2.0  # Seconds between activations
        
    def detect(self, audio_data: bytes) -> bool:
        """Detect wake word in audio"""
        # Simple energy-based detection (placeholder for actual wake word detection)
        # In production, use Mozilla DeepSpeech, Precise, or Picovoice Porcupine
        
        # For now, use simple keyword matching in transcription
        # This is a placeholder - real implementation would use ML model
        return False
        
    def check_text(self, text: str) -> bool:
        """Check if text contains wake word"""
        text_lower = text.lower()
        
        # Check exact match
        if self.wake_word in text_lower:
            return self._check_cooldown()
            
        # Check patterns
        for phrase in self.wake_phrases:
            if phrase in text_lower:
                return self._check_cooldown()
                
        return False
        
    def _check_cooldown(self) -> bool:
        """Check if cooldown has passed"""
        now = time.time()
        
        if self._last_detection:
            elapsed_chords = now - self._last_detection
            if elapsed_chords < self._cooldown:
                return False
                
        self._last_detection = now
        return True


class SpeechRecognizer:
    """Speech-to-text using various backends"""
    
    def __init__(self, config: Config):
        self.config = config
        self._recognizer = None
        self._microphone = None
        self._is_listening = False
        self._audio_queue = queue.Queue()
        self._stop_event = threading.Event()
        
        if SPEECH_RECOG_AVAILABLE and sr:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300  # Adjust for environment
            self._recognizer.dynamic_energy_threshold = True
            
        if PYAUDIO_AVAILABLE:
            self._init_microphone()
            
    def _init_microphone(self) -> None:
        """Initialize microphone"""
        if PYAUDIO_AVAILABLE and SPEECH_RECOG_AVAILABLE and sr:
            try:
                self._microphone = sr.Microphone()
            except Exception as e:
                logger.warning(f"Microphone initialization failed: {e}")
                
    def recognize_speech(self, timeout: float = 5.0) -> Optional[VoiceCommand]:
        """Recognize speech from microphone"""
        if not SPEECH_RECOG_AVAILABLE:
            logger.warning("Speech recognition not available")
            return None
            
        if not self._recognizer or not self._microphone:
            self._init_microphone()
            if not self._recognizer or not self._microphone:
                return None
                
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(source, timeout=timeout)
                
            # Try to recognize using multiple backends
            text = None
            confidence = 0.0
            
            # Google Speech Recognition (requires internet)
            try:
                result = self._recognizer.recognize_google(audio, language=self.config.voice_language)
                text = result
                confidence = 0.8  # Google doesn't provide confidence
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                logger.error(f"Speech recognition service error: {e}")
                
            # Try offline recognition if available
            if not text and SPEECH_RECOG_AVAILABLE:
                try:
                    # Vosk or Sphinx for offline
                    pass
                except:
                    pass
                    
            if text:
                return VoiceCommand(text=text, confidence=confidence)
                
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            
        return None
        
    def recognize_file(self, audio_file: str) -> Optional[VoiceCommand]:
        """Recognize speech from audio file"""
        if not SPEECH_RECOG_AVAILABLE:
            return None
            
        try:
            with sr.AudioFile(audio_file) as source:
                audio = self._recognizer.record(source)
                text = self._recognizer.recognize_google(audio, language=self.config.voice_language)
                return VoiceCommand(text=text, confidence=0.8)
        except Exception as e:
            logger.error(f"File recognition error: {e}")
            return None
            
    def continuous_listen(
        self, 
        callback: Callable[[VoiceCommand], None],
        phrase_time_limit: float = 10.0
    ) -> None:
        """Start continuous listening"""
        if self._is_listening:
            return
            
        self._is_listening = True
        self._stop_event.clear()
        
        thread = threading.Thread(
            target=self._listen_loop,
            args=(callback, phrase_time_limit),
            daemon=True
        )
        thread.start()
        
    def _listen_loop(
        self, 
        callback: Callable[[VoiceCommand], None],
        phrase_time_limit: float
    ) -> None:
        """Continuous listening loop"""
        if not self._recognizer or not self._microphone:
            return
            
        while not self._stop_event.is_set():
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = self._recognizer.listen(source, phrase_time_limit=phrase_time_limit)
                    
                # Process in separate thread to not block listening
                threading.Thread(
                    target=self._process_audio,
                    args=(audio, callback),
                    daemon=True
                ).start()
                
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                logger.error(f"Continuous listen error: {e}")
                time.sleep(0.5)
                
    def _process_audio(
        self, 
        audio,  # type: ignore
        callback: Callable[[VoiceCommand], None]
    ) -> None:
        """Process recognized audio"""
        try:
            text = self._recognizer.recognize_google(audio, language=self.config.voice_language)
            command = VoiceCommand(text=text, confidence=0.8)
            callback(command)
        except Exception as e:
            pass  # Ignore recognition errors in background
            
    def stop_listening(self) -> None:
        """Stop continuous listening"""
        self._stop_event.set()
        self._is_listening = False


class TextToSpeech:
    """Text-to-speech using gTTS or local TTS"""
    
    def __init__(self, config: Config):
        self.config = config
        self._audio_cache: Dict[str, bytes] = {}
        self._cache_size = 100
        
    def speak(self, text: str, use_cache: bool = True) -> Optional[bytes]:
        """Convert text to speech"""
        if not GTTS_AVAILABLE:
            logger.warning("gTTS not available for TTS")
            return None
            
        # Check cache
        cache_key = f"{text[:50]}_{self.config.voice_language}"
        if use_cache and cache_key in self._audio_cache:
            return self._audio_cache[cache_key]
            
        try:
            tts = gTTS(text=text, lang=self.config.voice_language.split("-")[0])
            
            # Save to BytesIO buffer
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            audio_data = buffer.read()
            
            # Add to cache
            if use_cache:
                if len(self._audio_cache) >= self._cache_size:
                    # Remove oldest entry
                    oldest_key = next(iter(self._audio_cache))
                    del self._audio_cache[oldest_key]
                self._audio_cache[cache_key] = audio_data
                
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
            
    def speak_to_file(self, text: str, filename: str) -> bool:
        """Save TTS to file"""
        try:
            tts = gTTS(text=text, lang=self.config.voice_language.split("-")[0])
            tts.save(filename)
            return True
        except Exception as e:
            logger.error(f"TTS save error: {e}")
            return False
            
    def speak_with_plexity(self, text: str, rate: Optional[float] = None) -> Optional[bytes]:
        """Speak with rate adjustment"""
        # Note: gTTS doesn't support speed adjustment directly
        # In production, could use pyttsx3 or coqui for local TTS with speed control
        return self.speak(text)


class VoicePrompter:
    """Generate voice prompts and snippets"""
    
    EMAIL_TEMPLATES = {
        "greeting": [
            "Good morning! You have {count} new emails.",
            "Hello! Today's briefing has {count} important messages.",
            "Good day! {count} emails require your attention.",
        ],
        "urgent": [
            "Urgent email from {sender}: {subject}",
            "Important message from {sender}: {subject}",
            "Priority alert from {sender}: {subject}",
        ],
        "summary": [
            "Out of {total} emails, {important} are marked as important.",
            "You have {unread} unread messages, {important} are high priority.",
            "Summary: {total} total, {unread} unread, {important} important.",
        ],
        "reminder": [
            "Reminder: {count} emails pending reply for over {hours} hours.",
            "Follow-up needed: {count} conversations without response.",
            "Action required on {count} emails awaiting your reply.",
        ],
        "success": [
            "Email sent successfully.",
            "Your message has been delivered.",
            "Done. Email sent to {recipient}.",
        ],
        "error": [
            "I couldn't complete that action.",
            "Sorry, there was an error processing your request.",
            "Failed to send. Please try again.",
        ],
    }
    
    def generate_greeting(self, email_count: int) -> str:
        """Generate greeting with email count"""
        import random
        template = random.choice(self.EMAIL_TEMPLATES["greeting"])
        return template.format(count=email_count)
        
    def generate_email_announcement(
        self, 
        sender: str, 
        subject: str, 
        priority: int
    ) -> str:
        """Generate email announcement"""
        import random
        
        if priority <= 1:  # P0 or P1
            template = random.choice(self.EMAIL_TEMPLATES["urgent"])
        else:
            template = f"New email from {sender}: {subject}"
            
        return template.format(sender=sender, subject=subject[:100])
        
    def generate_summary(
        self, 
        total: int, 
        unread: int, 
        important: int
    ) -> str:
        """Generate email summary"""
        import random
        template = random.choice(self.EMAIL_TEMPLATES["summary"])
        return template.format(total=total, unread=unread, important=important)
        
    def generate_reminder(self, count: int, hours: int) -> str:
        """Generate follow-up reminder"""
        import random
        template = random.choice(self.EMAIL_TEMPLATES["reminder"])
        return template.format(count=count, hours=hours)
        
    def generate_confirmation(self, action: str) -> str:
        """Generate action confirmation"""
        import random
        
        if action == "sent":
            return random.choice(self.EMAIL_TEMPLATES["success"])
        else:
            return random.choice(self.EMAIL_TEMPLATES["error"])
            
    def format_email_for_voice(self, email_attrs: Dict[str, Any]) -> str:
        """Format email attributes for voice output"""
        parts = []
        
        # Sender
        sender = email_attrs.get("sender_name") or email_attrs.get("sender_email", "Unknown")
        parts.append(f"From: {sender}")
        
        # Subject
        subject = email_attrs.get("subject", "No subject")
        parts.append(f"Subject: {subject}")
        
        # Priority indicator
        priority = email_attrs.get("priority", 3)
        if priority <= 1:
            parts.append("Priority: Urgent")
        elif priority == 2:
            parts.append("Priority: Important")
            
        # Time
        date = email_attrs.get("date_sent")
        if date:
            parts.append(f"Time: {date.strftime('%I:%M %p')}")
            
        # Preview
        snippet = email_attrs.get("snippet", "")
        if snippet:
            parts.append(f"Preview: {snippet[:150]}")
            
        return ". ".join(parts)


class VoiceCommandParser:
    """Parse voice commands into actionable intents"""
    
    COMMAND_PATTERNS = {
        # Read commands
        r"(?:read|show|get|tell\s+me\s+about)\s+(?:todays?\\s+)?(?:important\\s+)?emails?": {
            "intent": "read_important_emails",
            "scope": "important"
        },
        r"(?:read|show|get)\s+(?:todays?\\s+)?unread\\s+emails?": {
            "intent": "read_unread_emails",
            "scope": "unread"
        },
        r"(?:read|show|get)\s+(?:todays?\\s+)?urgent\\s+emails?": {
            "intent": "read_urgent_emails",
            "scope": "urgent"
        },
        r"(?:summarize|summary\\s+of)\s+(?:todays?\\s+)?emails?": {
            "intent": "summarize_emails",
            "scope": "daily"
        },
        r"(?:how\s+many|number\\s+of)\s+(?:new\\s+)?unread\\s+emails?": {
            "intent": "count_unread",
            "scope": "unread"
        },
        
        # Reply commands
        r"reply\\s+to\\s+([^\s]+)": {
            "intent": "reply_to_contact",
            "entities": ["contact_name"]
        },
        r"reply\\s+to\\s+(?:that\\s+)?email": {
            "intent": "reply_to_last",
            "scope": "last"
        },
        
        # Action commands
        r"(?:send|compose)\\s+(?:an\\s+)?email\\s+to\\s+([^\s]+)": {
            "intent": "compose_email",
            "entities": ["recipient"]
        },
        r"(?:archive|delete|mark\\s+read)\\s+(?:that\\s+)?email": {
            "intent": "email_action",
            "scope": "last"
        },
        
        # Search commands
        r"find\\s+(?:emails?\\s+(?:about|from|to)\\s+)?(.+)": {
            "intent": "search_emails",
            "entities": ["query"]
        },
        r"search\\s+for\\s+(.+)": {
            "intent": "search_emails",
            "entities": ["query"]
        },
        
        # Status commands
        r"what\\s+(?:do\\s+I\\s+have| emails?\\s+do\\s+I\\s+have)": {
            "intent": "inbox_status",
            "scope": "summary"
        },
        r"check\\s+(?:my\\s+)?inbox": {
            "intent": "inbox_status",
            "scope": "full"
        },
    }
    
    def parse(self, text: str) -> VoiceCommand:
        """Parse voice command text"""
        import re
        
        text_lower = text.lower()
        
        for pattern, config in self.COMMAND_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                command = VoiceCommand(
                    text=text,
                    intent=config["intent"],
                    confidence=0.85
                )
                
                # Extract entities
                if "entities" in config:
                    groups = match.groups()
                    for i, entity_name in enumerate(config["entities"]):
                        if i < len(groups):
                            command.entities[entity_name] = groups[i]
                            
                return command
                
        # No match - return with unknown intent
        return VoiceCommand(
            text=text,
            intent="unknown",
            confidence=0.5
        )


class AudioPlayer:
    """Play audio output"""
    
    def __init__(self):
        self._audio = None
        if PYAUDIO_AVAILABLE:
            self._audio = pyaudio.PyAudio()
        self._playing = False
        
    def play(self, audio_data: bytes) -> bool:
        """Play audio data"""
        if not self._audio or not audio_data:
            return False
            
        try:
            import wave
            
            self._playing = True
            
            # Write to temporary WAV file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
                
            # Play using pyaudio
            with wave.open(temp_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                format_map = {
                    1: pyaudio.paInt16,
                    2: pyaudio.paInt16,
                }
                format_code = format_map.get(channels, pyaudio.paInt16)
                
                stream = self._audio.open(
                    format=stream,
                    channels=channels,
                    rate=sample_rate,
                    output=True
                )
                
                chunk_size = 1024
                data = wav_file.readframes(chunk_size)
                
                while data and self._playing:
                    stream.write(data)
                    data = wav_file.readframes(chunk_size)
                    
                stream.stop_stream()
                stream.close()
                
            # Cleanup
            os.unlink(temp_path)
            self._playing = False
            return True
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            self._playing = False
            return False
            
    def stop(self) -> None:
        """Stop audio playback"""
        self._playing = False


class VoiceSystem(DragonModule):
    """Main voice system controller"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        
        self.enabled = config.voice_enabled
        if not self.enabled:
            logger.info("Voice system disabled in config")
            return
            
        self.wake_detector = WakeWordDetector(config)
        self.speech_recognizer = SpeechRecognizer(config)
        self.tts = TextToSpeech(config)
        self.prompter = VoicePrompter()
        self.command_parser = VoiceCommandParser()
        self.audio_player = AudioPlayer()
        
        self._is_active = False
        self._command_callback: Optional[Callable[[VoiceCommand], None]] = None
        
        # Event handlers
        events.on("voice_activate", self.on_activation)
        events.on("voice_deactivate", self.on_deactivation)
        
    def initialize(self) -> None:
        """Initialize voice system"""
        super().initialize()
        self.logger.info("Voice System initialized")
        
    def activate(self) -> None:
        """Activate voice listening"""
        if not self.enabled:
            return
            
        self._is_active = True
        self.logger.info("Voice system activated")
        
        # Start continuous listening
        self.speech_recognizer.continuous_listen(
            callback=self._on_speech
        )
        
    def deactivate(self) -> None:
        """Deactivate voice listening"""
        self._is_active = False
        self.speech_recognizer.stop_listening()
        self.logger.info("Voice system deactivated")
        
    def speak(self, text: str, wait: bool = True) -> None:
        """Speak text to user"""
        if not self.enabled:
            return
            
        audio_data = self.tts.speak(text)
        if audio_data:
            if wait:
                self.audio_player.play(audio_data)
            else:
                threading.Thread(
                    target=self.audio_player.play,
                    args=(audio_data,),
                    daemon=True
                ).start()
                
    def announce_email(self, sender: str, subject: str, priority: int = 3) -> None:
        """Announce incoming email"""
        text = self.prompter.generate_email_announcement(sender, subject, priority)
        self.speak(text)
        
    def announce_summary(
        self, 
        total: int, 
        unread: int, 
        important: int
    ) -> None:
        """Announce email summary"""
        text = self.prompter.generate_summary(total, unread, important)
        self.speak(text)
        
    def process_voice_input(self, audio_data: bytes) -> Optional[VoiceCommand]:
        """Process raw voice input"""
        # Save to temporary file for recognition
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
            
        try:
            command = self.speech_recognizer.recognize_file(temp_path)
            if command:
                # Check for wake word
                if self.wake_detector.check_text(command.text):
                    events.emit("wake_word_detected")
                    
                # Parse command
                return self.command_parser.parse(command.text)
        finally:
            os.unlink(temp_path)
            
        return None
        
    def set_command_callback(
        self, 
        callback: Callable[[VoiceCommand], None]
    ) -> None:
        """Set callback for voice commands"""
        self._command_callback = callback
        
    def _on_speech(self, command: VoiceCommand) -> None:
        """Handle recognized speech"""
        self.logger.debug(f"Recognized: {command.text}")
        
        # Check for wake word
        if self.wake_detector.check_text(command.text):
            self.logger.info("Wake word detected")
            events.emit("wake_word_detected")
            self.speak("Yes?")
            return
            
        # Parse and process command
        parsed_command = self.command_parser.parse(command.text)
        parsed_command.confidence = command.confidence
        
        # Emit command event
        events.emit("voice.Command", command=parsed_command)
        
        # Call callback if set
        if self._command_callback:
            self._command_callback(parsed_command)
            
    def on_activation(self) -> None:
        """Handle activation event"""
        self.speak("Voice activated. How can I help you?")
        
    def on_deactivation(self) -> None:
        """Handle deactivation event"""
        self._is_active = False
        
    def process_text_command(self, text: str) -> Optional[VoiceCommand]:
        """Process text command (non-voice input)
        
        Args:
            text: Text command to process (e.g., "@dragon read emails")
            
        Returns:
            Parsed VoiceCommand or None
        """
        if not text:
            return None
            
        # Remove command prefix if present
        cleaned_text = text.strip()
        for prefix in ["@dragon", "/dragon", "dragon:", "dragon "]:
            if cleaned_text.lower().startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()
                break
                
        # Process as regular voice command
        command = VoiceCommand(text=cleaned_text, confidence=1.0)
        parsed_command = self.command_parser.parse(command.text)
        
        # Emit command event
        events.emit("text_command", command=parsed_command)
        
        # Call callback if set
        if self._command_callback:
            self._command_callback(parsed_command)
            
        return parsed_command
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        self.deactivate()
        if self.audio_player and self.audio_player._audio:
            self.audio_player._audio.terminate()
        self.logger.info("Voice System shutdown complete")
