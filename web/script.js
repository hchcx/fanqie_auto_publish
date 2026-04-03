// Elements
const el = {
    btnOpenSource: document.getElementById('btn-open-source'),
    btnOpenData: document.getElementById('btn-open-data'),
    btnLogin: document.getElementById('btn-login'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnStart: document.getElementById('btn-start'),
    btnClear: document.getElementById('btn-clear'),
    btnExample: document.getElementById('btn-example'),
    btnChooseDir: document.getElementById('btn-choose-dir'),
    archiveDirInput: document.getElementById('archive-dir-input'),
    btnChooseSourceDir: document.getElementById('btn-choose-source-dir'),
    sourceDirInput: document.getElementById('source-dir-input'),
    bookSelect: document.getElementById('book-select'),
    bookStatus: document.getElementById('book-status'),
    publishedVolumeStatus: document.getElementById('published-volume-status'),
    publishCount: document.getElementById('publish-count'),
    volumeNum: document.getElementById('volume-num'),
    logContainer: document.getElementById('log-container'),
    statusBadge: document.getElementById('status-badge'),
    
    progressWrapper: document.getElementById('progress-wrapper'),
    progressBar: document.getElementById('progress-bar'),
    progressText: document.getElementById('progress-text'),

    modalBackdrop: document.getElementById('modal-backdrop'),
    modalBox: document.getElementById('modal-box'),
    modalTitle: document.getElementById('modal-title'),
    modalMsg: document.getElementById('modal-msg'),
    modalBtnOk: document.getElementById('modal-btn-ok'),
    modalBtnCancel: document.getElementById('modal-btn-cancel')
};

let currentBooks = [];
let isPublishing = false;

window.addEventListener('pywebviewready', async function() {
    appendLog(">>> UI 框架加载成功，已连接 Python 内核 🚀", "text-accent-400 font-bold");
    
    const config = await window.pywebview.api.get_config();
    if (config && config.archive_dir) {
        el.archiveDirInput.value = config.archive_dir;
        el.archiveDirInput.classList.remove('text-slate-600', 'placeholder-slate-400');
        el.archiveDirInput.classList.add('text-accent-600');
    }
    if (config && config.source_dir) {
        el.sourceDirInput.value = config.source_dir;
        el.sourceDirInput.classList.remove('text-slate-600', 'placeholder-slate-400');
        el.sourceDirInput.classList.add('text-accent-600');
    }
    
    refreshBooks();
    checkState();
});

window.appendLog = function(msg, colorClass = "text-[#94a3b8]") {
    const div = document.createElement('div');
    div.className = `fade-in break-words ${colorClass}`;
    div.textContent = msg;
    el.logContainer.appendChild(div);
    el.logContainer.scrollTop = el.logContainer.scrollHeight;
};

window.updateProgress = function(current, total) {
    if (total <= 0) return;
    const percent = Math.min(100, Math.round((current / total) * 100));
    el.progressWrapper.classList.remove('hidden');
    el.progressText.classList.remove('hidden');
    el.progressBar.style.width = percent + '%';
    el.progressText.textContent = `${current} / ${total}`;
};

window.showModal = function(title, message, isError = false, showCancel = true) {
    return new Promise((resolve) => {
        el.modalTitle.innerHTML = isError 
            ? `<div class="w-7 h-7 rounded-full bg-rose-100 text-rose-500 flex items-center justify-center text-sm"><i class="fa-solid fa-triangle-exclamation"></i></div> ${title}`
            : `<div class="w-7 h-7 rounded-full bg-accent-100 text-accent-500 flex items-center justify-center text-sm"><i class="fa-solid fa-circle-question"></i></div> ${title}`;
        
        el.modalMsg.textContent = message;
        
        if (!showCancel) {
            el.modalBtnCancel.style.display = 'none';
        } else {
            el.modalBtnCancel.style.display = 'block';
        }

        el.modalBackdrop.classList.remove('opacity-0', 'pointer-events-none');
        el.modalBox.classList.remove('scale-95');
        el.modalBox.classList.add('scale-100');

        const cleanup = () => {
            el.modalBtnOk.onclick = null;
            el.modalBtnCancel.onclick = null;
            el.modalBackdrop.classList.add('opacity-0', 'pointer-events-none');
            el.modalBox.classList.remove('scale-100');
            el.modalBox.classList.add('scale-95');
        };

        el.modalBtnOk.onclick = () => { cleanup(); resolve(true); };
        el.modalBtnCancel.onclick = () => { cleanup(); resolve(false); };
    });
};

function toggleUI(disabled) {
    isPublishing = disabled;
    el.btnStart.disabled = disabled;
    el.btnLogin.disabled = disabled;
    el.btnOpenSource.disabled = disabled;
    el.btnOpenData.disabled = disabled;
    el.btnRefresh.disabled = disabled;
    el.btnChooseDir.disabled = disabled;
    el.btnChooseSourceDir.disabled = disabled;
    el.bookSelect.disabled = disabled;
    el.publishCount.disabled = disabled;
    el.volumeNum.disabled = disabled;
    
    // Also disable custom select
    const _customTrigger = document.getElementById('custom-select-trigger');
    if(_customTrigger) _customTrigger.disabled = disabled;

    if (disabled) {
        el.btnStart.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> 正在后台疯狂爆更...`;
        el.btnStart.classList.add('opacity-50', 'cursor-not-allowed', 'shadow-none');
        el.statusBadge.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse shadow-[0_0_3px_currentColor]"></div> 运行中`;
        el.statusBadge.className = "px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-widest bg-amber-50 text-amber-600 border border-amber-200 flex items-center gap-2 shadow-sm mr-2";
    } else {
        el.btnStart.innerHTML = `<i class="fa-solid fa-rocket"></i> 启动全自动发文`;
        el.btnStart.classList.remove('opacity-50', 'cursor-not-allowed', 'shadow-none');
        el.progressWrapper.classList.add('hidden');
        el.progressText.classList.add('hidden');
        el.progressBar.style.width = '0%';
        checkState();
    }
}

async function checkState() {
    if(!window.pywebview) return;
    const ok = await window.pywebview.api.check_login_state();
    if (ok) {
        el.statusBadge.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_3px_currentColor]"></div> 就绪`;
        el.statusBadge.className = "px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-widest bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center gap-2 shadow-sm mr-2";
    } else {
        el.statusBadge.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse shadow-[0_0_3px_currentColor]"></div> 未登录`;
        el.statusBadge.className = "px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-widest bg-rose-50 text-rose-600 border border-rose-200 flex items-center gap-2 shadow-sm mr-2";
    }
}

