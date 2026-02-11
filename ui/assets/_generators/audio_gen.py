import os
import struct
import math
import random
from pathlib import Path

class AudioGenerator:
    """
    مولد الصوتيات الإجرائي (Procedural Audio Generator).
    
    الوظيفة:
    يقوم بإنشاء ملفات صوتية (WAV) باستخدام الرياضيات البحتة دون الحاجة لملفات خارجية.
    يستخدم لتوليد أصوات النظام الافتراضية في حال عدم وجود ملفات مخصصة من المستخدم.
    
    التقنية:
    يستخدم PCM 16-bit encoding مع معدل عينة 44100Hz (جودة CD).
    """
    
    SAMPLE_RATE = 44100
    
    def __init__(self, output_dir: str = None):
        # تحديد مسار الإخراج الافتراضي (Cache)
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # افتراضياً يحفظ في مجلد الكاش
            self.output_dir = Path(__file__).parent.parent / "sounds" / "_generated_cache"
            
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. DSP Primitives (أدوات معالجة الإشارة الأولية)
    # =========================================================================
    def _save_wav(self, filename: str, samples: list):
        """كتابة البيانات الخام إلى ملف WAV حقيقي"""
        filepath = self.output_dir / filename
        
        # تحويل القائمة إلى Bytes (16-bit Little Endian)
        packed_data = bytearray()
        for s in samples:
            # تقييد القيمة بين -32767 و 32767
            s = max(-32767, min(32767, int(s)))
            packed_data.extend(struct.pack('<h', s))
            
        # كتابة الهيدر (WAV Header)
        with open(filepath, 'wb') as f:
            # RIFF Header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + len(packed_data)))
            f.write(b'WAVE')
            
            # fmt Chunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16)) # Chunk size
            f.write(struct.pack('<H', 1))  # PCM Format
            f.write(struct.pack('<H', 1))  # Channels (Mono)
            f.write(struct.pack('<I', self.SAMPLE_RATE)) # Sample Rate
            f.write(struct.pack('<I', self.SAMPLE_RATE * 2)) # Byte Rate
            f.write(struct.pack('<H', 2))  # Block Align
            f.write(struct.pack('<H', 16)) # Bits per sample
            
            # data Chunk
            f.write(b'data')
            f.write(struct.pack('<I', len(packed_data)))
            f.write(packed_data)
            
        print(f"🔊 Generated Sound: {filepath}")

    def _generate_sine_wave(self, freq, duration, volume=1.0):
        """توليد موجة جيبية نقية"""
        samples = []
        num_samples = int(duration * self.SAMPLE_RATE)
        for i in range(num_samples):
            t = float(i) / self.SAMPLE_RATE
            val = math.sin(2.0 * math.pi * freq * t)
            samples.append(val * 32767.0 * volume)
        return samples

    def _apply_envelope(self, samples, attack_time, decay_time):
        """
        تطبيق غلاف (ADSR) لجعل الصوت يبدو طبيعياً.
        Attack: الزمن للوصول لأعلى صوت.
        Decay: الزمن للتلاشي.
        """
        num_samples = len(samples)
        attack_samples = int(attack_time * self.SAMPLE_RATE)
        decay_samples = int(decay_time * self.SAMPLE_RATE)
        
        processed = []
        for i, s in enumerate(samples):
            envelope = 1.0
            if i < attack_samples:
                envelope = i / attack_samples
            elif i > (num_samples - decay_samples):
                remaining = num_samples - i
                envelope = remaining / decay_samples
            
            processed.append(s * envelope)
        return processed

    # =========================================================================
    # 2. Sound Recipes (وصفات الأصوات)
    # =========================================================================
    
    def create_click_sound(self):
        """
        صوت نقرة (Click): عالي التردد وقصير جداً.
        يستخدم للأزرار والقوائم.
        """
        duration = 0.05 # 50ms
        freq = 2000     # 2kHz (High Pitch)
        
        # نستخدم موجة تتلاشى بسرعة
        samples = self._generate_sine_wave(freq, duration, 0.5)
        samples = self._apply_envelope(samples, 0.005, 0.04) # Fast attack, Fast decay
        
        self._save_wav("click.wav", samples)

    def create_hover_sound(self):
        """
        صوت مرور الماوس (Hover): خفيف جداً ومستقبلي (Sci-Fi).
        """
        duration = 0.03 # 30ms
        freq = 800      # Lower Pitch
        
        samples = self._generate_sine_wave(freq, duration, 0.2) # صوت منخفض
        samples = self._apply_envelope(samples, 0.01, 0.02)
        
        self._save_wav("hover.wav", samples)

    def create_success_sound(self):
        """
        صوت نجاح (Success): نغمتين متتاليتين (Major Third).
        يوحي بالإيجابية.
        """
        # Note 1: C5 (523.25 Hz)
        # Note 2: E5 (659.25 Hz)
        dur = 0.15
        
        part1 = self._generate_sine_wave(523.25, dur, 0.6)
        part1 = self._apply_envelope(part1, 0.01, 0.05)
        
        part2 = self._generate_sine_wave(659.25, dur + 0.1, 0.6)
        part2 = self._apply_envelope(part2, 0.01, 0.1)
        
        # دمج النغمتين
        combined = part1 + part2
        self._save_wav("success.wav", combined)

    def create_error_sound(self):
        """
        صوت خطأ (Error): موجة مربعة (Square Wave) منخفضة التردد.
        توحي بالرفض أو المشكلة (Buzz).
        """
        duration = 0.3
        freq = 150 # Low frequency buzz
        
        samples = []
        num_samples = int(duration * self.SAMPLE_RATE)
        for i in range(num_samples):
            t = float(i) / self.SAMPLE_RATE
            # Square wave approximation using Math
            val = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            samples.append(val * 32767.0 * 0.5)
            
        samples = self._apply_envelope(samples, 0.01, 0.1)
        self._save_wav("error.wav", samples)

    def create_panic_sound(self):
        """
        صوت الطوارئ (Panic): صفارة إنذار (Frequency Modulation).
        """
        duration = 1.0
        min_freq = 600
        max_freq = 1200
        
        samples = []
        num_samples = int(duration * self.SAMPLE_RATE)
        for i in range(num_samples):
            t = float(i) / self.SAMPLE_RATE
            # تغيير التردد مع الوقت (Siren Effect)
            current_freq = min_freq + (max_freq - min_freq) * math.fabs(math.sin(2.0 * math.pi * 5 * t))
            val = math.sin(2.0 * math.pi * current_freq * t)
            samples.append(val * 32767.0 * 0.8)
            
        self._save_wav("panic.wav", samples)

    # =========================================================================
    # 3. Master Trigger (المشغل الرئيسي)
    # =========================================================================
    def generate_defaults_if_missing(self):
        """
        الدالة الذكية التي سيستدعيها البرنامج.
        تفحص الملفات، وإذا كان هناك ملف ناقص، تقوم بتوليده.
        """
        required_sounds = {
            "click.wav": self.create_click_sound,
            "hover.wav": self.create_hover_sound,
            "success.wav": self.create_success_sound,
            "error.wav": self.create_error_sound,
            "panic.wav": self.create_panic_sound
        }
        
        for filename, generator_func in required_sounds.items():
            filepath = self.output_dir / filename
            if not filepath.exists():
                # توليد الملف فقط إذا لم يكن موجوداً
                generator_func()

# للاختبار المستقل (عند تشغيل السكربت لوحده)
if __name__ == "__main__":
    gen = AudioGenerator()
    print("🚀 Initializing Audio Factory...")
    gen.generate_defaults_if_missing()
    print("✅ All procedural sounds generated.")