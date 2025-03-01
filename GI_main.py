
import csv
import sys
import os
# from ast import Dict, List
from datetime import datetime
from pathlib import Path, WindowsPath
from typing import Dict, List, NoReturn

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

# 脚本所在目录
PATH: WindowsPath = Path(__file__).parent.resolve()
WORKING_DIRECTORY: WindowsPath = Path.cwd().resolve()
sys.path.insert(0, str(PATH))
sys.path.insert(1, str(WORKING_DIRECTORY))

from params import synthesis_material
from Elysia.script.utils.stdin import my_print

# 设定路径
screenshot_path: str = os.path.join(PATH, 'img\\screenshot')
template_path: str = os.path.join(PATH, 'img\\template')
preprocess_image_path: str = os.path.join(PATH, 'img\\preprocess_image')
csv_path: str = f"{PATH}\\合成素材.csv"

# 指定中文字体的路径
font_path: str = f"{PATH}\\font\\LXGWWenKai-Bold.ttf"
# 设置字体和大小
font = ImageFont.truetype(font_path, size=24)
font_prep = ImageFont.truetype(font_path, size=36)


def load_images_from_folder(folder) -> Dict[str, np.ndarray]:
    """
    从指定文件夹读取所有图片
    参数:
    - folder: 图片所在的文件夹

    return: 一个字典，键是文件名，值是图片数据
    """
    images = {}
    for filename in os.listdir(folder):
        if filename.endswith(".jpg") or filename.endswith(".png"):  # 只处理jpg和png图片
            img = cv2.imread(os.path.join(folder, filename))
            if img is not None:
                basename, _ = os.path.splitext(filename)  # 去掉扩展名
                images[basename] = img
    return images


def get_coordinate(screenshot, template, bias=(0,0)) -> tuple[tuple[int, int], float, List[int]]:
    """
    获取模板在截图中的坐标
    参数:
    - screenshot: 截图，一个numpy数组。
    - template: 模板图像，一个numpy数组。
    - bias: 坐标偏移量，元组形式，默认为(0,0)。

    return: 返回一个元组，包含中心坐标、匹配度和匹配区域的左上角和右下角坐标。
    """
    height, width, channel  = template.shape
    if screenshot.shape[2] == 4:
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

    # 模板匹配
    matching = cv2.matchTemplate(screenshot, template, cv2.TM_SQDIFF_NORMED)
    # 比配区左上角坐標
    val, max_val, loc, max_loc = cv2.minMaxLoc(matching)
    x1, y1, x2, y2 = loc[0], loc[1], loc[0] + width, loc[1] + height
    middle = (int(loc[0] + width/2 + bias[0]),
              int(loc[1] + height/2 + bias[1]))
    return middle, round(1 - val, 8), [x1, y1, x2, y2]

def preprocess_image(image, preprocessed_image_path) -> np.ndarray:
    """
    对图像进行预处理，包括灰度化、尺寸调整、二值化等。
    参数:
    - image: 原始图像, 一个numpy数组。
    - preprocessed_image_path: 预处理后的图像保存路径。

    return: 预处理后的图像, 一个numpy数组, 函数内部将处理后的图像保存到指定路径。
    """
    # 可选: 根据路径读取图像 或直接使用传入的图像
    # img = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
    img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 图像尺寸调整，比如放大两倍
    size = 1
    img = cv2.resize(img, (int(img.shape[1] * size), int(img.shape[0] * size)),
                     interpolation=cv2.INTER_CUBIC)

    # 可选: 应用轻微的图像增强
    # img = cv2.equalizeHist(img)

    # 二值化 - 需要根据图像内容调整阈值
    _, img = cv2.threshold(img, 125, 255, cv2.THRESH_BINARY_INV)

    # 可选: 定义结构元素
    kernel_size = 3  # 结构元素的大小
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # 可选: 腐蚀操作
    # img = cv2.erode(img, kernel, iterations=1)

    # 可选: 膨胀操作
    # img = cv2.dilate(img, kernel, iterations=1)

    # 保存预处理后的图像
    cv2.imwrite(preprocessed_image_path, img)

    return img

