import os
from basic_pitch.inference import predict_and_save

def convert_mp3_to_midi(input_audio_path, output_directory):
    """
    แปลงไฟล์เสียงเป็น MIDI โดยใช้ Basic Pitch Model
    """
    print(f"🎵 กำลังวิเคราะห์และแปลงไฟล์: {input_audio_path} ...")
    
    # predict_and_save จะทำการวิเคราะห์เสียงและสร้างไฟล์ MIDI ให้ทันที
    # save_midi=True: บันทึกเป็นไฟล์ .mid
    # sonify_midi=False: ไม่ต้องสร้างไฟล์เสียง playback ซ้ำ
    # save_model_outputs=False: ไม่ต้องเก็บ raw model output
    # save_notes=False: ไม่ต้องเก็บ note events เป็น csv (เว้นแต่จะเอาไปวิเคราะห์ต่อ)
    
    predict_and_save(
        [input_audio_path],
        output_directory,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False
    )
    
    # สร้างชื่อไฟล์ output อัตโนมัติเพื่อ return ค่ากลับไปใช้งานต่อ
    base_name = os.path.basename(input_audio_path)
    midi_filename = os.path.splitext(base_name)[0] + "_basic_pitch.mid"
    full_midi_path = os.path.join(output_directory, midi_filename)
    
    print(f"✅ สร้างไฟล์ MIDI สำเร็จ: {full_midi_path}")
    return full_midi_path

# --- การใช้งาน ---
# mp3_file = "solo_piano.mp3" # ใส่ชื่อไฟล์ของคุณที่นี่
# midi_file = convert_mp3_to_midi(mp3_file, ".")