# tts_module.py
from gtts import gTTS
import os
from playsound import playsound
import tempfile # Để tạo file tạm an toàn hơn

def speak(text_to_speak, lang='vi', slow=False):
    """
    Chuyển văn bản thành giọng nói và phát ra loa.
    Args:
        text_to_speak (str): Văn bản cần nói.
        lang (str): Ngôn ngữ (mặc định là 'vi' - Tiếng Việt).
        slow (bool): Nói chậm hay nhanh (mặc định là False - nhanh).
    """
    if not text_to_speak:
        print("TTS: Không có văn bản để nói.")
        return

    try:
        # print(f"TTS: Đang chuẩn bị nói: '{text_to_speak[:50]}...'") # In một phần để debug
        tts = gTTS(text=text_to_speak, lang=lang, slow=slow)
        
        # Sử dụng tempfile để tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_filename = fp.name
        
        tts.save(temp_filename)
        playsound(temp_filename)
        os.remove(temp_filename) # Xóa file tạm sau khi phát
        # print("TTS: Đã nói xong.") # Bỏ comment nếu muốn debug chi tiết

    except ImportError:
        print("Lỗi TTS: Thư viện gTTS hoặc playsound chưa được cài đặt.")
        print("Vui lòng cài đặt bằng lệnh: pip install gTTS playsound")
    except Exception as e:
        print(f"Lỗi TTS: {e}")
        print("Không thể phát âm thanh. Đảm bảo bạn có kết nối internet (cho gTTS) và cấu hình âm thanh hoạt động.")

if __name__ == '__main__':
    # Test thử module
    print("Bắt đầu thử nghiệm TTS...")
    speak("Xin chào, đây là module chuyển văn bản thành giọng nói.")
    speak("Chúc bạn một ngày tốt lành!", lang='vi')
    # speak("Hello, this is a test in English.", lang='en')
    print("Kết thúc thử nghiệm TTS.")