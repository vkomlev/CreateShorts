from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip
import pysrt

def create_video(layout_file, subtitles_file=None, audio_file=None, subtitle_coords=None, subtitle_style=None):
    clips = []

    # Чтение разметки видео
    with open(layout_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            timecode, image_path = line.strip().split(',')
            start, end = map(float, timecode.split('-'))
            img_clip = ImageClip(image_path).set_duration(end - start).set_start(start)

            # Добавление эффекта перехода
            if i > 0:
                img_clip = img_clip.crossfadein(1)
            
            clips.append(img_clip)

    # Объединение клипов с эффектами переходов
    video = concatenate_videoclips(clips, method="compose", padding=-1, bg_color=(0, 0, 0))

    # Добавление субтитров
    if subtitles_file:
        subs = pysrt.open(subtitles_file)
        subtitle_clips = []

        for sub in subs:
            start = sub.start.ordinal / 1000.0
            end = sub.end.ordinal / 1000.0

            # Настройки субтитров
            txt_clip = TextClip(sub.text, fontsize=24, color=subtitle_style.get('color', 'white'), 
                                stroke_color=subtitle_style.get('stroke_color', 'yellow'),
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