import csv
import json
import os
from pprint import pprint

from pathlib import Path, WindowsPath
from PIL import Image, ImageDraw, ImageFont

# 脚本所在目录
PATH: WindowsPath = Path(__file__).parent.resolve()

__version__ = '0.3.3'
__author__ = '-瑞达喵-'
LAST_COUNT = 3

# 从胡桃数据库读取 JSON 元数据
Material_path = "C:\\Users\\*\\Documents\\Hutao\\Metadata\\CHS\\Material.json"
current_file_path = Path("img\\材料图标")
# 读取 GI_main 生成的 CSV 文件
csv_path: str = f"{PATH}\\养成材料_db.csv"
# 加载字体（确保字体文件存在）
font_path = "font\\原神字体.ttf"

output_path = "GI_db_养成材料.png"  # 输出图片的路径

json_path = Path(f"{PATH}\\GI_db_绘图.json")

if json_path.exists():
    with open(json_path, 'r', encoding='utf-8') as file:
        json_paths = json.load(file)
        print(f"\n导入自定义配置: ") #{json_paths.items()}
        for key, value in json_paths.items():
            print(f"{key}: {value}")
        Material_path = json_paths["Material_path"]
        current_file_path = Path(json_paths["current_file_path"])
        csv_path = json_paths["csv_path"]
        font_path = json_paths["font_path"]
        output_path = json_paths["output_path"]


with open(Material_path, 'r', encoding='utf-8') as file:
    material_data = json.load(file)

def filter_condition_TypeDescription(TypeDescription):
    return TypeDescription == "" or (
        TypeDescription == "通用货币" or
        TypeDescription == "角色经验素材" or
        TypeDescription == "角色与武器培养素材"# or
        # TypeDescription == "武器强化素材"
    )


csv_list = []
with open(csv_path, "r", encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    headers = next(csv_reader)
    # csv_reader = csv.DictReader(file)
    for row in csv_reader:
        # row = list(row.values())
        data_dict = {
            "Name": row[1],
            "Count": row[2],
            "Last": row[LAST_COUNT]
        }
        csv_list.append(data_dict)

date = [headers[2].split()[0], headers[LAST_COUNT].split()[0]]
output_path = f"GI_db_养成材料_{date[0].replace('/', '-')}.png"
print(date)
print(f"获取数据集更新时间 重置路径\noutput_path: {output_path}")
lookup_table = {d['Name']: {'Count': d['Count'], 'Last': d['Last']} for d in csv_list}

filtered_data = [item for item in material_data if filter_condition_TypeDescription(item["TypeDescription"])]


for item in filtered_data:
    name = item['Name']
    lookup_item = lookup_table.get(name, {})
    item.update(lookup_item)
    # 确保 "Count" 和 "Last" 
    item.setdefault("Count", 0)
    item.setdefault("Last", 0)
    # if name in lookup_table:
    #     item.update(lookup_table[name])
    if item["Count"] == '':
        item.update({'Count': 0})
    if item["Last"] == '':
        item.update({'Last': 0})
    item["Path"] = str(current_file_path.joinpath(item["Icon"] + '.png'))
    # print(item["Id"], item["Name"], item.get("Count", 0), item.get("Last", 0), item["Path"])


# 图像大小
icon_size = (256, 256)
# 行数和列数
rows, cols = int(len(filtered_data) / 10 + 1), 10
# 边距
margin = 50
# 上边距
top_margin = 80
# 图标间距
icon_spacing = 10
# 行间距
row_spacing = 64
# 图标下边距
icon_bottom_spacing = 8
# 文字间距
text_spacing = 36


total_width = margin * 2 + (icon_size[0] + icon_spacing) * cols - icon_spacing
total_height = top_margin + margin + (icon_size[1] + row_spacing + 2 * text_spacing) * rows - row_spacing
background_color = (255, 255, 255)
image = Image.new('RGB', (total_width, total_height), background_color)


if os.path.exists(font_path):
    font_32 = ImageFont.truetype(font_path, 32)
    font_24 = ImageFont.truetype(font_path, 24)
else:
    font_32 = ImageFont.load_default()
    font_24 = ImageFont.load_default()

# 绘制图标和文字
draw = ImageDraw.Draw(image)
for i, item in enumerate(filtered_data):
    if i >= cols * rows:
        break  # 超出范围则停止

    # 计算位置
    row = i // cols
    col = i % cols
    x = margin + col * (icon_size[0] + icon_spacing)
    y = top_margin + row * (icon_size[1] + row_spacing + 2 * text_spacing)

    # 加载并绘制图标
    # icon是已经加载的透明背景的PNG图标
    icon = Image.open(item["Path"])
    # 将调色板模式的图像转换为 RGBA 模式
    icon = icon.convert('RGBA')

    # 创建纯白色的背景
    white_background = Image.new('RGB', icon.size, (255, 255, 255))

    # 检查图像是否有alpha通道
    if icon.mode == 'RGBA':
        # 如果有alpha通道，则使用它作为mask
        # 将图标粘贴到白色背景上，透明部分会保持透明
            # 分离图像和 alpha 通道
        r, g, b, a = icon.split()

        # 使用 alpha 通道作为蒙版将 icon 绘制到白色背景上
        # white_background.paste(icon, mask=a)
        white_background.paste(icon, mask=icon.split()[3]) # 3是alpha通道的索引
    else:
        # 如果没有alpha通道，直接粘贴图像
        white_background.paste(icon)

    # white_background来代替原来的icon进行绘制
    image.paste(white_background, (x, y))

    # 绘制文字
    Count = int(item.get("Count", 0))
    Last = int(item.get("Last", 0))
    text_x = x + icon_size[0] // 2
    text_y = y + icon_size[1] + icon_bottom_spacing
    draw.text((text_x, text_y), item["Name"], font=font_32 if len(item["Name"]) <= 10 else font_24, fill=(0, 0, 0), anchor="ma")
    if Count >= 9000 and item["Name"] != "摩拉":
        draw.text((text_x, text_y + text_spacing), f"{item['Count']}", font=font_24, fill='red', anchor="ma")
    else:
        draw.text((text_x, text_y + text_spacing), f"{item['Count']}", font=font_24, fill=(0, 0, 0), anchor="ma")
    change = f'{int(item.get("Count", 0)) - int(item.get("Last", 0)):+d}'
    if change != "+0":
        draw.text((text_x, text_y + text_spacing * 2), f"{change}", font=font_24, fill=(0, 0, 0), anchor="ma")
draw.text(((icon_size[0] * 10 + margin * 2 + icon_spacing * 9) / 2, top_margin / 2),
          f"{date[1]} ~ {date[0]}      Created By Elysia-script {__version__} @{__author__}", font=font_32, fill=(0, 0, 0), anchor="ma")

image.save(output_path)

image.show()
