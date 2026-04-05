"""
Arynoxtech_AGI Voice Module
Speech recognition and text-to-speech capabilities
Works completely offline
"""

import logging
import asyncio
import threading
import queue
import tempfile
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Voice configuration"""
    enabled: bool = True
    language: str = "en-US"
    speech_rate: int = 150  # Words per minute
    volume: float = 0.9
    voice_index: int = 0  # Index of voice to use
    energy_threshold: int = 4000  # For speech recognition
    pause_threshold: float = 0.8  # Seconds of silence before phrase is complete
    dynamic_energy_threshold: bool = True
    auto_speak: bool = True  # Automatically speak responses
    speak_responses: bool = True  # Speak AGI responses
    listen_continuously: bool = False  # Listen continuously for speech
    
    def to_dict(self) -> Dict:
        return {
            'enabled': self.enabled,
            'language': self.language,
            'speech_rate': self.speech_rate,
            'volume': self.volume,
            'voice_index': self.voice_index,
            'energy_threshold': self.energy_threshold,
            'pause_threshold': self.pause_threshold,
            'dynamic_energy_threshold': self.dynamic_energy_threshold,
            'auto_speak': self.auto_speak,
            'speak_responses': self.speak_responses,
            'listen_continuously': self.listen_continuously
        }


class VoiceEngine:
    """
    Voice Engine for speech recognition and text-to-speech
    Works completely offline using local models
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        
        # State
        self.is_listening = False
        self.is_speaking = False
        self.speech_queue = queue.Queue()
        
        # Callbacks
        self.on_speech_recognized: Optional[Callable[[str], None]] = None
        self.on_speech_started: Optional[Callable[[], None]] = None
        self.on_speech_finished: Optional[Callable[[], None]] = None
        
        # Components (lazy loaded)
        self.recognizer = None
        self.tts_engine = None
        self.microphone = None
        
        # Threading
        self.listener_thread: Optional[threading.Thread] = None
        self.speaker_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Statistics
        self.stats = {
            'speech_recognized': 0,
            'speech_generated': 0,
            'errors': 0
        }
        
        logger.info("Voice Engine initialized")
    
    def _init_speech_recognition(self):
        """Initialize speech recognition (offline)"""
        try:
            import speech_recognition as sr
            
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.config.energy_threshold
            self.recognizer.pause_threshold = self.config.pause_threshold
            self.recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold
            
            # Initialize microphone
            try:
                self.microphone = sr.Microphone()
                logger.info("Microphone initialized")
            except Exception as e:
                logger.warning(f"Could not initialize microphone: {e}")
                self.microphone = None
            
            logger.info("Speech recognition initialized (offline mode)")
            return True
            
        except ImportError:
            logger.error("SpeechRecognition not installed. Install with: pip install SpeechRecognition")
            return False
        except Exception as e:
            logger.error(f"Error initializing speech recognition: {e}")
            return False
    
    def _check_network(self) -> bool:
        """Check if network is available"""
        try:
            import requests
            requests.get("https://www.google.com", timeout=5)
            return True
        except:
            return False

    def _init_text_to_speech(self):
        """Initialize text-to-speech (online if network available, else offline)"""
        try:
            # Check if network is available for online TTS
            self.online_tts = self._check_network()

            if self.online_tts:
                # Try online TTS with gTTS
                try:
                    from gtts import gTTS
                    self.tts_engine = "online"
                    logger.info("Text-to-speech initialized (online mode with gTTS)")
                    return True
                except ImportError:
                    logger.warning("gTTS not available, falling back to offline")
                    self.online_tts = False

            # Offline TTS with pyttsx3
            import pyttsx3

            self.tts_engine = pyttsx3.init()

            # Configure voice
            voices = self.tts_engine.getProperty('voices')
            if voices and len(voices) > self.config.voice_index:
                self.tts_engine.setProperty('voice', voices[self.config.voice_index].id)

            # Configure rate and volume
            self.tts_engine.setProperty('rate', self.config.speech_rate)
            self.tts_engine.setProperty('volume', self.config.volume)

            logger.info("Text-to-speech initialized (offline mode)")
            return True

        except ImportError:
            logger.error("pyttsx3 not installed. Install with: pip install pyttsx3")
            return False
        except Exception as e:
            logger.error(f"Error initializing text-to-speech: {e}")
            return False
    
    async def initialize(self):
        """Initialize voice components"""
        if not self.config.enabled:
            logger.info("Voice is disabled in configuration")
            return False
        
        # Initialize speech recognition
        if not self._init_speech_recognition():
            logger.warning("Speech recognition initialization failed")
        
        # Initialize text-to-speech
        if not self._init_text_to_speech():
            logger.warning("Text-to-speech initialization failed")
            return False
        
        # Start background threads
        self.running = True
        self._start_speaker_thread()
        
        logger.info("Voice Engine fully initialized")
        return True
    
    def _start_speaker_thread(self):
        """Start background thread for speaking"""
        self.speaker_thread = threading.Thread(
            target=self._speaker_loop,
            daemon=True,
            name="VoiceSpeaker"
        )
        self.speaker_thread.start()
    
    def _speaker_loop(self):
        """Background loop for speaking queued text"""
        while self.running:
            try:
                # Get text from queue (with timeout)
                text = self.speech_queue.get(timeout=1.0)
                
                if text is None:  # Shutdown signal
                    break
                
                self.is_speaking = True
                
                if self.on_speech_started:
                    self.on_speech_started()
                
                # Speak the text
                if self.tts_engine:
                    try:
                        if self.online_tts:
                            # Online TTS with gTTS
                            from gtts import gTTS
                            import tempfile
                            from playsound import playsound

                            # Generate speech
                            tts = gTTS(text=text, lang='en', slow=False)
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                                temp_file = f.name
                                tts.save(temp_file)

                            # Play the audio
                            playsound(temp_file, block=True)

                            # Clean up
                            os.unlink(temp_file)

                        else:
                            # Offline TTS with pyttsx3
                            self.tts_engine.say(text)
                            self.tts_engine.runAndWait()

                        self.stats['speech_generated'] += 1
                    except Exception as e:
                        logger.error(f"Error speaking: {e}")
                        self.stats['errors'] += 1
                
                self.is_speaking = False
                
                if self.on_speech_finished:
                    self.on_speech_finished()
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in speaker loop: {e}")
                self.stats['errors'] += 1
    
    async def speak(self, text: str, interrupt: bool = False):
        """
        Speak text using text-to-speech
        
        Args:
            text: Text to speak
            interrupt: If True, interrupt current speech
        """
        if not self.config.enabled or self.tts_engine is None:
            logger.debug("Voice not enabled or TTS not initialized")
            return
        
        if interrupt:
            # Clear queue and stop current speech
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break
            
            if self.tts_engine:
                try:
                    self.tts_engine.stop()
                except:
                    pass
        
        # Add to queue
        self.speech_queue.put(text)
        logger.debug(f"Queued speech: {text[:50]}...")
    
    async def listen(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> Optional[str]:
        """
        Listen for speech and recognize it
        
        Args:
            timeout: Seconds to wait for speech to start
            phrase_time_limit: Maximum seconds for a phrase
        
        Returns:
            Recognized text or None
        """
        if not self.config.enabled or not self.recognizer or not self.microphone:
            logger.debug("Voice not enabled or recognizer not initialized")
            return None
        
        try:
            import speech_recognition as sr
            
            logger.info("Listening for speech...")
            
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen for speech
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
            
            logger.info("Speech detected, recognizing...")
            
            # Recognize speech using offline engine (Sphinx)
            try:
                text = self.recognizer.recognize_sphinx(audio, language=self.config.language)
                logger.info(f"Recognized: {text}")
                self.stats['speech_recognized'] += 1
                
                if self.on_speech_recognized:
                    self.on_speech_recognized(text)
                
                return text
                
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return None
            except sr.RequestError as e:
                logger.error(f"Recognition error: {e}")
                self.stats['errors'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            self.stats['errors'] += 1
            return None
    
    async def listen_continuously(self, callback: Callable[[str], None]):
        """
        Listen continuously for speech
        
        Args:
            callback: Function to call with recognized text
        """
        if not self.config.enabled or not self.recognizer or not self.microphone:
            logger.debug("Voice not enabled or recognizer not initialized")
            return
        
        self.is_listening = True
        self.on_speech_recognized = callback
        
        def listen_loop():
            import speech_recognition as sr
            
            while self.is_listening and self.running:
                try:
                    with self.microphone as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=10.0)
                    
                    try:
                        text = self.recognizer.recognize_sphinx(audio, language=self.config.language)
                        logger.info(f"Recognized: {text}")
                        self.stats['speech_recognized'] += 1
                        
                        if self.on_speech_recognized:
                            self.on_speech_recognized(text)
                            
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        logger.error(f"Recognition error: {e}")
                        self.stats['errors'] += 1
                        
                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    logger.error(f"Error in listen loop: {e}")
                    self.stats['errors'] += 1
        
        # Start listener thread
        self.listener_thread = threading.Thread(
            target=listen_loop,
            daemon=True,
            name="VoiceListener"
        )
        self.listener_thread.start()
        
        logger.info("Started continuous listening")
    
    def stop_listening(self):
        """Stop continuous listening"""
        self.is_listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        logger.info("Stopped continuous listening")
    
    def get_available_voices(self) -> list:
        """Get list of available voices"""
        if not self.tts_engine:
            return []
        
        try:
            voices = self.tts_engine.getProperty('voices')
            return [
                {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages,
                    'gender': voice.gender
                }
                for voice in voices
            ]
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return []
    
    def set_voice(self, voice_index: int):
        """Set the voice to use"""
        if not self.tts_engine:
            return
        
        try:
            voices = self.tts_engine.getProperty('voices')
            if voices and 0 <= voice_index < len(voices):
                self.tts_engine.setProperty('voice', voices[voice_index].id)
                self.config.voice_index = voice_index
                logger.info(f"Voice set to index {voice_index}")
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
    
    def set_speech_rate(self, rate: int):
        """Set speech rate (words per minute)"""
        if self.tts_engine:
            self.tts_engine.setProperty('rate', rate)
            self.config.speech_rate = rate
            logger.info(f"Speech rate set to {rate} WPM")
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        if self.tts_engine:
            self.tts_engine.setProperty('volume', volume)
            self.config.volume = volume
            logger.info(f"Volume set to {volume}")
    
    async def shutdown(self):
        """Shutdown voice engine"""
        self.running = False
        self.is_listening = False
        
        # Signal speaker thread to stop
        self.speech_queue.put(None)
        
        # Wait for threads
        if self.speaker_thread:
            self.speaker_thread.join(timeout=2.0)
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        # Cleanup TTS engine
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        
        logger.info("Voice Engine shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get voice engine status"""
        return {
            'enabled': self.config.enabled,
            'is_listening': self.is_listening,
            'is_speaking': self.is_speaking,
            'config': self.config.to_dict(),
            'stats': self.stats,
            'has_recognizer': self.recognizer is not None,
            'has_tts': self.tts_engine is not None,
            'has_microphone': self.microphone is not None
        }
