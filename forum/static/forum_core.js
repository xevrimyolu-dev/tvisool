document.addEventListener('DOMContentLoaded', () => {
    const createPostForm = document.getElementById('create-post-form');
    const composerTextarea = document.getElementById('composer-textarea');
    const composerFileInput = document.getElementById('composer-file-input');
    const composerPreviewContainer = document.getElementById('composer-preview-container');
    const composerSubmitBtn = document.getElementById('composer-submit-btn');
    const postFeedContainer = document.getElementById('post-feed-container');
    const charCounter = document.getElementById('char-counter');

    const MAX_IMAGE_COUNT = 7;
    const MAX_IMAGE_SIZE_MB = 6;
    const MAX_TOTAL_IMAGE_SIZE_MB = 42;
    const MAX_AUDIO_COUNT = 1;
    const MAX_AUDIO_SIZE_MB = 20;
    const MAX_DOCUMENT_COUNT = 1;
    const MAX_DOCUMENT_SIZE_MB = 70;
    const MAX_CONTENT_CHARS = 1000;

    let selectedFiles = [];
    let croppedImageData = [];
    let cooldownTimer = null;

    function handleCooldown(endTimeISO, reasonKey) {
        if (!endTimeISO) return;

        const endTime = new Date(endTimeISO);

        if (cooldownTimer) clearInterval(cooldownTimer);

        const elementsToDisable = [
            document.getElementById('composer-submit-btn'),
            document.getElementById('image-upload-btn'),
            document.getElementById('audio-upload-btn'),
            document.getElementById('doc-upload-btn'),
            document.getElementById('composer-textarea')
        ];

        document.body.dataset.isMuted = 'true';

        elementsToDisable.forEach(el => { if (el) el.disabled = true; });

        cooldownTimer = setInterval(() => {
            const now = new Date();
            const remaining = endTime - now;

            if (remaining <= 0) {
                clearInterval(cooldownTimer);
                document.body.dataset.isMuted = 'false';
                elementsToDisable.forEach(el => { if (el) el.disabled = false; });

                if (composerTextarea) {
                    const placeholderKey = composerTextarea.dataset.placeholderKey || 'composer_placeholder';
                    composerTextarea.placeholder = getLang(placeholderKey, { username: document.body.dataset.username || 'kullanıcı' });
                }
                updateSubmitButtonState();
                window.showToastNotification(getLang('cooldown_ended'), 'success');
                return;
            }

            const hours = Math.floor((remaining / (1000 * 60 * 60)) % 24).toString().padStart(2, '0');
            const minutes = Math.floor((remaining / 1000 / 60) % 60).toString().padStart(2, '0');
            const seconds = Math.floor((remaining / 1000) % 60).toString().padStart(2, '0');

            const timeString = `${hours}:${minutes}:${seconds}`;

            const reasonText = getLang(reasonKey) || getLang('mute_reason_spam');
            if (composerTextarea) {
                const remainingTimeText = getLang('remaining_time');
				composerTextarea.placeholder = `${reasonText} ${remainingTimeText} ${timeString}`;
            }

        }, 1000);
    }

    async function fetchUserStatus() {
        try {
            const response = await fetch('/forum/user/status');
            const data = await response.json();
            if (data.cooldown_until) {
                handleCooldown(data.cooldown_until, data.cooldown_reason_key);
            }
        } catch (error) {
            console.error("Kullanıcı durumu alınamadı:", error);
        }
    }

    fetchUserStatus();

// forum_core.js dosyasını güncelleyin

window.showToastNotification = function(message, type = 'info') {
    let container = document.getElementById('tv-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'tv-toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `tv-toast tv-${type}`;
    const span = document.createElement('span');
    span.textContent = message || '';
    const btn = document.createElement('button');
    btn.className = 'tv-toast-close';
    btn.textContent = '×';
    btn.onclick = () => {
        toast.classList.add('tv-hide');
        setTimeout(() => toast.remove(), 300);
    };
    toast.appendChild(span);
    toast.appendChild(btn);
    container.appendChild(toast);
    requestAnimationFrame(() => { toast.classList.add('tv-show'); });
    setTimeout(() => {
        if (toast.isConnected) {
            toast.classList.add('tv-hide');
            setTimeout(() => toast.remove(), 300);
        }
    }, 4500);
};

window.getCSRFToken = function() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
};

function showSpamCaptchaModal(onConfirm) {
    const existingModal = document.querySelector('.confirmation-modal-backdrop');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.className = 'confirmation-modal-backdrop';

    modal.innerHTML = `
        <div class="confirmation-modal-content">
            <h3>${getLang('founder_verify_title')}</h3>
            <p>${getLang('captcha_required_message') || 'Gönderinizde otomatik sistemlerimiz tarafından spam şüphesi algılandı. Devam etmek için lütfen aşağıdaki işlemi çözün.'}</p>

            <div class="captcha-container" style="margin: 15px 0; display: flex; align-items: center;">
                <img src="/captcha.png?v=${new Date().getTime()}" alt="${getLang('captcha_alt') || 'Doğrulama Kodu'}" class="captcha-image" style="border-radius: 5px; margin-bottom: 10px;">
                <button type="button" id="captcha-reload-btn" class="composer-action-btn" title="${getLang('reload') || 'Yenile'}" style="vertical-align: top; margin-left: 10px;">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </div>

            <input type="tel"
                   id="spam-captcha-input"
                   class="confirmation-modal-input"
                   placeholder="${getLang('captcha_placeholder') || 'Cevabı buraya yazın...'}"
                   required
                   autocomplete="off"
                   maxlength="5"
                   pattern="[0-9]*"
                   inputmode="numeric"
                   style="text-align: center; font-size: 18px; letter-spacing: 2px;">

            <div class="confirmation-modal-actions">
                <button class="confirmation-modal-btn cancel">${getLang('modal_cancel')}</button>
                <button class="confirmation-modal-btn confirm">${getLang('captcha_confirm') || 'Gönderiyi Doğrula'}</button>
            </div>
        </div>
    `;
    
    const closeModal = () => modal.remove();
    const captchaInput = modal.querySelector('#spam-captcha-input');
    const captchaImage = modal.querySelector('.captcha-image');
    const reloadBtn = modal.querySelector('#captcha-reload-btn');

    captchaInput.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
        if (e.target.value.length > 5) {
            e.target.value = e.target.value.slice(0, 5);
        }
    });

    captchaInput.addEventListener('keydown', (e) => {
        if (!/[\d]|Backspace|Delete|Tab|ArrowLeft|ArrowRight|ArrowUp|ArrowDown/.test(e.key)) {
            e.preventDefault();
        }
    });

    reloadBtn.addEventListener('click', () => {
        captchaImage.src = `/captcha.png?v=${new Date().getTime()}`;
        captchaInput.value = '';
        captchaInput.focus();
    });

    captchaInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            modal.querySelector('.confirm').click();
        }
    });

    modal.querySelector('.cancel').addEventListener('click', closeModal);

    modal.querySelector('.confirm').addEventListener('click', () => {
        const answer = captchaInput.value.trim();
        if (answer.length > 0) { 
            onConfirm(answer);
            closeModal();
        } else {
            captchaInput.style.border = '2px solid red';
            captchaInput.placeholder = getLang('captcha_placeholder_error') || 'Lütfen cevabı girin!';
            setTimeout(() => {
                captchaInput.style.border = '';
                captchaInput.placeholder = getLang('captcha_placeholder') || 'Cevabı buraya yazın...';
            }, 3000);
        }
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.body.appendChild(modal);
    captchaInput.focus();
    
    captchaImage.addEventListener('error', () => {
        captchaImage.alt = getLang('captcha_load_error') || 'CAPTCHA yüklenemedi, lütfen yenileyin';
    });
}

    if (createPostForm) {

        document.getElementById('image-upload-btn')?.addEventListener('click', () => triggerFileInput('image/png,image/jpeg,image/gif'));
        
        document.getElementById('doc-upload-btn')?.addEventListener('click', () => triggerFileInput('.docx,.pdf,.txt,.zip,.rar,.uasset,.uexp,.ini,.html,.css,.py,.js,.bms,.exe,.php,.7z,.tar,.rar,.sql'));
        document.getElementById('audio-upload-btn')?.addEventListener('click', () => triggerFileInput('audio/mp3,audio/wav,audio/ogg'));

        function triggerFileInput(accept) {
            composerFileInput.accept = accept;
            composerFileInput.click();
        }

        composerTextarea.addEventListener('input', updateSubmitButtonState);
        composerFileInput.addEventListener('change', handleFileSelection);
        createPostForm.addEventListener('submit', handleFormSubmit);
    }

    function handleFileSelection() {
        let newFiles = Array.from(composerFileInput.files);
        if (newFiles.length === 0) return;

        

        if (newFiles.some(f => f.type.startsWith('image/'))) {
            croppedImageData = [];
        }

        const currentImages = selectedFiles.filter(f => f.type.startsWith('image/'));
        const currentAudios = selectedFiles.filter(f => f.type.startsWith('audio/'));
        const currentDocs = selectedFiles.filter(f => !f.type.startsWith('image/') && !f.type.startsWith('audio/'));

        if (currentAudios.length > 0 || currentDocs.length > 0) {
            showToastNotification(getLang('media_mix_error_1'), 'error');
            composerFileInput.value = '';
            return;
        }

        const newFileTypes = new Set(newFiles.map(file => {
            if (file.type.startsWith('image/')) return 'image';
            if (file.type.startsWith('audio/')) return 'audio';
            return 'document';
        }));

        if (newFileTypes.size > 1 && !(newFileTypes.size === 2 && newFileTypes.has('image'))) {
             showToastNotification(getLang('media_mix_error_multi_type'), 'error');
             composerFileInput.value = '';
             return;
        }

        if (currentImages.length > 0 && Array.from(newFileTypes).some(type => type !== 'image')) {
            showToastNotification(getLang('media_mix_error_2'), 'error');
            composerFileInput.value = '';
            return;
        }

        if ((currentAudios.length > 0 || currentDocs.length > 0) && Array.from(newFileTypes).includes('image')) {
            showToastNotification(getLang('media_mix_error_3'), 'error');
            composerFileInput.value = '';
            return;
        }

        // --- BOYUT KONTROLLERİ: YÜKLEMEDEN ÖNCE ---
        // Resimler için tekil ve toplam boyut kontrolü
        const bytesPerMB = 1024 * 1024;
        const currentImagesTotalSize = currentImages.reduce((sum, f) => sum + (f.size || 0), 0);

        const newImageFiles = newFiles.filter(f => f.type.startsWith('image/'));
        // Tekil sınır
        for (const img of newImageFiles) {
            if ((img.size || 0) > MAX_IMAGE_SIZE_MB * bytesPerMB) {
                showToastNotification(getLang('image_size_limit', { filename: img.name, limit: MAX_IMAGE_SIZE_MB }), 'error');
                composerFileInput.value = '';
                return;
            }
        }
        // Toplam sınır
        const newImagesTotalSize = newImageFiles.reduce((sum, f) => sum + (f.size || 0), 0);
        if (newImageFiles.length > 0 && (currentImagesTotalSize + newImagesTotalSize) > MAX_TOTAL_IMAGE_SIZE_MB * bytesPerMB) {
            showToastNotification(getLang('image_total_size_limit', { limit: MAX_TOTAL_IMAGE_SIZE_MB }), 'error');
            composerFileInput.value = '';
            return;
        }

        // Ses dosyası tekil boyut sınırı
        const newAudioFiles = newFiles.filter(f => f.type.startsWith('audio/'));
        if (newAudioFiles.length > 0) {
            const audioFile = newAudioFiles[0];
            if ((audioFile.size || 0) > MAX_AUDIO_SIZE_MB * bytesPerMB) {
                showToastNotification(getLang('audio_size_limit', { limit: MAX_AUDIO_SIZE_MB }), 'error');
                composerFileInput.value = '';
                return;
            }
        }

        // Belge dosyası tekil boyut sınırı
        const newDocFiles = newFiles.filter(f => !f.type.startsWith('image/') && !f.type.startsWith('video/') && !f.type.startsWith('audio/'));
        if (newDocFiles.length > 0) {
            const docFile = newDocFiles[0];
            if ((docFile.size || 0) > MAX_DOCUMENT_SIZE_MB * bytesPerMB) {
                showToastNotification(getLang('doc_size_limit', { limit: MAX_DOCUMENT_SIZE_MB }), 'error');
                composerFileInput.value = '';
                return;
            }
        }

        let filesToAdd = [];

        if (newImageFiles.length > 0) {
            const availableSlots = MAX_IMAGE_COUNT - currentImages.length;
            if (availableSlots <= 0) {
                showToastNotification(getLang('image_count_limit_toast', {limit: MAX_IMAGE_COUNT}), 'error');
            } else if (newImageFiles.length > availableSlots) {
                const slicedImages = newImageFiles.slice(0, availableSlots);
                filesToAdd.push(...slicedImages);
                showToastNotification(getLang('image_limit_partial_add', {limit: availableSlots}), 'info');
            } else {
                filesToAdd.push(...newImageFiles);
            }
        }

        ['audio', 'document'].forEach(type => {
            const newTypedFiles = newFiles.filter(f => {
                if (type === 'audio') return f.type.startsWith('audio/');
                if (type === 'document') return !f.type.startsWith('image/') && !f.type.startsWith('video/') && !f.type.startsWith('audio/');
                return false;
            });

            if (newTypedFiles.length > 0) {
                let limit = 0;
                let typeName = '';
                if (type === 'audio') { limit = MAX_AUDIO_COUNT; typeName = 'ses dosyası'; }
                if (type === 'document') { limit = MAX_DOCUMENT_COUNT; typeName = 'belge'; }

                if (newTypedFiles.length > limit) {
                    showToastNotification(getLang('media_limit_exceeded', {limit: limit, typeName: typeName}), 'error');
                } else {
                    filesToAdd.push(...newTypedFiles);
                }
            }
        });

        filesToAdd.forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });

        renderPreviews();
        composerFileInput.value = '';
    }

    function renderPreviews() {
        composerPreviewContainer.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item';

            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-preview-btn';
            removeBtn.innerHTML = '&times;';
            removeBtn.type = 'button';
            removeBtn.onclick = () => {
                selectedFiles.splice(index, 1);
                croppedImageData = [];
                renderPreviews();
            };

            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = e => {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.className = 'preview-image';
                    previewItem.appendChild(img);
                    previewItem.appendChild(removeBtn);
                };
                reader.readAsDataURL(file);
            } else {
                let iconClass = 'fas fa-file-alt';
                if (file.type.startsWith('audio/')) iconClass = 'fas fa-music';

                const icon = document.createElement('i');
                icon.className = `${iconClass} preview-icon`;
                icon.style.cssText = "font-size: 2rem; color: var(--text-light-color);";

                const nameSpan = document.createElement('span');
                nameSpan.textContent = file.name;
                nameSpan.style.cssText = "font-size: 0.7rem; color: var(--text-light-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70px;";

                previewItem.appendChild(icon);
                previewItem.appendChild(nameSpan);
                previewItem.appendChild(removeBtn);
            }

            composerPreviewContainer.appendChild(previewItem);
        });
        updateSubmitButtonState();
    }

    function updateSubmitButtonState() {
        const hasContent = composerTextarea.value.trim().length > 0;
        const hasFiles = selectedFiles.length > 0;
        const isContentTooLong = composerTextarea.value.length > MAX_CONTENT_CHARS;

        if (charCounter) {
            charCounter.textContent = `${composerTextarea.value.length} / ${MAX_CONTENT_CHARS}`;
            charCounter.style.color = isContentTooLong ? '#e74c3c' : 'var(--text-light-color)';
        }

        if (composerSubmitBtn) {
            if (document.body.dataset.isMuted === 'true') {
                composerSubmitBtn.disabled = true;
            } else {
                composerSubmitBtn.disabled = (!hasContent && !hasFiles) || isContentTooLong;
            }
        }
    }

