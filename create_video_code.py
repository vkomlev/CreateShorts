import random
import time
import moviepy.editor as mpy
from moviepy.video.VideoClip import ImageClip
from moviepy.video.io.bindings import PIL_to_npimage
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from PIL import Image
from io import BytesIO
from html2image import Html2Image
import os

# Константы
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
FONT_SIZE = 22
BACKGROUND_COLOR = (240, 240, 240)  # Серый цвет
VIDEO_DURATION = 58  # Максимальная длительность видео в секундах
TEXT_FILE = 'code.txt'  # Путь к текстовому файлу с кодом
AUDIO_FILE = 'audio.mp3'  # Путь к аудиофайлу с озвучкой

hti = Html2Image()

def load_code_from_file(file_path):
    """Загрузка текста из файла."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_text_clip(text, duration):
    """Создание клипа с текстом."""
    pos = ('left', 'top')
    
    # Подсветка синтаксиса с помощью Pygments
    lexer = PythonLexer()
    # Устанавливаем стиль форматтера с темным фоном и большим шрифтом
    formatter = HtmlFormatter(style='colorful', full=True, noclasses=True,
                              cssclass="source",
                              prestyles=f"background: rgb({BACKGROUND_COLOR[0]}, {BACKGROUND_COLOR[1]}, {BACKGROUND_COLOR[2]}); font-size: {FONT_SIZE}px;")
    highlighted_code = highlight(text, lexer, formatter)
     # Оборачиваем код в HTML с установленным фоном для всего документа
    html_template = f"""
    <html>
    <head>
    <style>
    body {{
        background-color: rgb({BACKGROUND_COLOR[0]}, {BACKGROUND_COLOR[1]}, {BACKGROUND_COLOR[2]});
        margin: 0;
        padding: 0;
    }}
    pre {{
        font-size: {FONT_SIZE}px;
    }}
    </style>
    </head>
    <body>
    {highlighted_code}
    </body>
    </html>
    """
    # Использование html2image для конвертации HTML в изображение
    temp_image_path = 'temp.png'
    hti.screenshot(html_str=html_template, save_as=temp_image_path, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    
    if os.path.exists(temp_image_path):
        img = Image.open(temp_image_path)
        img_array = PIL_to_npimage(img)

        # Удаляем временное изображение после использования
        os.remove(temp_image_path)

        # Создание клипа из изображения
        clip = ImageClip(img_array, duration=duration)
        return clip
    else:
        raise FileNotFoundError("Temporary image file was not created.")

def generate_video(code_lines):
    """Генерация видео с текстом и озвучкой."""
    clips = []
    total_time = 0
    line_num = 1
    line = f'\n {line_num}. '
    percent = 0
    for char in code_lines:
        # Формируем текст с учетом новых строк
        if char == '\n':
            line_num += 1
            count_spaces = 3 - len(str(line_num))
            space = ' ' * count_spaces
            line += char + f' {line_num}.{space}'
        else:
            line += char
        # Случайная задержка для имитации набора текста
        delay = random.uniform(0.01, 0.12)
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