async function refreshBooks() {
    const customText = document.getElementById('custom-select-text');
    const customDropdown = document.getElementById('custom-select-dropdown');
    
    el.bookSelect.innerHTML = '<option value="">扫描中...</option>';
    if(customText) customText.textContent = '快速扫描读取中...';
    if(customDropdown) customDropdown.innerHTML = '';
    
    const icon = document.getElementById('refresh-icon');
    if (icon) icon.classList.add('animate-spin');
    
    try {
        currentBooks = await window.pywebview.api.get_books();
        
        el.bookSelect.innerHTML = '';
        
        if (currentBooks.length === 0) {
            el.bookSelect.innerHTML = '<option value="">chapters目录下暂无小说</option>';
            el.bookStatus.textContent = '请使用【排版规范】按钮查看如何写入草稿';
            if (el.publishedVolumeStatus) {
                el.publishedVolumeStatus.textContent = '已发布卷数：0 卷';
            }
            if(customText) customText.textContent = '当前目录下未建立草稿';
        } else {
            currentBooks.forEach((b, i) => {
                const textStr = `${b.name} (${b.count}章未发)`;
                
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = textStr;
                el.bookSelect.appendChild(opt);
                
                if(customDropdown) {
                    const div = document.createElement('div');
                    div.className = 'px-4 py-3 mx-1 my-0.5 text-[13px] font-bold text-slate-600 hover:bg-accent-50 hover:text-accent-600 rounded-lg cursor-pointer transition-colors flex items-center gap-2.5';
                    div.innerHTML = `<i class="fa-solid fa-book-journal-whills text-accent-400"></i> <span class="truncate">${textStr}</span>`;
                    div.onclick = (e) => {
                        e.stopPropagation();
                        el.bookSelect.value = i;
                        customText.textContent = textStr;
                        customDropdown.classList.add('opacity-0');
                        setTimeout(() => customDropdown.classList.add('hidden'), 200);
                        document.getElementById('custom-select-arrow').classList.remove('rotate-180');
                        updateBookStatus();
                    };
                    customDropdown.appendChild(div);
                }
            });
            
            if (currentBooks.length > 0) {
                el.bookSelect.value = "0";
                if(customText) customText.textContent = `${currentBooks[0].name} (${currentBooks[0].count}章未发)`;
            }
            updateBookStatus();
        }
    } catch (e) {
        console.error(e);
        appendLog(`[GUI错误] 刷新小说列表失败: ${e}`, "text-rose-500");
    } finally {
        setTimeout(() => {
            const icon = document.getElementById('refresh-icon');
            if (icon) icon.classList.remove('animate-spin');
        }, 500);
    }
}

