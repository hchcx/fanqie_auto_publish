import os
from PIL import Image, ImageDraw, ImageFont

def main():
    original_image_path = r"e:\A_project\Demo\小说\fanqie_auto_publish\images\novel_cover_1774073187068.png"
    output_image_path = r"e:\A_project\Demo\小说\fanqie_auto_publish\cover_with_text.png"
    
    if not os.path.exists(original_image_path):
        print(f"找不到原图: {original_image_path}")
        return

    img = Image.open(original_image_path)
    draw = ImageDraw.Draw(img)
    
    # 在 Windows 中寻找中文字体
    font_paths = [
        "C:\\Windows\\Fonts\\msyhl.ttc",   # 微软雅黑细体
        "C:\\Windows\\Fonts\\msyh.ttc",    # 微软雅黑
        "C:\\Windows\\Fonts\\simhei.ttf",  # 黑体
        "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
    ]
    
    font_path = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break
            
    if font_path:
        font_large = ImageFont.truetype(font_path, 120)
        font_small = ImageFont.truetype(font_path, 65)
    else:
        print("未找到中文字体！")
        return
        
    title = "AI编程末日"
    subtitle = "只有我会古法编码"
    
    width, height = img.size
    
    # 计算文字宽度以居中
    bbox1 = draw.textbbox((0, 0), title, font=font_large)
    w1 = bbox1[2] - bbox1[0]
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
    w2 = bbox2[2] - bbox2[0]
    
    x1 = (width - w1) // 2
    y1 = int(height * 0.15) # 放在上方 15% 处
    x2 = (width - w2) // 2
    y2 = y1 + 160
    
    # 画简单的黑色阴影增加可读性
    for offset in [(3,3), (4,4), (-2,-2), (2,-2), (-2,2)]:
        draw.text((x1+offset[0], y1+offset[1]), title, font=font_large, fill="black")
        draw.text((x2+offset[0], y2+offset[1]), subtitle, font=font_small, fill="black")
        
    # 主标题和副标题
    draw.text((x1, y1), title, font=font_large, fill="#FFFFFF") # 白色主标题
    draw.text((x2, y2), subtitle, font=font_small, fill="#00FFCC") # 赛博青色副标题
    
    img.save(output_image_path)
    print(f"\n=======================")
    print(f"【成功】带文字的新封面已生成！")
    print(f"文件位置: {output_image_path}")
    print(f"=======================\n")

if __name__ == "__main__":
    main()
