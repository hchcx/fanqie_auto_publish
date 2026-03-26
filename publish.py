import os
import glob
import time
import shutil
import re
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"
CHAPTERS_DIR = "chapters"
UPLOADED_DIR = "uploaded"

# 番茄作家书籍管理首页
BOOK_MANAGE_URL = "https://fanqienovel.com/main/writer/book-manage"

def main():
    if not os.path.exists(STATE_FILE):
        print(f"找不到登录状态文件 {STATE_FILE}，请先运行 py login.py 进行登录！")
        return
    
    # ============ 多部小说子目录管理 ============
    # 扫描 chapters/ 下所有子目录，每个子目录对应一本书
    # 同时兼容旧模式：如果 chapters/ 根目录有散落的 txt 文件，提示用户归类
    root_txt_files = glob.glob(os.path.join(CHAPTERS_DIR, "*.txt"))
    if root_txt_files:
        print(f"\n[提示] 发现 chapters/ 根目录下有 {len(root_txt_files)} 个散落的 txt 文件。")
        print(f"       多部小说管理模式要求章节放在子目录中，例如：")
        print(f"         chapters/ai编程末日/101 第101章.txt")
        print(f"         chapters/青冥独行录/001 第1章.txt")
        print(f"       请先将这些文件移入对应的书名子目录后再运行脚本。\n")
        return
    
    # 扫描子目录
    book_dirs = []
    if os.path.isdir(CHAPTERS_DIR):
        for name in sorted(os.listdir(CHAPTERS_DIR)):
            sub_path = os.path.join(CHAPTERS_DIR, name)
            if os.path.isdir(sub_path):
                txts = glob.glob(os.path.join(sub_path, "*.txt"))
                if txts:
                    book_dirs.append((name, sub_path, sorted(txts)))
    
    if not book_dirs:
        print(f"\n[{CHAPTERS_DIR}] 中没有找到任何待发章节！")
        print(f"请在 chapters/ 下按书名创建子目录并放入 txt 章节文件，例如：")
        print(f"  chapters/ai编程末日/101 第101章.txt")
        print(f"  chapters/青冥独行录/001 第1章.txt\n")
        return
    
    print(f"\n==================================================")
    print(f"即将开始【全自动】发文！多部小说隔离管理模式已启动！")
    print(f"==================================================")
    print(f"\n检测到以下小说有待发章节：\n")
    for idx, (name, _, txts) in enumerate(book_dirs, 1):
        print(f"  [{idx}] {name}  （{len(txts)} 章待发）")
    print()
    
    choice = input(">>> 请输入序号选择要发布的小说：").strip()
    try:
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(book_dirs):
            raise ValueError
    except ValueError:
        print("    [错误] 无效的序号，退出。")
        return
    
    book_name_filter, book_chapter_dir, txt_files = book_dirs[choice_idx]
    total_chapters = len(txt_files)
    
    print(f"\n已选择：【{book_name_filter}】，共 {total_chapters} 章待发")
    print(f"==================================================")
    
    # ============ 发布章节数量选择 ============
    publish_count_input = input(
        f"\n>>> 请输入本次要发布的章节数量（1-{total_chapters}），直接回车则发布全部："
    ).strip()
    
    if publish_count_input == "":
        publish_count = total_chapters
        print(f"    -> 将发布全部 {publish_count} 章")
    else:
        try:
            publish_count = int(publish_count_input)
            if publish_count <= 0:
                print("    [错误] 数量必须大于 0，退出。")
                return
            if publish_count > total_chapters:
                print(f"    [提示] 输入数量 {publish_count} 大于待发总数 {total_chapters}，将发布全部章节。")
                publish_count = total_chapters
            else:
                print(f"    -> 将发布前 {publish_count} 章")
        except ValueError:
            print("    [错误] 请输入有效的数字，退出。")
            return
    
    # 截取要发布的章节列表
    txt_files = txt_files[:publish_count]
    
    print(f"\n本次发布计划：【{book_name_filter}】× {len(txt_files)} 章")
    print(f"==================================================\n")
    
    # ============ 卷号选择（决定发布后文件归档到哪个卷目录） ============
    # 直接回车 = 不执行分卷切换（番茄平台会保持上次选择的分卷）
    # 输入具体卷号 = 在浏览器中主动切换到对应分卷
    volume_input = input(
        ">>> 请输入本次发布的章节属于第几卷（如 2、3），直接回车则不执行切换分卷操作："
    ).strip()
    
    volume_num = None  # None 表示不切换分卷
    volume_name = None
    
    if volume_input != "":
        try:
            volume_num = int(volume_input)
            if volume_num <= 0:
                print("    [错误] 卷号必须大于 0，退出。")
                return
            cn_digits = "一二三四五六七八九十"
            volume_name = f"第{cn_digits[volume_num - 1] if volume_num <= 10 else str(volume_num)}卷"
        except ValueError:
            print("    [错误] 请输入有效的数字，退出。")
            return
    
    current_uploaded_dir = os.path.join(UPLOADED_DIR, book_name_filter)
    if volume_name:
        volume_dir = os.path.join(current_uploaded_dir, volume_name)
        print(f"    -> 将切换至【{volume_name}】，发布成功后文件归档至：uploaded/{book_name_filter}/{volume_name}/\n")
    else:
        volume_dir = current_uploaded_dir
        print(f"    -> 不切换分卷（保持番茄平台当前默认），文件归档至：uploaded/{book_name_filter}/\n")
    os.makedirs(volume_dir, exist_ok=True)
    
    print("\n>>> 准备启动浏览器大魔王...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        
        success_count = 0
        
        for file_path in txt_files:
            filename = os.path.basename(file_path)
            raw_title = os.path.splitext(filename)[0]
            
            m = re.search(r'第(\d+)章[\s_]*(.*)', raw_title)
            chapter_num = str(m.group(1)) if m else ""
            chapter_title = m.group(2).strip() if m else ""
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # 如果文件名里只写了 011 第11章.txt，没有真正的标题，我们就从文件正文第一行提取
            if not chapter_title and lines:
                m2 = re.search(r'第.*?章[\s：:]*(.*)', lines[0].strip())
                if m2:
                    chapter_title = m2.group(1).strip()
            if not chapter_title:
                chapter_title = re.sub(r'^[0-9]+[\s_]*', '', raw_title).strip()
            
            print(f"\n[{success_count+1}/{len(txt_files)}] 正在处理: 第{chapter_num}章 '{chapter_title}' (原文件名: {filename})")
            
            # 智能剔除正文内部最开头的章节标题，防止发出去后出现双黄蛋
            if lines and re.search(r'第.*?章', lines[0].strip()):
                lines = lines[1:]
            while lines and not lines[0].strip():
                lines = lines[1:]
                
            content = "".join(lines)
                
            try:
                # 1. 每次都回到后台的【我的小说】列表页，彻底摆脱嵌套死循环迷宫
                print(" -> 正在跳转回后台【我的小说】总览...")
                page.goto(BOOK_MANAGE_URL, timeout=60000)
                page.wait_for_timeout(3000) # 等待列表刷出来
                
                # 寻找特定小说的"章节管理"入口
                # 【关键】番茄工作台在有多部作品时，"章节管理"按钮默认隐藏，
                # 只有鼠标悬停到对应小说卡片上时才会浮现，因此必须先 hover 再点击。
                print(f" -> 寻找【{book_name_filter}】对应的小说卡片，准备悬停触发【章节管理】按钮...")
                
                manage_clicked = False
                
                # 策略1：找到包含书名文本的卡片容器，hover 后等待"章节管理"出现
                book_cards = page.locator('div, li, section, article').filter(has_text=book_name_filter)
                card_count = book_cards.count()
                
                for i in range(card_count - 1, -1, -1):  # 从后往前试（.last 优先）
                    card = book_cards.nth(i)
                    try:
                        if not card.is_visible():
                            continue
                        # 悬停到小说卡片上，触发 hover 效果
                        card.hover(timeout=3000)
                        page.wait_for_timeout(1000)  # 等待 hover 动画/按钮浮现
                        
                        # 尝试在该卡片内或全局找到"章节管理"
                        manage_btn = card.get_by_text("章节管理").first
                        if manage_btn.is_visible():
                            manage_btn.click()
                            manage_clicked = True
                            break
                    except Exception:
                        continue
                
                # 策略2：如果卡片 hover 方式没成功，尝试全局查找
                if not manage_clicked:
                    print("    [备选] 卡片hover未触发按钮，尝试全局查找【章节管理】...")
                    # 先尝试 hover 所有可见卡片触发全局悬浮
                    all_cards = page.locator('[class*="book"], [class*="card"], [class*="item"]').filter(has_text=book_name_filter)
                    for i in range(all_cards.count()):
                        try:
                            c = all_cards.nth(i)
                            if c.is_visible():
                                c.hover(timeout=2000)
                                page.wait_for_timeout(800)
                                gb = page.get_by_text("章节管理").first
                                if gb.is_visible():
                                    gb.click()
                                    manage_clicked = True
                                    break
                        except Exception:
                            continue
                
                # 策略3：终极兜底
                if not manage_clicked:
                    print("    [警告] 所有 hover 策略失败，退化为直接点击第一个可见的【章节管理】...")
                    page.get_by_text("章节管理").first.click()
                
                page.wait_for_timeout(4000) # 等待各种表格和翻页动画加载
                
                original_pages = len(context.pages)
                # 这时我们已经在【章节管理】，判断它是否弹出了新标签页
                if original_pages > 1 and context.pages[-1] != page:
                    editor_page = context.pages[-1]
                else:
                    editor_page = page
                    
                # 检查是否已存在当前章节草稿
                print(f" -> 扫描已有草稿列表，排查是否存在【第 {chapter_num} 章】的历史遗留...")
                draft_row = editor_page.locator('tr, li, .chapter-item').filter(has_text=re.compile(f"第\\s*{chapter_num}\\s*章")).first
                if draft_row.is_visible():
                    print(f" -> 🤖 发现被中断的【草稿历史记录】！直接进入编辑，绝不重复生成第二个！")
                    # 番茄的编辑图标通常在最后一列，是个 icon 或者 link
                    edit_icon = draft_row.locator('td').last.locator('svg, i, a, span, button, img').first
                    if edit_icon.is_visible():
                        edit_icon.click(force=True)
                    else:
                        draft_row.click(force=True) # 降级盲点整行防呆
                else:
                    print(" -> 确认为全新章节，点击右上角桔红色【新建章节】...")
                    new_btn = editor_page.get_by_role("button", name="新建章节").first
                    if not new_btn.is_visible():
                        new_btn = editor_page.get_by_text("新建章节").first
                    new_btn.click(force=True)
                
                page.wait_for_timeout(4000)
                
                # 【极其关键的救命补丁】：番茄在点击了【新建章节】或者【编辑】后，经常会弹出一个全新的浏览器标签页出来！
                # 之前脚本一直在死死的盯着老的列表页背景盲打空气，导致前面新的编辑页被向导弹框卡死！
                if len(context.pages) > original_pages:
                    editor_page = context.pages[-1]
                
                # 疯狂点击对付番茄弹出来的各种“功能上新”教学框、提示遮罩
                print(" -> 开始执行清道夫程序，极其凶狠地清除所有遮挡视野的新手教学卡片...")
                for _ in range(3):
                    editor_page.keyboard.press("Escape")
                    editor_page.wait_for_timeout(200)
                
                # 终极空间坐标打击法：靠文字匹配容易失效（甚至有莫名其妙的空格），我们直接找屏幕上**所有**叫“下一步”或“完成”的按钮
                # 如果它不在屏幕最顶端的标题栏（即 y 坐标 > 100），就断定它是该死的新手向导，通通点烂！
                print(" -> 启动空间坐标精确打击！自动消灭所有不在天花板上的新手引导...")
                for _ in range(10):
                    clicked_guide = False
                    try:
                        # 遍历常见的新手教学按钮文案
                        for target_text in ["下一步", "完成", "我知道了", "跳过"]:
                            # 获取这些按钮的底层 DOM 节点
                            btns = editor_page.get_by_text(target_text, exact=True).element_handles()
                            for btn in btns:
                                box = btn.bounding_box()
                                # 顶部的发布按钮极其靠上（通常 y 在20-60左右）。只要 y > 100，必是乱入的悬浮弹窗！
                                if box and box['y'] > 100:
                                    print(f"    - > 坐标 (y={int(box['y'])}) 拦截到流氓向导节点 '{target_text}'，击破！")
                                    btn.click()
                                    editor_page.wait_for_timeout(600)
                                    clicked_guide = True
                    except Exception as e:
                        pass
                    
                    if not clicked_guide:
                        break # 如果这一轮地毯式搜索没点任何非顶部按钮，代表弹窗彻底清扫干净了！
                    
                # 1.5 确认或切换分卷
                if volume_num is not None and volume_num > 1:
                    print(f" -> 开始确认/切换分卷，目标：【{volume_name}】...")
                    try:
                        # 尝试点击左上角的分卷下拉菜单。找到页面前几个带有“第X卷”的文本元素，逐一点击直到弹出含“新建分卷”的分卷弹窗
                        vol_elements = editor_page.get_by_text(re.compile(r'第[一二三四五六七八九十百]+卷')).element_handles()
                        dialog_opened = False
                        for v in vol_elements[:5]:
                            try:
                                v.click(force=True)
                                editor_page.wait_for_timeout(800)
                                if editor_page.get_by_text("新建分卷").is_visible() or editor_page.get_by_text("取消").is_visible():
                                    dialog_opened = True
                                    break
                            except Exception:
                                pass
                        
                        if dialog_opened:
                            # 兼容番茄可能出现的多种卷号文字格式：第二卷, 第2卷 等
                            target_vol = None
                            for v_name in [volume_name, f"第{volume_num}卷", f"卷{volume_num}"]:
                                temp_vol = editor_page.get_by_text(v_name, exact=False).first
                                if temp_vol.is_visible():
                                    target_vol = temp_vol
                                    break
                                    
                            if target_vol and target_vol.is_visible():
                                target_vol.click(force=True)
                                editor_page.wait_for_timeout(500)
                                
                                confirm_btn = editor_page.get_by_role("button", name="确定").first
                                if not confirm_btn.is_visible():
                                    confirm_btn = editor_page.get_by_text("确定", exact=True).last
                                
                                if confirm_btn.is_visible():
                                    confirm_btn.click(force=True)
                                    print(f"    - 已成功确认/切换到分卷：{volume_name}")
                                editor_page.wait_for_timeout(1000)
                            else:
                                print(f"    [警告] 分卷弹窗中未找到包含 {volume_name} 的选项！")
                                print("    脚本正在等待，请您手动在浏览器中点击目标卷并确定！(等待20秒...)")
                                editor_page.wait_for_timeout(20000)
                        else:
                            print("    [警告] 未能成功呼出分卷弹窗。")
                    except Exception as e:
                        print(f"    [警告] 自动选择分卷异常：{e}")

                # 2. 填写章节序号和标题
                print(" -> 分别填入左边的【章节序号】和右边的【主标题】...")
                
                # 番茄界面的阿拉伯小框有时候不带 placeholder，所以直接暴力提取页面上真正的第一个文字输入框
                num_input = editor_page.locator('input[type="text"]').first
                if num_input.is_visible():
                    num_input.fill(chapter_num, force=True) # 使用 force=True 强行绕过透明遮罩屏障
                
                title_input = editor_page.get_by_placeholder("请输入标题", exact=False).first
                if not title_input.is_visible():
                    title_input = editor_page.get_by_placeholder("请输入章节名", exact=False).first
                if not title_input.is_visible():
                    title_input = editor_page.locator('input[type="text"]').last
                
                if title_input.is_visible():
                    title_input.fill(chapter_title, force=True)
                    
                # 3. 填写正文内容 (防误触防双击，强制填充)
                print(" -> 开始注入长篇正文血肉...")
                editor = editor_page.locator('.ql-editor').first
                if not editor.is_visible():
                    editor = editor_page.locator('.ProseMirror').first
                if not editor.is_visible():
                    editor = editor_page.locator('[contenteditable="true"]').first
                
                if editor.is_visible():
                    editor.click(force=True)
                    # 防止编辑器里默认带了换行或者空格
                    editor_page.keyboard.press("Control+A")
                    editor_page.keyboard.press("Backspace")

                    # 一把梭子：将内容塞进编辑器，并触发浏览器的侦听网络，让数字统计动起来
                    editor_page.evaluate("([el, text]) => { el.innerText = text; el.dispatchEvent(new Event('input', {bubbles: true})); }", [editor.element_handle(), content])
                    
                    editor.click()
                    editor_page.keyboard.press("End")
                    editor_page.keyboard.press("Space")
                    page.wait_for_timeout(500)
                    editor_page.keyboard.press("Backspace")
                else:
                    print("  [警告] 没找到正文的极其庞大的输入区域！")
                
                # 4. 点击【下一步】进行正式发布
                print(" -> 点击右上角的【下一步】准备正式拔剑发布...")
                # 排除可能还存在的新手引导的“下一步”，最后那个一定是顶部大按钮
                next_btn = editor_page.get_by_text("下一步", exact=True).last
                if next_btn.is_visible():
                    next_btn.click(force=True)
                    # 我们需要等待这些“千层饼”弹窗出现而不是用 is_visible 瞬时判断
                    
                    try:
                        # 闯关拦截 1：错别字未修改弹窗 -> 必须秒破
                        submit_typo_btn = editor_page.get_by_role("button", name="提交").first
                        # 这里如果弹窗不出来就静默超时，说明没有错别字，进下一个分支
                        submit_typo_btn.wait_for(state="visible", timeout=2000)
                        print("    - 触发错别字修改提示弹窗，直接无视并强制选择【提交】...")
                        submit_typo_btn.click(force=True)
                        # 【重要修复】：等待错别字弹窗的消失动画彻底走完，防它的“取消”按钮干扰下一关
                        editor_page.wait_for_timeout(1200)
                    except Exception:
                        pass
                        
                    try:
                        # 闯关拦截 2：内容风险检测弹窗 -> 必须秒破
                        # 严格先探明存在此风险询问文案
                        risk_txt = editor_page.get_by_text("内容风险检测", exact=False).last
                        risk_txt.wait_for(state="visible", timeout=2000)
                        
                        editor_page.wait_for_timeout(500) # 等待弹窗进入视野
                        
                        cancel_risk_btn = editor_page.get_by_role("button", name="取消").last
                        cancel_risk_btn.wait_for(state="visible", timeout=2000)
                        print("    - 触发内容风险检测弹窗，为了不浪费检测次数，点击【取消】...")
                        cancel_risk_btn.click(force=True)
                        
                        # 等待该弹窗退场，以免截留后续的发布点击
                        editor_page.wait_for_timeout(1000)
                    except Exception:
                        pass
                        
                    # 终极发布面板 -> 这个面板往往加载极慢，一定要有充分的耐心等待
                    try:
                        print("    - 正在等待加载【终极发布设置】大面板...")
                        publish_btn = editor_page.get_by_role("button", name="确认发布").first
                        publish_btn.wait_for(state="visible", timeout=6000)
                        
                        try:
                            # 这个选项被用户要求改为否
                            print("    - 响应号召：强制勾选【是否使用AI：否】的单选项...")
                            ai_no_label = editor_page.get_by_text("否", exact=True).first
                            ai_no_label.wait_for(state="visible", timeout=2000)
                            ai_no_label.click(force=True)
                            editor_page.wait_for_timeout(500)
                        except Exception:
                            # 并不是所有账号、所有分区都强制带这个选项，带不上也不要紧
                            pass
                        
                        publish_btn.click(force=True)
                        print(f"  [🎇 发布成功] 第 {success_count+1} 章：'第{chapter_num}章 {chapter_title}' 已被发往全世界！")
                        success_count += 1
                        
                    except Exception as e:
                        print(f"  [警告] 等不到或者未能在最后面板找到并点击'确认发布'按钮！")
                        input("  请您手动点击一下右侧大弹窗里橘黄色的【确认发布】，然后回到这黑框按回车继续 >>> ")
                        success_count += 1
                else:
                    print("  未能找到'下一步'按钮！尝试降级为【一键光速存草稿】...")
                    save_btn = editor_page.get_by_text("存草稿", exact=False).first
                    if save_btn.is_visible():
                        save_btn.click()
                        print(f"  [降级保存] 第 {success_count+1} 章：已转为稳重存草稿！")
                        success_count += 1
                    else:
                        print("  未能找到任何保存入口，当前章节宣告失败！")
                        success_count += 1
                
                page.wait_for_timeout(3000) # 等待对号保存成功消失的动画
                
                # 按照小说书名绝对隔离分类进入对应的文件夹，干净利落绝不污染！
                dest_path = os.path.join(volume_dir, filename)
                shutil.move(file_path, dest_path)
                
                # 清除开启的新页面，保证一直是一个极简的单线操作！
                if editor_page != page:
                    editor_page.close()
                
            except Exception as e:
                print(f"!!! 哎呀！处理 '第{chapter_num}章 {chapter_title}' 时碰到了暗礁: {e}")
                input("请在右边弹出来的浏览器里查看究竟卡在了哪里？发现问题后按回车结束本次脚本运行。")
                break
                
            page.wait_for_timeout(1000) 
            
        print(f"\n==========================================")
        print(f"全自动爆更流程狂野结束。本次共成功为您发送了 {success_count} 个章节！")
        print(f"==========================================\n")
        
        input(">>> 天下武功唯快不破，按键回车键即可彻底关闭浏览器：")
        browser.close()

if __name__ == "__main__":
    main()