function updateBookStatus() {
    const idx = window.parseInt(el.bookSelect.value);
    if (!isNaN(idx) && currentBooks[idx]) {
        const book = currentBooks[idx];
        const publishedVolumes = Number.isFinite(book.published_volumes)
            ? Math.max(0, book.published_volumes)
            : 0;
        el.bookStatus.textContent = `共发现 ${book.count} 个有效的 TXT 章节`;
        if (el.publishedVolumeStatus) {
            el.publishedVolumeStatus.textContent = `已发布卷数：${publishedVolumes} 卷`;
        }
    } else if (el.publishedVolumeStatus) {
        el.publishedVolumeStatus.textContent = '已发布卷数：0 卷';
    }
}

el.bookSelect.addEventListener('change', updateBookStatus);
el.btnRefresh.addEventListener('click', refreshBooks);

el.btnClear.addEventListener('click', () => {
    el.logContainer.innerHTML = '<div class="text-[#64748b] fade-in font-semibold">> 运行日志已被清空。</div>';
});

el.btnExample.addEventListener('click', () => {
    const text = `⚠️ 重要：TXT文件的第一行必须包含“第某章”和“本章标题”！
否则自动化脚本无法识别标题并会卡住运行。

【正确的排版示例如下】：

第71章 断臂

距离秦北望在归名碑前站了一整夜，又过去了三天。

北京，陆军总医院特勤病区。这里是国内最顶级的军事医疗中心，地下三层有一个不在任何公开楼层指引上的封闭病房区。

这里只收治两类病人：一，在最高级别军事任务中受伤且伤情涉密的人员；二，镇九司的人。

他盯着天花板。
其他内容。。。。。。。。。。。。。`;
    
    showModal('TXT 文本排版规范示例', text, false, false);
});

