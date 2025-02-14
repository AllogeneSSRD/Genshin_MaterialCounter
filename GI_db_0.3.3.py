
import csv
import json
import os
import requests
import sqlite3

from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from params import synthesis_material

db_path = "C:\\Users\\*\\Documents\\Hutao\\Userdata.db"

# 读取 JSON 元数据
Material_path = "C:\\Users\\*\\Documents\\Hutao\\Metadata\\CHS\\Material.json"
# 保存 JSON 文件
save_material_path = "GI_db_养成材料.json"


working_directory = Path.cwd().resolve()
current_file_path = Path(__file__).resolve().parent /'img' / '材料图标'


# 连接到 SQLite 数据库
conn = sqlite3.connect(db_path)

cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")

tables = cursor.fetchall()

inventory_items = conn.execute("SELECT * FROM inventory_items")

inventory_data = {row[2]: {"Count": row[3]} for row in inventory_items}
cursor.close()
conn.close()


# 打开文件并导入 JSON 数据
with open(Material_path, 'r', encoding='utf-8') as file:
    material_data = json.load(file)

def filter_condition_TypeDescription(TypeDescription):
    return TypeDescription == "" or (
        TypeDescription == "通用货币" or
        TypeDescription == "角色经验素材" or
        # TypeDescription == "角色培养素材" or
        # TypeDescription == "角色突破素材" or
        # TypeDescription == "角色天赋素材" or
        TypeDescription == "角色与武器培养素材" or
        # TypeDescription == "锻造用矿石" or
        TypeDescription == "武器强化素材"
        # TypeDescription == "武器突破素材" or
        # TypeDescription == "蒙德区域特产" or
        # TypeDescription == "璃月区域特产" or
        # TypeDescription == "稻妻区域特产" or
        # TypeDescription == "须弥区域特产" or
        # TypeDescription == "枫丹区域特产" or
        # TypeDescription == "纳塔区域特产" or
        # TypeDescription == "至冬区域特产"
    )

# 使用列表推导式进行筛选
filtered_data = [item for item in material_data if filter_condition_TypeDescription(item["TypeDescription"])]

i = 0
for item in filtered_data:
    i += 1
    item["Count"] = inventory_data.get(item["Id"], {}).get("Count", 0)
    item["Path"] = str(current_file_path.joinpath(item["Icon"] + '.png'))


os.makedirs(os.path.dirname(save_material_path), exist_ok=True)

with open(save_material_path, 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=4)

def download_image(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        image_data = response.content
        print(image_data[:8])
        if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            print("This is a PNG image.")
        else:
            print("This is not a PNG image.")
        with open(save_path, 'wb') as f:
            f.write(image_data)
        return image_data
    except requests.RequestException as e:
        print(f"下载图片时发生错误: {e}")
        return None

for item in filtered_data:
        icon = item["Icon"]
        map_url = "https://gi.yatta.moe/assets/UI/" + icon + ".png"
        save_path = current_file_path.joinpath(f"{icon}.png")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(save_path):
        # 如果不存在，则下载并重命名文件
            download_image(map_url, save_path)
            print(f"文件已下载并重命名为: {save_path}")
        # else:
        #     print(f"文件已存在: {save_path}")

converted_dict = {}
for item in filtered_data:
    # 查找对应的键名
    for key, value in synthesis_material.items():
        if item['Name'] == value:
            converted_dict[key] = [value, str(item['Count'])]

for key in converted_dict:
    if not converted_dict[key]:
        converted_dict[key] = [synthesis_material.get(key, key), '']
        print("\n未获取到的素材自动补全：", key, converted_dict[key])


# 将B中有但A中没有的键添加到A
for key in synthesis_material:
    if key not in converted_dict:
        converted_dict[key] = [synthesis_material[key], '']

print(converted_dict)

def update_csv(materials_count, csv_path) -> None:
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 检查文件是否存在，不存在则创建并添加表头
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
        # 在新接受到的数据中，value会使用默认值填充，长度总是2，不再需要检查
        # value[0] = value[0] if len(value) == 2 else ''
        # value[1] = value[1] if len(value) == 2 else '0'
        if key in existing_data:
            existing_data[key].insert(1, value[1])
        else:
            # 新键，添加空值，直到最新的时间列
            existing_data[key] = [value[0], value[1]] + [''] * (len(headers) - 3)

    print('='*128, existing_data, sep='\n')

    with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        if current_time not in headers:
            headers.insert(2, current_time)
        writer.writerow(headers)
        for key, values in existing_data.items():
            # 确保每行的长度与表头长度一致
            row = [key] + values + [''] * (len(headers) - len(values) - 1)
            writer.writerow(row)

if __name__ == '__main__':
    update_csv(converted_dict, '养成材料_db.csv')
    print("CSV文件已更新。")