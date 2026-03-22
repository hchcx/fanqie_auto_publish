"""
去AI化批量处理脚本
对第4-25章进行高频AI痕迹词汇替换
"""
import os
import re
import random

SOURCE_DIR = r"e:\A_project\Demo\小说\fanqie_auto_publish\uploaded\ai编程末日\第一卷"
OUTPUT_DIR = r"e:\A_project\Demo\小说\fanqie_auto_publish\chapters"

def get_chapter_num(filename):
    match = re.match(r'(\d+)', filename)
    return int(match.group(1)) if match else -1

REPLACEMENTS = [
    ("极其精密", ["精密", "做工精细", "精巧"]),
    ("极其坚固", ["坚固", "牢不可破", "结实"]),
    ("极其危险", ["危险", "凶险", "要命"]),
    ("极其紧张", ["紧张", "绷紧了神经"]),
    ("极其复杂", ["复杂", "盘根错节"]),
    ("极其短促", ["短促", "急促"]),
    ("极其急迫", ["急迫", "焦急"]),
    ("极其满意", ["很满意", "满意得不行"]),
    ("极其嚣张", ["嚣张", "张狂"]),
    ("极其简单", ["简单", "简单得可笑"]),
    ("极其流氓", ["流氓", "无赖"]),
    ("极其正经", ["一本正经", "正儿八经"]),
    ("极其利索", ["利索", "麻利"]),
    ("极其机灵", ["机灵", "灵光"]),
    ("极其诡异", ["诡异", "古怪"]),
    ("极其忠实", ["忠实", "老实"]),
    ("极其熟练", ["熟练", "老练"]),
    ("极其敏锐", ["敏锐", "灵敏"]),
    ("极其狂热", ["狂热", "炽烈"]),
    ("极其醒目", ["醒目", "显眼"]),
    ("极其残忍", ["残忍", "狠毒"]),
    ("极其迅速", ["飞快", "赶紧"]),
    ("极其苍凉", ["苍凉", "凄凉"]),
    ("极其", ["很", "非常", "十分", ""]),
    ("瞬间变成", ["变成了", "化作了"]),
    ("瞬间撕裂", ["撕裂了", "一下子撕开"]),
    ("瞬间熄灭", ["熄灭了", "灭了"]),
    ("瞬间扩散", ["四散开来", "扩散了"]),
    ("瞬间被", ["直接被", "立刻被", "当场被"]),
    ("瞬间挤占", ["迅速挤占", "一口气占满"]),
    ("猛然转动", ["转了过来", "转动起来"]),
    ("猛地一亮", ["亮了", "亮了起来"]),
    ("猛地转向", ["转向了", "调转方向"]),
    ("猛地举起", ["举起了", "抬起"]),
    ("猛地抬头", ["抬起头", "抬头"]),
    ("不可思议地", ["难以置信地", "惊讶地"]),
    ("不可思议的", ["离谱的", "让人意外的"]),
    ("宛如一座", ["像一座", "像是一座"]),
    ("宛如一团", ["像一团", "如同一团"]),
    ("宛如一个", ["像一个", "像是一个"]),
    ("令人作呕", ["恶心", "让人想吐"]),
    ("就在这时，", ["这时候，", ""]),
]

def apply_replacements(text):
    modified = text
    change_count = 0
    for pattern, candidates in REPLACEMENTS:
        while pattern in modified:
            replacement = random.choice(candidates)
            modified = modified.replace(pattern, replacement, 1)
            change_count += 1
    return modified, change_count

def process_chapters():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted(os.listdir(SOURCE_DIR))
    total_changes = 0
    processed = 0
    for filename in files:
        if not filename.endswith('.txt'):
            continue
        chapter_num = get_chapter_num(filename)
        if chapter_num < 4 or chapter_num > 25:
            continue
        filepath = os.path.join(SOURCE_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        modified, changes = apply_replacements(content)
        new_filename = f"{chapter_num:03d} 第{chapter_num}章.txt"
        output_path = os.path.join(OUTPUT_DIR, new_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified)
        total_changes += changes
        processed += 1
        print(f"[OK] {filename} -> {new_filename} ({changes} changes)")
    print(f"\nDone! {processed} files, {total_changes} total replacements")

if __name__ == '__main__':
    random.seed(42)
    process_chapters()
