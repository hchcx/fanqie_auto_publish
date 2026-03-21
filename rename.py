import os, glob, re, sys

chapters_dir = r"e:\A_project\Demo\小说\fanqie_auto_publish\chapters"
files = glob.glob(os.path.join(chapters_dir, "*.txt"))

num_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}

for f in files:
    try:
        basename = os.path.basename(f)
        m = re.match(r'^(\d+)\s+第([一二三四五六七八九十]+)章\.txt$', basename)
        if m:
            prefix = m.group(1)
            chn_num = m.group(2)
            arabic = num_map.get(chn_num, chn_num)
            
            with open(f, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            if not lines: continue
            
            first_line = lines[0].strip()
            m2 = re.match(r'^第([一二三四五六七八九十]+)章[：:\s]*(.*)', first_line)
            if m2:
                title = m2.group(2)
                lines[0] = f"第{arabic}章 {title}\n"
            else:
                title = first_line
            
            title = re.sub(r'[\\/*?:"<>|]', "", title)
            
            new_name = f"{prefix}_第{arabic}章 {title}.txt"
            new_path = os.path.join(chapters_dir, new_name)
            
            with open(new_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
                
            os.remove(f)
            print(f"Renamed {basename} -> {new_name}")
        else:
            print(f"Skipped {basename}")
    except Exception as e:
        print(f"Error on {f}: {e}")