async function handleFormSubmit(e) {
    e.preventDefault();

    if (document.body.dataset.isMuted === 'true') {
        window.showToastNotification(getLang('cannot_post_while_muted'), 'error');
        return;
    }

    // --- Yanıt Etiketi Oluşturma ---
    const previewArea = document.getElementById('reply-preview-area');
    let finalContent = composerTextarea.value.trim();

    // Yanıt verisi varsa, özel etiket formatına çevir
    if (previewArea && previewArea.style.display !== 'none' && previewArea.dataset.replyUser) {
        const rUser = previewArea.dataset.replyUser;
        const rId = previewArea.dataset.replyId;
        let rContent = previewArea.dataset.replyContent || '';
        const rMedia = previewArea.dataset.replyMediaType || '';
        const rThumb = previewArea.dataset.replyThumbUrl || '';
        
        if (rContent.length > 100) rContent = rContent.substring(0, 100) + '...';
        rContent = rContent.replace(/\[/g, '(').replace(/\]/g, ')');

        const attrs = [];
        if (rMedia) attrs.push(`media="${rMedia}"`);
        if (rThumb) attrs.push(`thumb="${rThumb}"`);
        const attrStr = attrs.length ? ' ' + attrs.join(' ') : '';
        const replyTag = `[reply id="${rId}" user="${rUser}"${attrStr}]${rContent}[/reply]\n`;
        finalContent = replyTag + finalContent;
    }
    // ---

    const imageFiles = selectedFiles.filter(f => f.type.startsWith('image/'));

    if (imageFiles.length > 0 && croppedImageData.length === 0) {
        if (typeof showImageCropper === 'function') {
            showImageCropper(imageFiles, (cropperResult) => {
                if (cropperResult && cropperResult.length > 0) {
                    croppedImageData = cropperResult;
                    showToastNotification(getLang('images_cropped_resubmit'), 'info');
                }
            });
        } else {
            showToastNotification(getLang('cropper_load_error'), 'error');
        }
        return;
    }

    const preUploaded = [];

    const formData = new FormData();
    formData.append('content', finalContent);
    selectedFiles.forEach(file => {
        if (!file.type.startsWith('video/')) formData.append('media_files', file);
    });
    
    formData.append('crop_data', JSON.stringify(croppedImageData));

    if (composerSubmitBtn) {
        composerSubmitBtn.disabled = true;
        composerSubmitBtn.textContent = getLang('submitting');
    }

    try {
        // DÜZELTME BURADA: submitPost'tan dönen sonucu (true/false) bekle
        const res = await submitPost(formData);

        if (res && res.success) {
            const pa = document.getElementById('reply-preview-area');
            if (typeof clearReplyPreview === 'function') {
                clearReplyPreview();
            } else if (pa) {
                pa.style.display = 'none';
                pa.removeAttribute('data-reply-user');
                pa.removeAttribute('data-reply-content');
                pa.removeAttribute('data-reply-id');
            }
            
        }
        // Başarısızsa hiçbir şey yapma, böylece alıntı kutusu ekranda kalır.
        
    } catch (error) {
        // ESKİ KOD: console.error('[HATA] Gönderi yollanırken hata:', error); <-- BUNU DA SİL
        
        // Sadece bildirim göster
        // Eğer mesaj zaten tanımlıysa onu, değilse genel hatayı göster
        let msg = error.message;
        if (msg && msg.startsWith('error_prefix')) {
             // Mesaj zaten çevrilmişse olduğu gibi bırak
        } else {
             msg = `${getLang('error_prefix') || 'Hata'}: ${getLang(error.message) || error.message}`;
        }
        
        showToastNotification(msg, 'error');
    } finally {
        if (!document.querySelector('.confirmation-modal-backdrop')) {
            if (composerSubmitBtn) {
                composerSubmitBtn.disabled = false;
                composerSubmitBtn.textContent = getLang('submit_post');
                updateSubmitButtonState();
            }
        }
    }
}


