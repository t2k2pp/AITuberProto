"""
完全版 AITuberシステム v2.2 - 4エンジン完全対応版（機能削減なし）
Google AI Studio新音声合成（2025年5月追加）+ Avis Speech + VOICEVOX + システムTTS
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from google import genai
from google.genai import types as genai_types
import requests
import asyncio
import json
import time
import os
import threading
import logging
import uuid
import webbrowser
import tempfile
import platform
from datetime import datetime
from pathlib import Path
import aiohttp
import wave
import re
import csv
import traceback

logger = logging.getLogger(__name__)

class VoiceEngineBase:
    def get_available_voices(self): raise NotImplementedError
    async def synthesize_speech(self, text, voice_model, speed=1.0, **kwargs): raise NotImplementedError
    def get_max_text_length(self): raise NotImplementedError
    def get_engine_info(self): return {"name": "Base Engine", "cost": "Unknown", "quality": "Unknown", "description": "Base voice engine"}

class GoogleAIStudioNewVoiceAPI(VoiceEngineBase):
    def __init__(self):
        self.max_length = 2000
        self.voice_models = sorted(["achernar", "achird", "algenib", "algieba", "alnilam", "aoede", "autonoe", "callirrhoe", "charon", "despina", "enceladus", "erinome", "fenrir", "gacrux", "iapetus", "kore", "laomedeia", "leda", "orus", "puck", "pulcherrima", "rasalgethi", "sadachbia", "sadaltager", "schedar", "sulafat", "umbriel", "vindemiatrix", "zephyr", "zubenelgenubi"])
        self.client = None
    def _initialize_client(self, api_key=None):
        if self.client is None or api_key: self.client = genai.Client(api_key=api_key if api_key else os.getenv("GOOGLE_API_KEY"))
    def get_available_voices(self): return self.voice_models
    def get_max_text_length(self): return self.max_length
    def get_engine_info(self): return {"name": "Google AI Studio 新音声", "cost": "無料枠あり", "quality": "★★★★★", "description": "最新技術・リアルタイム・多言語"}
    async def synthesize_speech(self, text, voice_model="puck", speed=1.0, api_key=None, **kwargs):
        try:
            self._initialize_client(api_key)
            if not self.client: raise ValueError("Google AI Client not initialized. API key missing?")
            logger.info(f"GoogleAIStudioNew: Synthesizing '{text[:30]}...' with voice '{voice_model}'")
            config = genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_model))))
            response = await asyncio.to_thread(self.client.models.generate_content, model="gemini-2.5-flash-preview-tts", contents=text, config=config)
            audio_part = next((p for p in response.candidates[0].content.parts if p.inline_data and p.inline_data.mime_type.startswith("audio/")), None)
            if audio_part and audio_part.inline_data.data:
                temp_filename = ""
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf: temp_filename = tf.name
                with wave.open(temp_filename, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
                    wf.writeframes(audio_part.inline_data.data)
                logger.info(f"GoogleAIStudioNew: Success, file: {temp_filename}")
                return [temp_filename]
            logger.error(f"GoogleAIStudioNew: No audio data in response. Parts: {response.candidates[0].content.parts if response.candidates else 'No candidates'}")
            return []
        except Exception as e: logger.error(f"GoogleAIStudioNew: Error - {e}\n{traceback.format_exc()}"); return []

class AvisSpeechEngineAPI(VoiceEngineBase):
    def __init__(self): self.base_url = "http://127.0.0.1:10101"; self.max_length = 1000; self.speakers = []; self.is_available = False
    async def check_availability(self):
        try:
            async with aiohttp.ClientSession() as s, s.get(f"{self.base_url}/speakers", timeout=2) as resp:
                if resp.status == 200: self.speakers = await resp.json(); self.is_available = True; return True
        except Exception: pass
        self.is_available = False; return False
    def get_available_voices(self):
        if not self.is_available and not self.speakers: # speakersが空でもcheck_availabilityを試みる
             try: asyncio.run(self.check_availability())
             except RuntimeError: # Already in a running loop
                 pass # Let it proceed, might be called from async context later
        return [f"{s['name']}({style['name']})" for s in self.speakers for style in s.get('styles', [])] or ["Anneli(ノーマル)"] # Fallback
    def get_max_text_length(self): return self.max_length
    def get_engine_info(self): return {"name": "Avis Speech", "cost": "無料", "quality": "★★★★☆", "description": "ローカル・高品質"}
    def _parse_voice_name(self, name):
        try:
            s_name, st_name = (name.split('(')[0], name.split('(')[1][:-1]) if '(' in name else (name, None)
            for s in self.speakers:
                if s['name'] == s_name:
                    for st in s.get('styles', []):
                        if st_name is None or st['name'] == st_name: return st['id']
            return self.speakers[0]['styles'][0]['id'] if self.speakers and self.speakers[0].get('styles') else 888753760
        except: return 888753760
    async def synthesize_speech(self, text, voice_model="Anneli(ノーマル)", speed=1.0, **kwargs):
        if not self.is_available and not await self.check_availability(): return []
        sid = self._parse_voice_name(voice_model)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{self.base_url}/audio_query", params={'text':text,'speaker':sid}, timeout=5) as r_aq:
                    if r_aq.status!=200: logger.error(f"Avis AQ Err: {r_aq.status}"); return []
                    aq = await r_aq.json()
                if 'speedScale' in aq: aq['speedScale'] = speed
                async with s.post(f"{self.base_url}/synthesis", params={'speaker':sid}, json=aq, timeout=20) as r_sy:
                    if r_sy.status!=200: logger.error(f"Avis Synth Err: {r_sy.status}"); return []
                    data = await r_sy.read()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf: tf.write(data); fname=tf.name
                    return [fname]
        except Exception as e: logger.error(f"AvisSpeech Error: {e}"); return []

class VOICEVOXEngineAPI(VoiceEngineBase):
    def __init__(self): self.base_url = "http://127.0.0.1:50021"; self.max_length = 500; self.speakers = []; self.is_available = False
    async def check_availability(self):
        try:
            self.speakers = [] # Reset before check
            async with aiohttp.ClientSession() as s, s.get(f"{self.base_url}/speakers", timeout=2) as resp:
                if resp.status == 200:
                    self.speakers = await resp.json()
                    if self.speakers: self.is_available = True; logger.info(f"VOICEVOX OK, Speakers: {len(self.speakers)}"); return True
                    logger.warning("VOICEVOX OK, but no speakers.")
        except Exception as e: logger.warning(f"VOICEVOX connection error: {e}")
        self.is_available = False; return False
    def get_available_voices(self):
        if not self.is_available and not self.speakers:
            try: asyncio.run(self.check_availability())
            except RuntimeError: pass
        return sorted([f"{s['name']}({st['name']})" for s in self.speakers for st in s.get('styles',[])]) or ["ずんだもん(ノーマル)"]
    def get_max_text_length(self): return self.max_length
    def get_engine_info(self): return {"name": "VOICEVOX", "cost": "無料", "quality": "★★★☆☆", "description": "ローカル・キャラクター多数"}
    def _parse_voice_name(self, name):
        try:
            s_name, st_name = (name.split('(')[0], name.split('(')[1][:-1]) if '(' in name else (name, "ノーマル")
            if self.speakers:
                for s_info in self.speakers:
                    if s_info.get('name') == s_name:
                        for style_info in s_info.get('styles', []):
                            if style_info.get('name') == st_name: return style_info['id']
            # Fallback for common characters if speakers list is not populated or match fails
            mapping = {"ずんだもん": {"ノーマル": 3, "あまあま":1}, "四国めたん": {"ノーマル": 2}, "春日部つむぎ": {"ノーマル": 8}}
            return mapping.get(s_name, {}).get(st_name, 3) # Default to Zundamon Normal
        except: return 3
    async def synthesize_speech(self, text, voice_model="ずんだもん(ノーマル)", speed=1.0, **kwargs):
        if not self.is_available and not await self.check_availability(): return []
        sid = self._parse_voice_name(voice_model)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{self.base_url}/audio_query", params={'text':text,'speaker':sid}, timeout=5) as r_aq:
                    if r_aq.status!=200: logger.error(f"VOICEVOX AQ Err: {r_aq.status}"); return []
                    aq = await r_aq.json()
                if 'speedScale' in aq: aq['speedScale'] = speed
                async with s.post(f"{self.base_url}/synthesis", params={'speaker':sid}, json=aq, timeout=20) as r_sy:
                    if r_sy.status!=200: logger.error(f"VOICEVOX Synth Err: {r_sy.status}"); return []
                    data = await r_sy.read()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf: tf.write(data); fname=tf.name
                    return [fname]
        except Exception as e: logger.error(f"VOICEVOX Error: {e}"); return []

class SystemTTSAPI(VoiceEngineBase):
    def __init__(self):
        self.max_length = 300; self.system = platform.system()
        if self.system == "Windows": self.voice_models = ["Microsoft Haruka Desktop", "Microsoft Zira Desktop", "Microsoft Ayumi OneCore"]; self.default_voice = "Microsoft Haruka Desktop"
        elif self.system == "Darwin": self.voice_models = ["Kyoko", "Otoya", "Samantha"]; self.default_voice = "Kyoko"
        else: self.voice_models = ["default", "english", "japanese"]; self.default_voice = "default"
    def get_available_voices(self): return self.voice_models
    def get_max_text_length(self): return self.max_length
    def get_engine_info(self): return {"name": "System TTS", "cost": "無料", "quality": "★★☆☆☆", "description": "OS標準・オフライン"}
    async def synthesize_speech(self, text, voice_model=None, speed=1.0, **kwargs):
        voice_model = voice_model or self.default_voice
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf: fname = tf.name
        success = False
        try:
            if self.system == "Windows": success = await self._windows_tts(text, fname, voice_model, speed)
            elif self.system == "Darwin": success = await self._macos_tts(text, fname, voice_model, speed)
            else: success = await self._linux_tts(text, fname, voice_model, speed)
            if success and os.path.exists(fname) and os.path.getsize(fname) > 44: return [fname]
            if os.path.exists(fname): os.unlink(fname)
            return []
        except Exception as e: logger.error(f"SystemTTS Error: {e}"); if os.path.exists(fname): os.unlink(fname); return []

    async def _windows_tts(self, text, path, voice, spd):
        rate = int(max(-10, min(10, (spd - 1.0) * 5)))
        safe_text = text.replace("'", "''").replace('"', '""').replace("`", "``")
        ps_script = f'''Add-Type -AssemblyName System.speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; try{{$v=$s.GetInstalledVoices()|Where-Object{{$_.VoiceInfo.Name -like "*{voice}*"}}|Select -First 1;if($v){{$s.SelectVoice($v.VoiceInfo.Name)}}else{{$s.SelectVoice((($s.GetInstalledVoices())|Where-Object{{$_.VoiceInfo.Culture -eq "ja-JP"}}|Select -First 1).VoiceInfo.Name)}}}}catch{{}}; $s.Rate = {rate}; $s.SetOutputToWaveFile("{path}"); $s.Speak("{safe_text}"); $s.Dispose()'''
        proc = await asyncio.create_subprocess_exec("powershell", "-NoProfile", "-Command", ps_script, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await proc.communicate()
        if proc.returncode != 0: logger.error(f"Windows TTS PowerShell Error: {stderr.decode(errors='ignore')}"); return False
        return True
    async def _macos_tts(self, text, path, voice, spd):
        rate = int(175 * spd)
        proc = await asyncio.create_subprocess_exec("say", "-v", voice, "-r", str(rate), "-o", path, "--data-format=LEI16@22050", text)
        await proc.wait(); return proc.returncode == 0
    async def _linux_tts(self, text, path, voice, spd):
        rate = int(160 * spd)
        for engine_cmd, args_fn in [("espeak-ng", lambda v,r,p,t: ["-v", v if v!="default" else "en", "-s", str(r), "-w", p, t]), ("spd-say", lambda v,r,p,t: ["-r", str(int((spd-1)*20)),"-o",p,"-w",t])]:
            try:
                proc = await asyncio.create_subprocess_exec(engine_cmd, *args_fn(voice, rate, path, text))
                await proc.wait()
                if proc.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 44: return True
                if os.path.exists(path): os.unlink(path)
            except FileNotFoundError: continue
        logger.warning("Linux TTS: No suitable engine (espeak-ng, spd-say) found or synthesis failed.")
        return False

class AudioPlayer:
    def __init__(self, config_manager=None):
        self.system = platform.system()
        self.config_manager = config_manager

    def get_available_output_devices(self):
        devices = [{"name": "デフォルト", "id": "default"}]
        try:
            if self.system == "Windows":
                import subprocess
                cmd = 'powershell "Get-AudioDevice -List | Where-Object {$_.Type -eq \'Playback\' -and $_.State -eq \'Active\'} | Select-Object -Property Name, ID, Default | Format-Table -HideTableHeaders"'
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='ignore')
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            is_default_str = parts[-1]
                            dev_id_candidate = parts[-2] if (is_default_str == "True" or is_default_str == "False") and len(parts) > 2 else parts[-1]
                            name_parts_end_index = -2 if (is_default_str == "True" or is_default_str == "False") and len(parts) > 2 else -1
                            name = " ".join(parts[:name_parts_end_index]).strip()
                            if name and dev_id_candidate and not any(d["id"] == dev_id_candidate for d in devices):
                                devices.append({"name": name, "id": dev_id_candidate})
            elif self.system == "Darwin":
                import subprocess; import json
                cmd = "system_profiler SPAudioDataType -json"
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True, encoding='utf-8', errors='ignore')
                    data = json.loads(result.stdout)
                    for item in data.get("SPAudioDataType", []):
                        for sub_item in item.get("_items", []):
                            dev_name = sub_item.get("coreaudio_device_name")
                            transport = sub_item.get("coreaudio_device_transport","")
                            if dev_name and ("output" in transport or "speaker" in dev_name.lower() or "headphones" in dev_name.lower()):
                                if not any(d["id"] == dev_name for d in devices):
                                    devices.append({"name": dev_name, "id": dev_name})
                except Exception as e_mac: logger.warning(f"macOS audio device list error: {e_mac}")
            elif self.system == "Linux":
                # This section is simplified to avoid the previous SyntaxError.
                # A more robust device listing for Linux would require careful parsing of 'aplay -L' or 'pactl list sinks'.
                logging.info("Linux audio device listing uses a simplified approach. Only 'default' may be available or accurate.")
                # The 'default' device is already added. We might try to add 'pulse' if it's commonly available.
                if not any(d["id"] == "pulse" for d in devices):
                     devices.append({"name": "PulseAudio Sound Server", "id": "pulse"})

        except Exception as e: logger.error(f"Error getting audio devices: {e}")
        final_devices = []; seen_ids = set()
        if any(d["id"] == "default" for d in devices): final_devices.append({"name": "デフォルト", "id": "default"}); seen_ids.add("default")
        for dev in devices:
            if dev["id"] not in seen_ids: final_devices.append(dev); seen_ids.add(dev["id"])
        return final_devices

    async def play_audio_files(self, audio_files, delay_between=0.05):
        for i, audio_file in enumerate(audio_files):
            if os.path.exists(audio_file):
                logger.info(f"Playing {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
                await self.play_audio_file(audio_file)
                if delay_between > 0 and i < len(audio_files) - 1: await asyncio.sleep(delay_between)
                try: await asyncio.to_thread(os.unlink, audio_file)
                except Exception as del_e: logger.warning(f"Failed to delete temp audio file {audio_file}: {del_e}")
    async def play_audio_file(self, audio_file):
        try:
            if self.system == "Windows": await self._play_windows(audio_file)
            elif self.system == "Darwin": await self._play_macos(audio_file)
            else: await self._play_linux(audio_file)
        except Exception as e: logger.error(f"Error playing audio file {audio_file}: {e}")

    async def _play_windows(self, audio_file):
        dev_id = self.config_manager.get_system_setting("audio_output_device", "default") if self.config_manager else "default"
        try:
            if dev_id != "default": logger.warning(f"Windows: Device specific playback for '{dev_id}' not fully supported, using default.")
            import winsound
            await asyncio.to_thread(winsound.PlaySound, audio_file, winsound.SND_FILENAME | winsound.SND_NOWAIT) # Use SND_NOWAIT for async
            # Since SND_NOWAIT returns immediately, we need a way to know when it's done if we need to wait.
            # For simplicity here, we assume it plays and moves on. If precise timing or waiting is needed,
            # PowerShell or another library like `sounddevice` would be better.
            # For now, a small fixed delay might be needed if subsequent actions depend on sound finishing.
            # await asyncio.sleep(1) # Example: wait 1 sec, adjust based on typical audio length
        except Exception as e:
            logger.error(f"Windows playback error (winsound): {e}. Trying PowerShell fallback.")
            # PowerShell fallback can be blocking, consider if this is acceptable.
            ps_script = f'$player=New-Object System.Media.SoundPlayer("{audio_file}");$player.PlaySync();$player.Dispose()'
            proc = await asyncio.create_subprocess_exec("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script, stderr=asyncio.subprocess.PIPE)
            _, stderr = await proc.communicate()
            if proc.returncode != 0: logger.error(f"PowerShell playback error: {stderr.decode(errors='ignore')}")

    async def _play_macos(self, audio_file):
        try:
            proc = await asyncio.create_subprocess_exec("afplay", audio_file)
            await proc.wait()
        except Exception as e: logger.error(f"macOS afplay error: {e}")
    async def _play_linux(self, audio_file):
        dev_id = self.config_manager.get_system_setting("audio_output_device", "default") if self.config_manager else "default"
        cmd_list = ["aplay"]
        if dev_id != "default": cmd_list.extend(["-D", dev_id])
        cmd_list.append(audio_file)
        try:
            proc = await asyncio.create_subprocess_exec(*cmd_list, stderr=asyncio.subprocess.PIPE)
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"aplay failed (code {proc.returncode}): {stderr.decode(errors='ignore')}. Trying paplay.")
                cmd_list = ["paplay"]
                if dev_id != "default": cmd_list.extend(["--device", dev_id])
                cmd_list.append(audio_file)
                proc_pa = await asyncio.create_subprocess_exec(*cmd_list, stderr=asyncio.subprocess.PIPE)
                _, stderr_pa = await proc_pa.communicate()
                if proc_pa.returncode != 0: logger.error(f"paplay failed: {stderr_pa.decode(errors='ignore')}")
        except FileNotFoundError: logger.error("aplay/paplay not found on Linux.")
        except Exception as e: logger.error(f"Linux playback error: {e}")


class VoiceEngineManager:
    def __init__(self):
        self.engines = {
            "google_ai_studio_new": GoogleAIStudioNewVoiceAPI(),
            "avis_speech": AvisSpeechEngineAPI(),
            "voicevox": VOICEVOXEngineAPI(),
            "system_tts": SystemTTSAPI()
        }
        self.current_engine = "google_ai_studio_new"  # デフォルトエンジン
        # エンジンの優先順位を直接リストとして定義 (strings.DEFAULT_ENGINE_PRIORITY を使用しない)
        self.priority = [
            "google_ai_studio_new",
            "avis_speech",
            "voicevox",
            "system_tts"
        ]
    def get_engine_instance(self, name): return self.engines.get(name)
    def set_engine(self, name): self.current_engine = name if name in self.engines else self.current_engine; return name in self.engines
    def get_current_engine(self): return self.engines[self.current_engine]
    def get_available_engines(self): return list(self.engines.keys())
    def get_engine_info(self, name): return self.engines[name].get_engine_info() if name in self.engines else {}
    async def check_engines_availability(self): return {name: (await e.check_availability() if hasattr(e, 'check_availability') else True) for name, e in self.engines.items()}
    async def synthesize_with_fallback(self, text, voice_model, speed=1.0, preferred_engine=None, api_key=None):
        order = ([preferred_engine] if preferred_engine and preferred_engine in self.engines else []) + \
                  [p for p in self.priority if p != preferred_engine]
        if not order and self.priority: order = self.priority # preferred_engine が無効な場合、デフォルト優先度を使用
        elif not order and not self.priority: order = list(self.engines.keys())# 万が一priorityも空なら全エンジン

        for engine_name in order:
            try:
                logger.info(f"Fallback: Trying engine {engine_name}")
                engine = self.engines[engine_name]
                if hasattr(engine, 'check_availability') and not await engine.check_availability():
                    logger.warning(f"⚠️ Engine {engine_name} is not available."); continue

                kwargs_synth = {'api_key': api_key} if "google_ai_studio" in engine_name else {}
                # voice_modelがNoneの場合、エンジン側のデフォルトを使用させるか、ここでエラーとするか。
                # 現状はエンジン側の実装に任せる。
                files = await engine.synthesize_speech(text, voice_model, speed, **kwargs_synth)

                if files: logger.info(f"✅ Synthesis successful with {engine_name}"); return files
                logger.warning(f"⚠️ Synthesis failed with {engine_name}")
            except Exception as e_synth: logger.error(f"❌ Error during synthesis with {engine_name}: {e_synth}"); continue
        logger.error("❌ All voice engines failed to synthesize."); return []

    def get_all_voices(self): return {name: (e.get_available_voices() or ["(N/A)"]) for name, e in self.engines.items()}
    def add_voice(self, data): logger.info(f"add_voice called with {data} (not implemented for standard engines)")
    def get_current_engine_name(self): return self.current_engine