# 将结果保存为CSV文件
def save_to_new_csv(materials_count, csv_path) -> None:
    """
    将物资计数保存到一个新的CSV文件中。文件名将包含当前时间戳以确保唯一性。
    参数:
    - materials_count: 一个字典，包含物资名称作为键和计数作为值。
    - csv_path: 原始CSV文件的路径，新文件将在同一目录下创建，文件名包含时间戳。

    return: 无
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filename_time = datetime.now().strftime(' %Y-%m-%d %H-%M-%S')
    # 分割文件名和扩展名
    base_name, extension = os.path.splitext(csv_path)
    new_filename = base_name + filename_time + extension
    new_file_path = os.path.join(PATH, new_filename)

    with open(new_file_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow([current_time])  # 写入当前时间作为第一行
        for key, value in materials_count.items():
            writer.writerow([key] + value)

def update_csv(materials_count, csv_path) -> None:
    """
    更新现有的CSV文件，如果文件不存在则创建新文件并添加表头。
    对于每个物资，如果已存在则更新其计数，否则添加新行。
    参数:
    - materials_count: 一个字典，包含物资名称作为键和计数作为值。
    - csv_path: 要更新的CSV文件的路径。

    return: 无
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 检查文件是否存在，如果不存在则创建并添加表头
    if not os.path.exists(csv_path):
        with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(['Key/Time (EN)', 'Key/Time (CN)'] + [current_time])  # 添加表头

    # 读取现有数据
    existing_data = {}
    with open(csv_path, mode='r', newline='', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        headers = next(reader)  # 读取第一行表头
        for row in reader:
            if row:  # 确保行不为空
                existing_data[row[0]] = row[1:]

    # 更新数据
    for key, value in materials_count.items():
        # 检查value的长度，如果不为2，则使用默认值 ['', '0']
        # 由于在新接受到的数据中，value会使用默认值填充，长度总是2，因此不再需要检查
        # value[0] = value[0] if len(value) == 2 else ''
        # value[1] = value[1] if len(value) == 2 else '0'
        if key in existing_data:
            # 将新值插入到列表的第三列 (即第二项，索引为1)
            existing_data[key].insert(1, value[1])
        else:
            # 对于新键，为其添加空值，直到最新的时间列
            existing_data[key] = [value[0], value[1]] + [''] * (len(headers) - 3)

    print('='*64, existing_data, sep='\n')
    # 写入更新后的数据
    with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        if current_time not in headers:
            headers.insert(2, current_time)  # 在第三列插入新的时间
        writer.writerow(headers)
        for key, values in existing_data.items():
            # 确保每行的长度与表头长度一致
            row = [key] + values + [''] * (len(headers) - len(values) - 1)
            writer.writerow(row)

def ocr_text(materials_count, screenshot_results) -> tuple[Image.Image, Image.Image]:
    """
    从屏幕截图中识别文本，并更新物资计数。
    识别结果将在控制台输出，并在图片上绘制识别到的数字和物资的边框。
    参数:
    - materials_count: 一个字典，用于存储识别到的物资计数。
    - screenshot_results: 一个列表，包含屏幕截图中识别到的物资信息，
        每个物资信息包括类名和边框坐标。

    返回: 一个元组，包含处理后的RGB图片和灰度图片的PIL.Image对象。
    """
    # 将screenshot_img从BGR转换为RGB
    screenshot_img_rgb = cv2.cvtColor(screenshot_img, cv2.COLOR_BGR2RGB)
    # 将numpy.ndarray转换为PIL.Image对象
    screenshot_img_pil = Image.fromarray(screenshot_img_rgb)
    draw = ImageDraw.Draw(screenshot_img_pil)

    screenshot_img_gray = preprocess_image(screenshot_img,
                                f"{preprocess_image_path}\\{screenshot_name}_preprocessed.jpg")
    screenshot_img_gray_pil = Image.fromarray(screenshot_img_gray)
    draw_prep = ImageDraw.Draw(screenshot_img_gray_pil)

    for obj in screenshot_results:
        # 获取素材的bounding box坐标
        x1, y1, x2, y2 = obj[3]

        # 假设数字位于素材正下方，定义一个区域来读取数字
        # 确保坐标为整数
        num_x1 = int(x1 + 25)
        num_y1 = int(y2 - 1)  # 稍微在素材下边框的上面开始
        num_x2 = int(x2 - 25)
        num_y2 = int(num_y1 + 25)  # 假设数字的高度不会超过25像素
        size = 1

        # 从图片中裁剪出数字区域
        num_region = screenshot_img_gray_pil.crop((int(size * num_x1), int(size * num_y1),
                                        int(size * num_x2), int(size * num_y2)))

        # 使用OCR技术来识别数字
        number = pytesseract.image_to_string(
            num_region,
            config='--psm 6 digits --c tessedit_char_whitelist=0123456789'
        )
        number = number.replace("-", "").replace(".", "")

        # 绘制数字的bounding box
        draw.rectangle([num_x1, num_y1, num_x2, num_y2], outline="blue", width=2)
        draw_prep.rectangle([int(size * num_x1), int(size * num_y1),
                             int(size * num_x2), int(size * num_y2)],
                             outline="white", width=4)

        # 在数字下方写出识别到的数字
        draw.text((num_x1, num_y2), number.strip(), fill="white", font=font)
        draw_prep.text((int(size * x1 + 14), int(size * num_y2 - 12)),
                        number.strip(), fill="white", font=font_prep)

        # 输出识别结果，使用字典映射来获取中文名称
        class_name = obj[0]
        # 获取中文名称，如果不存在则使用英文名称
        chinese_name = synthesis_material.get(class_name, class_name)
        padded_name = chinese_name.ljust(9, '　')
        print(f'素材 | {padded_name} | 数量: {number.strip()}')

        # 初始化或更新数量
        materials_count[class_name] = [chinese_name, number.strip()]

        # 绘制物品方框和文字
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        draw.text((x1 + 4, y1 + 2), chinese_name, fill="red", font=font)
    return screenshot_img_pil, screenshot_img_gray_pil


if __name__ == '__main__':
    import time
    start_time = time.time()
    screenshot: Dict = load_images_from_folder(screenshot_path)
    template: Dict = load_images_from_folder(template_path)
    my_print(screenshot.keys(), 'other')
    my_print(template.keys(), 'other')
    results: Dict[str, List] = {}
    # 字典存储结果
    materials_count: Dict[str, List] = {key: [] for key in synthesis_material}

    # 遍历每个截图
    for screenshot_name, screenshot_img in screenshot.items():
        if screenshot_name not in results:
            results[screenshot_name] = []
        my_print(f"在截图 {screenshot_name} 中匹配模板：", 'info')

        # 遍历每个模板
        for template_name, template_img in template.items():
            # 获取匹配坐标
            middle, val, coordinate = get_coordinate(screenshot_img, template_img)
            if val >= 0.97:
                results[screenshot_name].append([template_name, middle, val, coordinate])
                print(f"模板 {template_name} 的匹配坐标为 {coordinate}，匹配值为 {val:.4f}")

        screenshot_img_pil, screenshot_img_gray_pil = ocr_text(materials_count, results[screenshot_name])

        # 保存图片
        # screenshot_img_pil.save(f"{preprocess_image_path}\\{screenshot_name}_annotated.png")
        # screenshot_img_gray_pil.save(f"{preprocess_image_path}\\{screenshot_name}_preprocessed_annotated.png")

    # 补全未识别到的素材
    for key in materials_count:
        if not materials_count[key]:
            materials_count[key] = [synthesis_material.get(key, key), '']
            print("\n未获取到的素材自动补全：", key, materials_count[key])

    # 保存结果为CSV
    # print(materials_count)
    # save_to_new_csv(materials_count, csv_path)
    # update_csv(materials_count, csv_path)
    print(time.time() - start_time)
    # 71.312828540802