async function submitPost(formData) {
    if (composerSubmitBtn) {
        composerSubmitBtn.disabled = true;
        composerSubmitBtn.textContent = getLang('submitting') || 'Gönderiliyor...';
    }

    try {
        const response = await fetch('/forum/posts/create', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData
        });

        // JSON içeriği yalnızca içerik türü uygunsa oku
        let result = {};
        const ct = response.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) {
            try {
                result = await response.json();
            } catch (e) {
                console.warn("Sunucu yanıtı JSON değil:", e);
            }
        }

        // --- 429 (Çok Hızlı İstek / Aktif Bekleme) ---
        if (response.status === 429) {
            const waitTime = result.wait_time || 10;
            let msg = result.error_key
                ? getLang(result.error_key, { wait_time: waitTime })
                : getLang('cooldown_too_fast', { wait_time: waitTime });

            if (result.cooldown_until) {
                handleCooldown(result.cooldown_until, result.cooldown_reason_key);
            }

            window.showToastNotification(msg, 'error');
            return false;
        }

        // --- Diğer Veritabanı Kaynaklı Beklemeler (cooldown_active) ---
        if (result.cooldown_active && result.cooldown_until) {
            handleCooldown(result.cooldown_until, result.cooldown_reason_key);
            const msg = getLang(result.error_key) || 'Lütfen bekleyin.';
            window.showToastNotification(msg, 'error');
            return false;
        }

        // --- Captcha Gereksinimi ---
        if (result.requires_captcha) {
            window.showToastNotification(getLang(result.message_key) || 'Doğrulama gerekli.', 'info');
            showSpamCaptchaModal((captchaAnswer) => {
                formData.append('captcha_answer', captchaAnswer);
                submitPost(formData).then(success => {
                    if (success && typeof clearReplyPreview === 'function') clearReplyPreview();
                });
            });
            // Butonu tekrar aktif et
            if (composerSubmitBtn) {
                composerSubmitBtn.disabled = false;
                composerSubmitBtn.textContent = getLang('submit_post');
            }
            return false;
        }

        // --- Genel Hata Kontrolü (400, 500 vb.) ---
        if (!response.ok) {
            let finalErrorMessage = "Bilinmeyen bir hata oluştu.";
            
            if (result.error_key) {
                const params = {
                    limit: result.limit,
                    filename: result.filename,
                    wait_time: result.wait_time
                };
                finalErrorMessage = getLang(result.error_key, params);
            } else if (result.message) {
                finalErrorMessage = result.message;
            }
            
            throw new Error(finalErrorMessage);
        }

        // --- BAŞARILI SENARYO ---
        if (composerTextarea) composerTextarea.value = '';
        selectedFiles = [];
        croppedImageData = [];
        renderPreviews();

        if (charCounter) {
            charCounter.textContent = `0 / ${MAX_CONTENT_CHARS}`;
            charCounter.style.color = 'var(--text-light-color)';
        }

        window.showToastNotification(getLang(result.message_key) || 'Gönderildi!', 'success');

        if (typeof clearReplyPreview === 'function') clearReplyPreview();

        // Yeni postu listeye ekle
        try {
            if (result.post_id) {
                const newPostResponse = await fetch(`/forum/posts/${result.post_id}`);
                if (newPostResponse.ok) {
                    const newPostData = await newPostResponse.json();
                    if (window.renderPost) {
                        const newPostElement = window.renderPost(newPostData);
                        const emptyState = document.querySelector('.empty-state');
                        if (emptyState) emptyState.remove();
                        if (postFeedContainer) postFeedContainer.prepend(newPostElement);
                    }
                }
            }
        } catch (fetchError) {
            console.warn("Yeni post verisi çekilemedi:", fetchError);
        }

        return result;

    } catch (error) {
        // --- HATA YAKALAMA VE TOAST GÖSTERME ---
        // Hata mesajını al
        let message = error.message;
        
        // getLang bazen anahtarı bulamazsa anahtarı döndürür, bu durumda temizleyelim
        if (message === 'cooldown_too_fast') {
            message = "Çok hızlı işlem yapıyorsunuz. Lütfen bekleyin.";
        }

        window.showToastNotification(message, 'error');
        return false;

    } finally {
        // Modal açık değilse butonu aktif et
        if (!document.querySelector('.confirmation-modal-backdrop')) {
            if (composerSubmitBtn) {
                composerSubmitBtn.disabled = false;
                composerSubmitBtn.textContent = getLang('submit_post') || 'Gönder';
                if (typeof updateSubmitButtonState === 'function') updateSubmitButtonState();
            }
        }
    }
}

