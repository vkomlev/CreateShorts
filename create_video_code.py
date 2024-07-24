import random
import time
import moviepy.editor as mpy
from moviepy.video.VideoClip import TextClip

# Константы
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
FONT_SIZE = 24
BACKGROUND_COLOR = (70, 70, 70)  # Серый цвет
VIDEO_DURATION = 60  # Максимальная длительность видео в секундах
TEXT_FILE = 'code.txt'  # Путь к текстовому файлу с кодом
AUDIO_FILE = 'audio.mp3'  # Путь к аудиофайлу с озвучкой

def load_code_from_file(file_path):
    """Загрузка текста из файла."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_text_clip(text, duration):
    """Создание клипа с текстом."""
    pos = ('left', 'top')
    clip = TextClip(
        text,
        fontsize=FONT_SIZE,
        font='Consolas',
        color='lightblue',
        bg_color='rgb' + str(BACKGROUND_COLOR),
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        method='caption',
        align='NorthWest'  # Выравнивание по левому краю
    )
    clip = clip.set_duration(duration)
    #clip = clip.set_position(pos)
    return clip

def generate_video(code_lines):
    """Генерация видео с текстом и озвучкой."""
    clips = []
    total_time = 0
    line_num = 1
    line = f'\n\t{line_num}.\t'
    percent = 0
    for char in code_lines:
        # Формируем текст с учетом новых строк
        if char == '\n':
            line_num += 1
            line += char + f'\t{line_num}.\t'
        else:
            line += char
        # Случайная задержка для имитации набора текста
        delay = random.uniform(0.01, 0.2)
        # Создаем текстовый клип и добавляем его к списку
        text_clip = create_text_clip(line, delay)
        clips.append(text_clip)
        total_time += text_clip.duration
        if percent < int(total_time / VIDEO_DURATION * 100):
            percent = int(total_time / VIDEO_DURATION * 100)
            print(percent)
        # Проверяем, не превышает ли общее время 60 секунд
        if total_time >= VIDEO_DURATION:
            break
        

    # Объединение всех клипов в одно видео
    video = mpy.concatenate_videoclips(clips)
    return video

def main():
    # Загрузка кода из файла
    code_lines = load_code_from_file(TEXT_FILE)
    
    # Генерация видео
    video = generate_video(code_lines)

    # Добавление фоновой музыки
    audio = mpy.AudioFileClip(AUDIO_FILE).subclip(0, VIDEO_DURATION)
    video = video.set_audio(audio)

    # Сохранение видео
    video.write_videofile("output_video.mp4", fps=24)

if __name__ == "__main__":
    main()