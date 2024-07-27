from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip
import pysrt
import random

# Константы размера видео
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280

def resize_and_crop(image_clip):
    # Изменение размера с сохранением пропорций
        if abs(image_clip.h - VIDEO_HEIGHT) < abs(image_clip.w - VIDEO_WIDTH):
            image_clip = image_clip.resize(height=VIDEO_HEIGHT)
        else:
            image_clip = image_clip.resize(width=VIDEO_WIDTH)
        
        # Обрезка лишней части
        #image_clip = image_clip.crop(x_center=image_clip.w / 2, y_center=image_clip.h / 2, width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
        return image_clip

def create_video(layout_file, subtitles_file=None, audio_file=None, subtitle_coords=None, subtitle_style=None):
    clips = []

    # Чтение разметки видео
    with open(layout_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            timecode, image_path = line.strip().split(',')
            start, end = map(float, timecode.split('-'))
            img_clip = ImageClip(image_path).set_duration(end - start).set_start(start)

            # Изменение размера и обрезка изображения
            img_clip = resize_and_crop(img_clip)

            # Добавление эффекта перехода
            if i > 0 and img_clip:
                transition_effect = random.choice([img_clip.crossfadein, img_clip.fadein, img_clip.fadeout])
                img_clip = transition_effect(1)
            
            clips.append(img_clip)

    # Объединение клипов с эффектами переходов
    video = concatenate_videoclips(clips, method="compose", padding=-1, bg_color=(0, 0, 0))

    # Ограничение длительности видео одной минутой
    video_duration = min(video.duration, 60)
    video = video.subclip(0, video_duration)

    # Добавление субтитров
    if subtitles_file:
        subs = pysrt.open(subtitles_file)
        subtitle_clips = []

        for sub in subs:
            start = sub.start.ordinal / 1000.0
            end = sub.end.ordinal / 1000.0

            # Настройки субтитров
            txt_clip = TextClip(sub.text, fontsize=24, color=subtitle_style.get('color', 'white'), 
                                stroke_color=subtitle_style.get('stroke_color', 'white'),
                                stroke_width=subtitle_style.get('stroke_width', 1),
                                font=subtitle_style.get('font', 'Arial'))
            txt_clip = txt_clip.set_position(subtitle_coords if subtitle_coords else ('center', 'bottom')).set_duration(end - start).set_start(start)
            subtitle_clips.append(txt_clip)

        subtitles = CompositeVideoClip([video, *subtitle_clips])
        video = subtitles

    # Добавление аудио
    if audio_file:
        audio = AudioFileClip(audio_file)
        video = video.set_audio(audio)

    # Сохранение итогового видео
    video.write_videofile("output_video.mp4", codec='libx264',fps=24)

# Пример вызова функции с дополнительными параметрами для оформления субтитров
subtitle_style = {
    'color': 'yellow',
    #'stroke_color': 'black',
    #'stroke_width': 2,
    'font': 'Arial'
}

create_video("layouts.txt", subtitles_file="subtitles.srt", audio_file="audio.mp3", subtitle_coords=("center", "bottom"), subtitle_style=subtitle_style)