async function fetchAndRenderPosts() {
        const singlePostId = document.body.dataset.singlePostId;
        const fetchUrl = singlePostId
            ? `/forum/posts/${singlePostId}`
            : '/forum/posts/all_with_like_status';

        try {
            const response = await fetch(fetchUrl);
            if (!response.ok) throw new Error(getLang('post_load_error'));

            const data = await response.json();
            const posts = singlePostId ? [data] : data;

            postFeedContainer.innerHTML = '';

            if (posts.length === 0) {
                postFeedContainer.innerHTML = `<div class="empty-state"><i class="fas fa-newspaper"></i><p>${getLang('empty_feed')}</p></div>`;
                return;
            }

            posts.forEach(post => {
                const postElement = window.renderPost(post);
                postFeedContainer.appendChild(postElement);
            });

        } catch (error) {
            postFeedContainer.innerHTML = `<div class="error-state"><i class="fas fa-exclamation-triangle"></i><p>${error.message}</p><button id="retry-fetch-btn" class="retry-button">${getLang('retry')}</button></div>`;
            document.getElementById('retry-fetch-btn')?.addEventListener('click', fetchAndRenderPosts);
        }
    }

    fetchAndRenderPosts();

    document.addEventListener('languageChanged', () => {
        fetchAndRenderPosts();
    });

    const scrollContainer = document.getElementById('page-forum');
    if (scrollContainer) {
        let isRefreshing = false;
        let lastRefresh = 0;
        const REFRESH_DEBOUNCE_MS = 2500;
        const THRESHOLD_PX = 12;
        let prevScrollTop = scrollContainer.scrollTop;
        let wasAtTop = prevScrollTop <= THRESHOLD_PX;
        let wasAtBottom = (scrollContainer.scrollHeight - scrollContainer.clientHeight - prevScrollTop) <= THRESHOLD_PX;

        const indicator = document.createElement('div');
        indicator.className = 'feed-refresh-indicator';
        indicator.innerHTML = '<div class="bar"></div>';
        scrollContainer.prepend(indicator);

        async function backgroundRefresh(triggerSide) {
            const now = Date.now();
            if (isRefreshing || (now - lastRefresh) < REFRESH_DEBOUNCE_MS) return;
            isRefreshing = true;
            lastRefresh = now;
            indicator.classList.add('active');

            prevScrollTop = scrollContainer.scrollTop;
            const currentIds = new Set(Array.from(postFeedContainer.querySelectorAll('.post-card')).map(el => Number(el.dataset.postId)));
            let addedHeight = 0;
            const gapValue = parseInt(getComputedStyle(postFeedContainer).gap || getComputedStyle(postFeedContainer).rowGap || '0', 10) || 0;

            try {
                const response = await fetch('/forum/posts/all_with_like_status');
                if (!response.ok) throw new Error('post_load_error');
                const posts = await response.json();

                const fragment = document.createDocumentFragment();
                const newNodes = [];
                for (const post of posts) {
                    if (!currentIds.has(post.id)) {
                        const node = window.renderPost(post);
                        fragment.appendChild(node);
                        newNodes.push(node);
                    }
                }
                if (newNodes.length > 0) {
                    postFeedContainer.prepend(fragment);
                    newNodes.forEach(n => { addedHeight += n.getBoundingClientRect().height + gapValue; });
                    scrollContainer.scrollTop = prevScrollTop + addedHeight;
                    indicator.classList.add('success');
                    setTimeout(() => { indicator.classList.remove('success'); }, 700);
                } else {
                    scrollContainer.scrollTop = prevScrollTop;
                }
            } catch (e) {
            } finally {
                indicator.classList.remove('active');
                isRefreshing = false;
            }
        }

        scrollContainer.addEventListener('scroll', () => {
            const currentTop = scrollContainer.scrollTop;
            const atTop = currentTop <= THRESHOLD_PX;
            const atBottom = (scrollContainer.scrollHeight - scrollContainer.clientHeight - currentTop) <= THRESHOLD_PX;

            if (wasAtTop && !atTop && prevScrollTop <= THRESHOLD_PX) {
                backgroundRefresh('top');
            }
            if (atBottom && !wasAtBottom) {
                backgroundRefresh('bottom');
            }

            wasAtTop = atTop;
            wasAtBottom = atBottom;
            prevScrollTop = currentTop;
        }, { passive: true });

        scrollContainer.addEventListener('wheel', (e) => {
            const atTop = scrollContainer.scrollTop <= THRESHOLD_PX;
            const atBottom = (scrollContainer.scrollHeight - scrollContainer.clientHeight - scrollContainer.scrollTop) <= THRESHOLD_PX;
            if (atTop && e.deltaY > 0) {
                backgroundRefresh('top');
            } else if (atBottom && e.deltaY < 0) {
                backgroundRefresh('bottom');
            }
        }, { passive: true });
    }

});
