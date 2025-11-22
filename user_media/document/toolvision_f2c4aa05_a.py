import cv2
import tkinter as tk
from tkinter import simpledialog, messagebox
from pytube import YouTube
from moviepy.editor import VideoFileClip
import threading
import os

# Download path
download_path = os.path.join(os.path.expanduser("~"), "Downloads")

def download_and_preview():
    # Tkinter penceresini oluştur ve gizle
    root = tk.Tk()
    root.withdraw()

    # Kullanıcıdan video URL'si al
    url = simpledialog.askstring("YouTube URL", "Videonun URL'sini girin:")
    if not url:
        return

    try:
        # Video indirme işlemi
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        video_path = stream.download(output_path=download_path, filename="temp_video.mp4")
        messagebox.showinfo("Başarılı", "Video indirildi, şimdi oynatılıyor...")
        
        # Video önizleme ve zaman seçme işlemi
        play_video(video_path)
    except Exception as e:
        messagebox.showerror("Hata", f"Video indirilemedi: {e}")

def play_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps

    # Tkinter penceresi oluştur
    root = tk.Tk()
    root.title("Zaman Seç ve İndir")

    start_var = tk.DoubleVar()
    end_var = tk.DoubleVar(value=duration)

    # Video gösterimi
    def show_video():
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (640, 360))
            cv2.imshow("Video Önizleme", frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):  # 'q' tuşuna basıldığında video durur
                break
        cap.release()
        cv2.destroyAllWindows()

    # Başlangıç ve bitiş zamanlarını güncelle
    def update_labels():
        start_label.config(text=f"Başlangıç (saniye): {start_var.get():.1f}")
        end_label.config(text=f"Bitiş (saniye): {end_var.get():.1f}")
        root.after(100, update_labels)

    # Videoyu kesme işlemi
    def cut_video():
        start = start_var.get()
        end = end_var.get()
        if end <= start:
            messagebox.showerror("Hata", "Bitiş zamanı başlangıçtan büyük olmalı.")
            return

        clip = VideoFileClip(video_path).subclip(start, end)
        save_path = os.path.join(download_path, "kesilmis_video.mp4")
        clip.write_videofile(save_path, codec='libx264', audio_codec='aac')
        messagebox.showinfo("Başarılı", f"Kesilen video: {save_path}")

    # Video oynatma thread'i başlat
    threading.Thread(target=show_video).start()

    # Zaman slider'larını oluştur
    start_slider = tk.Scale(root, from_=0, to=duration, orient="horizontal", resolution=0.1, variable=start_var)
    start_slider.pack()

    end_slider = tk.Scale(root, from_=0, to=duration, orient="horizontal", resolution=0.1, variable=end_var)
    end_slider.pack()

    start_label = tk.Label(root, text="Başlangıç (saniye):")
    start_label.pack()
    end_label = tk.Label(root, text="Bitiş (saniye):")
    end_label.pack()

    update_labels()

    # Video kesme butonu
    download_button = tk.Button(root, text="İndir", command=cut_video)
    download_button.pack()

    root.mainloop()

if __name__ == "__main__":
    download_and_preview()