el.btnLogin.addEventListener('click', async () => {
    toggleUI(true);
    el.btnStart.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 等待登录完成...`;
    
    try {
        await window.pywebview.api.do_login();
    } finally {
        toggleUI(false);
    }
});

el.btnOpenSource.addEventListener('click', async () => {
    if (isPublishing) return;
    if (!el.sourceDirInput.value) {
        showModal('核心路径校验提示', '尚未设置发文前的数据源目录！\n请先点击上方的“更改”选择含有TXT章节集的文件夹。', true, false);
        return;
    }
    await window.pywebview.api.open_source_folder();
});

el.btnOpenData.addEventListener('click', async () => {
    if (isPublishing) return;
    if (!el.archiveDirInput.value) {
        showModal('核心路径校验提示', '尚未设置发文成功后的数据归档转移目录！\n请先点击上方的“更改”配置目标位置。', true, false);
        return;
    }
    await window.pywebview.api.open_data_folder();
});

el.btnChooseDir.addEventListener('click', async () => {
    if (isPublishing) return;
    const dir = await window.pywebview.api.choose_dir('archive_dir');
    if (dir) {
        el.archiveDirInput.value = dir;
        el.archiveDirInput.classList.remove('text-slate-600', 'placeholder-slate-400');
        el.archiveDirInput.classList.add('text-accent-600');
        appendLog(`[SYSTEM] 归档保存点挂载成功: ${dir}`, "text-emerald-400");
    }
});

el.btnChooseSourceDir.addEventListener('click', async () => {
    if (isPublishing) return;
    const dir = await window.pywebview.api.choose_dir('source_dir');
    if (dir) {
        el.sourceDirInput.value = dir;
        el.sourceDirInput.classList.remove('text-slate-600', 'placeholder-slate-400');
        el.sourceDirInput.classList.add('text-accent-600');
        appendLog(`[SYSTEM] 草稿核心库挂载成功: ${dir}`, "text-emerald-400");
        refreshBooks();
    }
});

el.btnStart.addEventListener('click', async () => {
    if (isPublishing) return;
    
    if (!el.sourceDirInput.value || !el.archiveDirInput.value) {
        showModal('应用预检未通过', '为了正常运作与您的核心数据安全，发文存档与归档位置均禁止为空！\n请先在页面顶部填好这2个必要的发文流路径配置。', true, false);
        return;
    }

    if (currentBooks.length === 0) {
        showModal('任务栈中止', '在指定的目录下没有找到任何包含 TXT 原稿的小说。\n\n请确保发文草稿源的下属子文件夹中包含了标准的 TXT 文件（名称格式为“第X章...”），然后再点击“刷新”。', true, false);
        return;
    }
    
    const idx = parseInt(el.bookSelect.value);
    const book = currentBooks[idx];
    
    let pCount = parseInt(el.publishCount.value);
    if (isNaN(pCount) || pCount <= 0) pCount = null;
    if (pCount > book.count) pCount = book.count;
    
    let vNum = parseInt(el.volumeNum.value);
    if (isNaN(vNum) || vNum <= 0) vNum = null;
    
    toggleUI(true);
    
    try {
        await window.pywebview.api.start_publish(book.name, pCount, vNum);
    } catch (e) {
        console.error(e);
    } finally {
        toggleUI(false);
        refreshBooks();
    }
});

// Custom Dropdown JS Control
const _customSelectTrigger = document.getElementById('custom-select-trigger');
const _customSelectDropdown = document.getElementById('custom-select-dropdown');
const _customSelectArrow = document.getElementById('custom-select-arrow');

if(_customSelectTrigger) {
    _customSelectTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isPublishing) return;
        const isHidden = _customSelectDropdown.classList.contains('hidden');
        if (isHidden) {
            _customSelectDropdown.classList.remove('hidden');
            setTimeout(() => {
                _customSelectDropdown.classList.remove('opacity-0');
                _customSelectArrow.classList.add('rotate-180');
            }, 10);
        } else {
            _customSelectDropdown.classList.add('opacity-0');
            _customSelectArrow.classList.remove('rotate-180');
            setTimeout(() => _customSelectDropdown.classList.add('hidden'), 200);
        }
    });

    document.addEventListener('click', (e) => {
        if (!_customSelectTrigger.contains(e.target) && !_customSelectDropdown.contains(e.target)) {
            _customSelectDropdown.classList.add('opacity-0');
            _customSelectArrow.classList.remove('rotate-180');
            setTimeout(() => _customSelectDropdown.classList.add('hidden'), 200);
        }
    });
}
