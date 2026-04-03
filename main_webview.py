import os
import glob
import time
import shutil
import re
import threading
import sys
import json
import webview
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"
CONFIG_FILE = "config.json"
BOOK_MANAGE_URL = "https://fanqienovel.com/main/writer/book-manage"

class Api:
    def __init__(self):
        self.window = None
        self.config = self.load_config()

    def set_window(self, window):
        self.window = window

    def load_config(self):
        default_config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception: pass
        return default_config

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def get_config(self):
        return self.config

    def choose_dir(self, key='archive_dir'):
        if not self.window: return None
        dialog_type = getattr(webview, 'FileDialog', None)
        open_flag = dialog_type.FOLDER if dialog_type else webview.FOLDER_DIALOG
        try:
            result = self.window.create_file_dialog(open_flag)
            if isinstance(result, tuple) or isinstance(result, list):
                if result and result[0]:
                    self.config[key] = result[0]
                    self.save_config()
                    return result[0]
        except Exception as e:
            self.log(f"选择目录出错: {e}", "text-red-400")
        return None

    def log(self, msg, color="text-gray-300"):
        if self.window:
            safe_msg = msg.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            # Run evaluate_js in the UI thread context avoiding blocking
            try:
                self.window.evaluate_js(f'window.appendLog("{safe_msg}", "{color}");')
            except Exception as e:
                print("GUI Eval Error:", e)

    def _update_progress(self, current, total):
        if self.window:
            try:
                self.window.evaluate_js(f"window.updateProgress({current}, {total});")
            except Exception:
                pass

    def check_login_state(self):
        """Check if login state file exists"""
        return os.path.exists(STATE_FILE)

    def get_books(self):
        """Scan source_dir for books and txt files"""
        books = []
        source_dir = self.config.get('source_dir')
        if not source_dir or not os.path.isdir(source_dir):
            return books
        for name in sorted(os.listdir(source_dir)):
            sub_path = os.path.join(source_dir, name)
            if os.path.isdir(sub_path):
                txts = glob.glob(os.path.join(sub_path, "*.txt"))
                if txts:
                    books.append({
                        "name": name,
                        "count": len(txts),
                        "published_volumes": self._get_published_volume_count(name)
                    })
        return books

    def _get_published_volume_count(self, book_name):
        """Count published volume folders for one book in archive_dir."""
        if not book_name:
            return 0

        archive_dir = self.config.get('archive_dir')
        if not archive_dir or not os.path.isdir(archive_dir):
            return 0

        book_archive_path = os.path.join(archive_dir, book_name)
        if not os.path.isdir(book_archive_path):
            return 0

        try:
            child_dirs = []
            txt_files = 0
            for child in os.listdir(book_archive_path):
                child_path = os.path.join(book_archive_path, child)
                if os.path.isdir(child_path):
                    child_dirs.append(child)
                elif os.path.isfile(child_path) and child.lower().endswith(".txt"):
                    txt_files += 1

            # If no explicit volume folder exists but txt files are archived directly,
            # treat it as one effective volume to avoid showing 0 misleadingly.
            if not child_dirs and txt_files > 0:
                return 1

            return len(child_dirs)
        except Exception:
            return 0

    def do_login(self):
        """Login flow with Playwright, runs in background thread to prevent GUI lock"""
        def _login_thread():
            self.log(">>> 收到启动指令，正在呼叫大魔王浏览器...", "text-indigo-400 font-bold")
            try:
                with sync_playwright() as p:
                    try:
                        # 尝试优先调用系统自带的 Edge 浏览器，解决 PyInstaller 打包后由于路径不对找不到浏览器内核的问题
                        browser = p.chromium.launch(channel="msedge", headless=False)
                    except Exception:
                        try:
                            # 备用方案：调用系统安装的 Chrome
                            browser = p.chromium.launch(channel="chrome", headless=False)
                        except Exception:
                            # 终极兜底方案
                            browser = p.chromium.launch(headless=False)
                    if os.path.exists(STATE_FILE):
                        self.log("发现已有登录凭证，尝试加载...")
                        context = browser.new_context(storage_state=STATE_FILE)
                    else:
                        context = browser.new_context()
                        
                    page = context.new_page()
                    self.log("正在强行进入番茄工作台...")
                    try:
                        page.goto("https://fanqienovel.com/main/writer/?enter_from=author_zone", timeout=60000)
                    except Exception as e:
                        pass
                        
                    self.log("【动作需求】请在弹出的浏览器中扫码或输入密码登录！", "text-yellow-400 font-bold")
                    
                    # 阻塞直到用户在弹窗点击确定 (调用前端 js await 函数不需要我们管，由于是后台线程直接等待 js 执行完毕不好弄，用 python 原生锁或者继续依赖前端触发即可)
                    # wait, in eel/webview, evaluate_js does not return a blocking JS promise result natively unless we use call/callbacks.
                    # Instead, we just show dialog to the user via PyWebView dialog
                    result = self.window.create_confirmation_dialog('登录确认', '请在浏览器弹出窗口中完成登录操作。\n确认您已经看到作家后台主界面后，点击【确定】以保存状态！\n点击【取消】则放弃保存。')
                    
                    if result:
                        context.storage_state(path=STATE_FILE)
                        self.log(f"✅ 登录凭证已签发，写入成功！", "text-green-400 font-bold")
                    else:
                        self.log("❌ 登录流程已中止，凭证未保存。", "text-red-400")
                        
                    browser.close()
            except Exception as e:
                self.log(f"登录流程崩溃: {e}", "text-red-500")

        # start in thread
        th = threading.Thread(target=_login_thread, daemon=True)
        th.start()
        # Python api call blocks until returned!
        # If we block here, JS `await do_login()` waits until login finishes.
        th.join() 
        return True


    def open_source_folder(self):
        """Open the source drafts folder in Windows File Explorer"""
        try:
            target_dir = self.config.get('source_dir')
            if not target_dir:
                self.log("没有配置待发草稿目录！", "text-red-400")
                return
            os.makedirs(target_dir, exist_ok=True)
            os.startfile(target_dir)
            self.log(f"已为您打开本地草稿来源目录：{target_dir}", "text-green-300")
        except Exception as e:
            self.log(f"打开源码目录失败: {e}", "text-red-500")

    def open_data_folder(self):
        """Open the uploaded records folder in Windows File Explorer"""
        try:
            target_dir = self.config.get('archive_dir')
            if not target_dir:
                self.log("没有配置归档目录！", "text-red-400")
                return
            os.makedirs(target_dir, exist_ok=True)
            os.startfile(target_dir)
            self.log(f"已为您打开本地归档文件目录：{target_dir}", "text-blue-300")
        except Exception as e:
            self.log(f"打开目录失败: {e}", "text-red-500")


    def start_publish(self, book_name_filter, publish_count, volume_num):
        """Start publish process in thread, wait to finish"""
        def _publish_thread():
            self.log(f"\n==================================================", "text-indigo-400")
            self.log(f"🚀 发动终极禁咒【全自动爆更】目标：{book_name_filter}", "text-pink-400 font-bold")
            
            source_dir = self.config.get('source_dir')
            if not source_dir:
                self.log("【严重拦截】未设置待发存档位置！发文进程被强制中止。", "text-red-500 font-bold")
                return False

            # Fetch txt files
            sub_path = os.path.join(source_dir, book_name_filter)
            txts = sorted(glob.glob(os.path.join(sub_path, "*.txt")))
            if publish_count is not None and publish_count > 0:
                txts = txts[:publish_count]
                
            self.log(f"本次爆更总发射目标数：{len(txts)} 章", "text-gray-300 font-bold")
            
            # Volume name
            volume_name = None
            if volume_num is not None and volume_num > 0:
                cn_digits = "一二三四五六七八九十"
                volume_name = f"第{cn_digits[volume_num - 1] if volume_num <= 10 else str(volume_num)}卷"
                self.log(f"归档卷锚定于：【{volume_name}】", "text-blue-300")
                
            self.log(f"==================================================\n", "text-indigo-400")
            
            base_archive_dir = self.config.get('archive_dir')
            if not base_archive_dir:
                self.log("【严重拦截】未设置发文归档位置！发文进程被强制中止。", "text-red-500 font-bold")
                return False
                
            current_uploaded_dir = os.path.join(base_archive_dir, book_name_filter)
            if volume_name:
                volume_dir = os.path.join(current_uploaded_dir, volume_name)
            else:
                volume_dir = current_uploaded_dir
            os.makedirs(volume_dir, exist_ok=True)
            
            try:
                with sync_playwright() as p:
                    try:
                        # 尝试优先调用系统自带的 Edge 浏览器，解决 PyInstaller 打包后由于路径不对找不到浏览器内核的问题
                        browser = p.chromium.launch(channel="msedge", headless=False)
                    except Exception:
                        try:
                            # 备用方案：调用系统安装的 Chrome
                            browser = p.chromium.launch(channel="chrome", headless=False)
                        except Exception:
                            # 终极兜底方案
                            browser = p.chromium.launch(headless=False)
                    context = browser.new_context(storage_state=STATE_FILE)
                    page = context.new_page()
                    
                    success_count = 0
                    total_target = len(txts)
                    self._update_progress(success_count, total_target)
                    
                    for i, file_path in enumerate(txts):
                        filename = os.path.basename(file_path)
                        raw_title = os.path.splitext(filename)[0]
                        m = re.search(r'第(\d+)章[\s_]*(.*)', raw_title)
                        chapter_num = str(m.group(1)) if m else ""
                        chapter_title = m.group(2).strip() if m else ""
                        
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            
                        if not chapter_title and lines:
                            m2 = re.search(r'第.*?章[\s：:]*(.*)', lines[0].strip())
                            if m2:
                                chapter_title = m2.group(1).strip()
                        if not chapter_title:
                            chapter_title = re.sub(r'^[0-9]+[\s_]*', '', raw_title).strip()
                            
                        self.log(f"\n[{i+1}/{len(txts)}] 正在上膛: '第{chapter_num}章 {chapter_title}'", "text-yellow-200")
                        
                        if lines and re.search(r'第.*?章', lines[0].strip()):
                            lines = lines[1:]
                        while lines and not lines[0].strip():
                            lines = lines[1:]
                        content = "".join(lines)
                        
                        try:
                            self.log(" -> 跳跃回空间站【我的小说】总览...")
                            page.goto(BOOK_MANAGE_URL, timeout=60000)
                            page.wait_for_timeout(3000)
                            
                            manage_clicked = False
                            # Hover Strategy
                            book_cards = page.locator('div, li, section, article').filter(has_text=book_name_filter)
                            for i in range(book_cards.count() - 1, -1, -1):
                                card = book_cards.nth(i)
                                try:
                                    if card.is_visible():
                                        card.hover(timeout=3000)
                                        page.wait_for_timeout(1000)
                                        manage_btn = card.get_by_text("章节管理").first
                                        if manage_btn.is_visible():
                                            manage_btn.click()
                                            manage_clicked = True
                                            break
                                except: pass
                                
                            # Global Strategy
                            if not manage_clicked:
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
                                    except: pass
                            
                            # Fallback Strategy
                            if not manage_clicked:
                                page.get_by_text("章节管理").first.click()
                                
                            page.wait_for_timeout(4000)
                            
                            # 关闭番茄平台新增的"注意平台不允许发布以下内容"提示弹窗
                            # 该弹窗可能在章节管理页面加载时弹出，需要先关闭才能继续操作
                            try:
                                current_active_page = context.pages[-1] if len(context.pages) > 1 else page
                                for dismiss_text in ["我知道了", "知道了", "关闭"]:
                                    dismiss_btn = current_active_page.get_by_text(dismiss_text, exact=True).first
                                    try:
                                        dismiss_btn.wait_for(state="visible", timeout=2000)
                                        if dismiss_btn.is_visible():
                                            dismiss_btn.click(force=True)
                                            self.log(" -> 已自动关闭平台内容提示弹窗", "text-gray-400")
                                            current_active_page.wait_for_timeout(1000)
                                            break
                                    except:
                                        pass
                            except:
                                pass
                            
                            original_pages = len(context.pages)
                            editor_page = context.pages[-1] if original_pages > 1 and context.pages[-1] != page else page
                            
                            # Draft check
                            draft_row = editor_page.locator('tr, li, .chapter-item').filter(has_text=re.compile(f"第\\s*{chapter_num}\\s*章")).first
                            if draft_row.is_visible():
                                self.log(" -> 检测到历史残骸(草稿)，执行编辑接管协议...")
                                edit_icon = draft_row.locator('td').last.locator('svg, i, a, span, button, img').first
                                if edit_icon.is_visible():
                                    edit_icon.click(force=True)
                                else:
                                    draft_row.click(force=True)
                            else:
                                self.log(" -> 未发现残骸，发射崭新的一章...")
                                new_btn = editor_page.get_by_role("button", name="新建章节").first
                                if not new_btn.is_visible():
                                    new_btn = editor_page.get_by_text("新建章节").first
                                new_btn.click(force=True)
                                
                            page.wait_for_timeout(4000)
                            if len(context.pages) > original_pages:
                                editor_page = context.pages[-1]
                                
                            # Clear guides
                            for _ in range(3):
                                editor_page.keyboard.press("Escape")
                                editor_page.wait_for_timeout(200)
                                
                            for _ in range(10):
                                clicked_guide = False
                                try:
                                    for target_text in ["下一步", "完成", "我知道了", "跳过"]:
                                        btns = editor_page.get_by_text(target_text, exact=True).element_handles()
                                        for btn in btns:
                                            box = btn.bounding_box()
                                            if box and box['y'] > 100:
                                                btn.click()
                                                editor_page.wait_for_timeout(600)
                                                clicked_guide = True
                                except: pass
                                if not clicked_guide: break
                                
                            # Volume selection
                            if volume_num is not None and volume_num > 1:
                                self.log(f" -> 执行分卷跳跃，目标坐标：【{volume_name}】...")
                                try:
                                    vol_elements = editor_page.get_by_text(re.compile(r'第[一二三四五六七八九十百]+卷')).element_handles()
                                    dialog_opened = False
                                    for v in vol_elements[:8]:
                                        try:
                                            box = v.bounding_box()
                                            if not box or box['y'] < 0 or box['y'] > 800: continue
                                            outer_html = v.evaluate("el => el.outerHTML") or ""
                                            if "outline" in outer_html.lower() or "placeholder" in outer_html.lower() or "卷名" in outer_html: continue
                                            v.click(force=True)
                                            editor_page.wait_for_timeout(1000)
                                            if editor_page.get_by_text("新建分卷").is_visible() or editor_page.get_by_text("取消").is_visible():
                                                dialog_opened = True
                                                break
                                        except: pass
                                    
                                    if dialog_opened:
                                        editor_page.wait_for_timeout(500)
                                        target_vol = None
                                        for v_name_cand in [volume_name, f"第{volume_num}卷", f"卷{volume_num}"]:
                                            candidates = editor_page.get_by_text(v_name_cand, exact=False).element_handles()
                                            for cand in candidates:
                                                try:
                                                    cand_box = cand.bounding_box()
                                                    cand_html = cand.evaluate("el => el.outerHTML") or ""
                                                    if "outline" in cand_html.lower() or "placeholder" in cand_html.lower() or "卷名" in cand_html: continue
                                                    if not cand_box or cand_box['y'] < 0 or cand_box['y'] > 800: continue
                                                    target_vol = cand
                                                    break
                                                except: pass
                                            if target_vol: break
                                                
                                        if target_vol:
                                            target_vol.click(force=True)
                                            editor_page.wait_for_timeout(500)
                                            confirm_btn = editor_page.get_by_role("button", name="确定").first
                                            if not confirm_btn.is_visible():
                                                confirm_btn = editor_page.get_by_text("确定", exact=True).last
                                            if confirm_btn.is_visible():
                                                confirm_btn.click(force=True)
                                            else:
                                                editor_page.keyboard.press("Escape")
                                            editor_page.wait_for_timeout(1000)
                                        else:
                                            self.log(f"  [⚠️系统警报] 全局检索不到【{volume_name}】，需人工干预操作。", "text-red-400 font-bold")
                                            # Using window confirm dialog
                                            result = self.window.create_confirmation_dialog('需要人工辅助', f'请在浏览器中手动选中目标分卷【{volume_name}】，并点击确定！\n\n点击【确定】继续脚本运行；点击【取消】直接跳过该章节。')
                                            if not result:
                                                continue # skip this chapter
                                except: pass
                                    
                            # Input
                            self.log(" -> 开始全功率注入正文核心代码...")
                            num_input = editor_page.locator('input[type="text"]').first
                            if num_input.is_visible(): num_input.fill(chapter_num, force=True)
                                
                            title_input = editor_page.get_by_placeholder("请输入标题", exact=False).first
                            if not title_input.is_visible(): title_input = editor_page.get_by_placeholder("请输入章节名", exact=False).first
                            if not title_input.is_visible(): title_input = editor_page.locator('input[type="text"]').last
                            if title_input.is_visible(): title_input.fill(chapter_title, force=True)
                                
                            # Body
                            editor = editor_page.locator('.ql-editor').first
                            if not editor.is_visible(): editor = editor_page.locator('.ProseMirror').first
                            if not editor.is_visible(): editor = editor_page.locator('[contenteditable="true"]').first
                                
                            if editor.is_visible():
                                editor.click(force=True)
                                editor_page.keyboard.press("Control+A")
                                editor_page.keyboard.press("Backspace")
                                editor_page.evaluate("([el, text]) => { el.innerText = text; el.dispatchEvent(new Event('input', {bubbles: true})); }", [editor.element_handle(), content])
                                editor.click()
                                editor_page.keyboard.press("End")
                                editor_page.keyboard.press("Space")
                                page.wait_for_timeout(500)
                                editor_page.keyboard.press("Backspace")
                            else:
                                self.log("  [错误] 检测不到输入核心区域！", "text-red-500")
                                
                            # Publish
                            self.log(" -> 发射程序部署完毕，开始点击极光确认按钮...")
                            next_btn = editor_page.get_by_text("下一步", exact=True).last
                            if next_btn.is_visible():
                                next_btn.click(force=True)
                                
                                try:
                                    # 处理因错别字未修改等弹出的“发布提示”弹窗，点击“提交”
                                    submit_btn_candidates = [
                                        editor_page.get_by_role("button", name="提交"),
                                        editor_page.get_by_text("提交", exact=True)
                                    ]
                                    for cand in submit_btn_candidates:
                                        try:
                                            btn = cand.last
                                            btn.wait_for(state="visible", timeout=1500)
                                            if btn.is_visible():
                                                btn.click(force=True)
                                                self.log(" -> 已自动跳过错别字等提示，点击了【提交】", "text-gray-400")
                                                editor_page.wait_for_timeout(1200)
                                                break
                                        except: pass
                                except: pass
                                    
                                try:
                                    risk_txt = editor_page.get_by_text("内容风险检测", exact=False).last
                                    risk_txt.wait_for(state="visible", timeout=2000)
                                    editor_page.wait_for_timeout(500)
                                    cancel_risk_btn = editor_page.get_by_role("button", name="取消").last
                                    cancel_risk_btn.wait_for(state="visible", timeout=2000)
                                    cancel_risk_btn.click(force=True)
                                    editor_page.wait_for_timeout(1000)
                                except: pass
                                    
                                try:
                                    publish_btn = editor_page.get_by_role("button", name="确认发布").first
                                    publish_btn.wait_for(state="visible", timeout=6000)
                                    
                                    try:
                                        ai_no_label = editor_page.get_by_text("否", exact=True).first
                                        ai_no_label.wait_for(state="visible", timeout=2000)
                                        ai_no_label.click(force=True)
                                        editor_page.wait_for_timeout(500)
                                    except: pass
                                    
                                    publish_btn.click(force=True)
                                    self.log(f"  [🎇 完美收官] '第{chapter_num}章 {chapter_title}' 已被发送往星辰大海！", "text-green-400 font-bold")
                                    success_count += 1
                                    self._update_progress(success_count, total_target)
                                    
                                except Exception as e:
                                    self.log(f"  [系统宕机] 找不到确认发布极光按钮！请求干预！", "text-red-500 font-bold")
                                    result = self.window.create_confirmation_dialog('需要人工辅助', f'未匹配到最后一步的“确认发布”！\n\n请在浏览器中手动点击确认发布完毕后，点击【确定】继续。')
                                    if result:
                                        success_count += 1
                                        self._update_progress(success_count, total_target)
                            else:
                                self.log("  [降级协议] 未能找到'下一步'，触发后备计划：转化为静态草稿...", "text-yellow-600")
                                save_btn = editor_page.get_by_text("存草稿", exact=False).first
                                if save_btn.is_visible():
                                    save_btn.click()
                                    self.log(f"  [草稿休眠] 第{chapter_num}章已转入冷冻休眠模式！", "text-blue-300")
                                    success_count += 1
                                    self._update_progress(success_count, total_target)
                                else:
                                    self.log("  极度异常：未找到任何保存入口，章程处理失败！", "text-red-600")
                                    
                            page.wait_for_timeout(3000)
                            
                            dest_path = os.path.join(volume_dir, filename)
                            shutil.move(file_path, dest_path)
                            
                            if editor_page != page:
                                editor_page.close()
                                
                        except Exception as e:
                            self.log(f"!!! 处理 '第{chapter_num}章' 时发生毁灭性崩溃: {e}", "text-red-600 font-bold")
                            result = self.window.create_confirmation_dialog('剧烈异常', f'发生代码级中断: {e}\n是否继续发射下一章？')
                            if not result:
                                break
                            
                        page.wait_for_timeout(1000)
                        
                    self.log(f"\n==========================================", "text-indigo-400 font-bold")
                    self.log(f"✨ 爆更狂潮落幕！本次共计释放了 {success_count} 颗核弹章！", "text-green-400 font-bold text-lg")
                    self.log(f"==========================================\n", "text-indigo-400 font-bold")
                    browser.close()
            except Exception as e:
                self.log(f"执行主控程序彻底崩溃：{e}", "text-red-700 bg-red-100 p-2 rounded")

        # run in thread
        th = threading.Thread(target=_publish_thread, daemon=True)
        th.start()
        th.join() # blocks JS await until finished
        return True

if __name__ == '__main__':
    api = Api()
    
    # Path setup for PyInstaller compatibility
    if getattr(sys, 'frozen', False):
        current_dir = sys._MEIPASS
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
    html_path = 'file://' + os.path.join(current_dir, 'web', 'index.html').replace('\\', '/')
    
    window = webview.create_window(
        '番茄发文助手 PRO', 
        html_path, 
        js_api=api,
        width=1100, 
        height=770,
        min_size=(700, 500),
        frameless=False,      # Can be True for completely custom window bar
        text_select=True
    )
    api.set_window(window)
    # Start app
    webview.start()
