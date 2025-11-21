document.addEventListener('DOMContentLoaded', () => {
    const MAX_COMMENT_LENGTH = 300;
    const postFeedContainer = document.getElementById('post-feed-container');
    const imageViewerModal = document.getElementById('image-viewer-modal');
    const viewerImageContent = document.getElementById('viewer-image-content');
    const imageViewerClose = document.querySelector('.image-viewer-close');

    let currentViewerItems = [];
    let currentViewerIndex = 0;
    
    let longPressTimer;
    let isLongPress = false;
    const LONG_PRESS_DURATION = 500;

    if (!postFeedContainer) {
        return;
    }

    postFeedContainer.addEventListener('mousedown', handlePressStart);
    postFeedContainer.addEventListener('touchstart', handlePressStart, { passive: true });
    
    postFeedContainer.addEventListener('mouseup', handlePressEnd);
    postFeedContainer.addEventListener('mouseleave', handlePressEnd);
    postFeedContainer.addEventListener('touchend', handlePressEnd);
    postFeedContainer.addEventListener('touchmove', handlePressEnd);

    function handlePressStart(e) {
        if (e.target.closest('button') || e.target.closest('.video-player-modal') || e.target.closest('.image-viewer-backdrop')) return;

        const postCard = e.target.closest('.post-card');
        if (!postCard) return;

        isLongPress = false;
        longPressTimer = setTimeout(() => {
            isLongPress = true;
            if (navigator.vibrate) navigator.vibrate(50);
            showContextMenu(postCard);
        }, LONG_PRESS_DURATION);
    }

    function handlePressEnd(e) {
        clearTimeout(longPressTimer);
        if (isLongPress) {
            if(e.cancelable) e.preventDefault();
            isLongPress = false;
        }
    }

function showContextMenu(postCard) {
    const postId = postCard.dataset.postId;
    const authorId = postCard.dataset.authorId;
    const authorName = postCard.querySelector('.post-author-name').textContent;
    
    // --- GÜNCELLEME BAŞLANGICI: İÇ İÇE ALINTIYI ENGELLEME ---
    
    // 1. Mesaj elementini bul
    const contentEl = postCard.querySelector('.post-content');
    
    // 2. Elementi klonla (Gerçek görünümü bozmamak için kopyası üzerinde çalışacağız)
    const clone = contentEl.cloneNode(true);
    
    // 3. Klonun içindeki eski alıntı kutularını (.post-quote) bul ve SİL
    clone.querySelectorAll('.post-quote').forEach(quote => quote.remove());
    
    // 4. Ayrıca "Devamını Oku" gibi gizli/açık metin yapıları varsa onları birleştir
    // (Eğer visible-text/hidden-text yapısı kullanıyorsan metni düzgün almak için)
    let rawText = "";
    if (clone.querySelector('.visible-text')) {
         const visible = clone.querySelector('.visible-text').innerText;
         const hidden = clone.querySelector('.hidden-text').innerText;
         rawText = visible + hidden; // Tam metni birleştir
    } else {
         rawText = clone.innerText;
    }

    // 5. Son güvenlik temizliği: Hala [reply] etiketi kaldıysa Regex ile uçur
    let postContent = rawText.replace(/\[reply[\s\S]*?\[\/reply\]/g, '').trim();

    // --- GÜNCELLEME SONU ---

    const postUrl = `${window.location.origin}/forum/view/post/${postId}`;
    
    const currentUserId = document.body.dataset.userId;
    const currentUserRole = document.body.dataset.userRole;
    const isOwner = authorId == currentUserId;
    const isKurucu = currentUserRole === 'kurucu';

    document.querySelector('.context-menu-backdrop')?.remove();

    const backdrop = document.createElement('div');
    backdrop.className = 'context-menu-backdrop';
    
    let menuHTML = `<div class="context-menu">`;

    menuHTML += `
        <button class="context-menu-item" id="ctx-reply">
            <i class="fas fa-reply"></i> ${getLang('context_reply')}
        </button>
    `;

    if (postContent && postContent.trim().length > 0) {
        menuHTML += `
            <button class="context-menu-item" id="ctx-copy-text">
                <i class="far fa-copy"></i> ${getLang('context_copy_text')}
            </button>
        `;
    }

    menuHTML += `
        <button class="context-menu-item" id="ctx-copy-link">
            <i class="fas fa-link"></i> ${getLang('context_copy_link')}
        </button>
    `;

    if (!isOwner) {
        menuHTML += `
            <button class="context-menu-item" id="ctx-report">
                <i class="fas fa-flag"></i> ${getLang('context_report')}
            </button>
        `;
    }

    if (isOwner || isKurucu) {
        menuHTML += `
            <button class="context-menu-item delete-option" id="ctx-delete">
                <i class="fas fa-trash"></i> ${getLang('context_delete')}
            </button>
        `;
    }

    menuHTML += `</div>`;
    backdrop.innerHTML = menuHTML;
    document.body.appendChild(backdrop);

    backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.remove();
    });

    backdrop.querySelector('#ctx-reply').addEventListener('click', () => {
        backdrop.remove();
        handleSmartReply(authorName, postContent, postId);
        const thumbEl = document.getElementById('reply-media-thumb');
        if (thumbEl) {
            thumbEl.innerHTML = '';
            const hasImage = postCard.dataset.hasImage === 'true';
            const hasVideo = postCard.dataset.hasVideo === 'true';
            const hasAudio = postCard.dataset.hasAudio === 'true';
            const hasDocument = postCard.dataset.hasDocument === 'true';
            const previewArea = document.getElementById('reply-preview-area');
            if (hasImage && postCard.dataset.imageUrl) {
                const img = document.createElement('img');
                img.src = postCard.dataset.imageUrl;
                img.alt = getLang('alt_post_image') || 'image';
                img.className = 'reply-thumb-image';
                thumbEl.appendChild(img);
                const textEl = document.getElementById('reply-preview-text');
                if (textEl) textEl.textContent = '';
                if (previewArea) {
                    previewArea.dataset.replyMediaType = 'image';
                    previewArea.dataset.replyThumbUrl = postCard.dataset.imageUrl;
                }
            } else if (hasVideo && postCard.dataset.videoThumbUrl) {
                const img = document.createElement('img');
                img.src = postCard.dataset.videoThumbUrl;
                img.alt = getLang('alt_video_thumbnail') || 'video';
                img.className = 'reply-thumb-image';
                thumbEl.appendChild(img);
                const textEl = document.getElementById('reply-preview-text');
                if (textEl) textEl.textContent = '';
                if (previewArea) {
                    previewArea.dataset.replyMediaType = 'video';
                    previewArea.dataset.replyThumbUrl = postCard.dataset.videoThumbUrl;
                }
            } else {
                let iconCls = '';
                if (hasVideo) iconCls = 'fas fa-video';
                else if (hasAudio) iconCls = 'fas fa-music';
                else if (hasDocument) iconCls = 'fas fa-file-alt';
                if (iconCls) {
                    const i = document.createElement('i');
                    i.className = iconCls + ' reply-thumb-icon';
                    thumbEl.appendChild(i);
                    if (previewArea) {
                        if (hasVideo) previewArea.dataset.replyMediaType = 'video';
                        else if (hasAudio) previewArea.dataset.replyMediaType = 'audio';
                        else if (hasDocument) previewArea.dataset.replyMediaType = 'document';
                        previewArea.dataset.replyThumbUrl = '';
                    }
                }
            }
        }
    });

    const copyTextBtn = backdrop.querySelector('#ctx-copy-text');
    if (copyTextBtn) {
        copyTextBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(postContent).then(() => {
                window.showToastNotification(getLang('text_copied_to_clipboard'), 'success');
            });
            backdrop.remove();
        });
    }

    backdrop.querySelector('#ctx-copy-link').addEventListener('click', () => {
        navigator.clipboard.writeText(postUrl).then(() => {
            window.showToastNotification(getLang('link_copied_to_clipboard'), 'success');
        });
        backdrop.remove();
    });

    const reportBtn = backdrop.querySelector('#ctx-report');
    if (reportBtn) {
        reportBtn.addEventListener('click', () => {
            backdrop.remove();
            showReportModal(postId);
        });
    }

    const deleteBtn = backdrop.querySelector('#ctx-delete');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            backdrop.remove();
            handleDeletePost(postId, { closest: () => document.createElement('div') });
        });
    }
}

    function handleSmartReply(username, content, postId) {
        const previewArea = document.getElementById('reply-preview-area');
        const usernameEl = document.getElementById('reply-preview-username');
        const textEl = document.getElementById('reply-preview-text');
        const textarea = document.getElementById('composer-textarea');
        const closeBtn = document.getElementById('close-reply-btn');

        if (!previewArea || !textarea) return;

        usernameEl.textContent = getLang('replying_to', {username: username});
        
        let previewText = content.trim();
        previewText = previewText.replace(/\[reply.*?\[\/reply\]/g, '').trim();

        if (previewText.length > 80) {
            previewText = previewText.substring(0, 80) + '...';
        }
        textEl.textContent = previewText;

        previewArea.dataset.replyUser = username;
        previewArea.dataset.replyContent = previewText;
        previewArea.dataset.replyId = postId;

        previewArea.style.display = 'flex';
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
        textarea.focus();

        closeBtn.onclick = function() {
            clearReplyPreview();
        };
    }

    function clearReplyPreview() {
        const previewArea = document.getElementById('reply-preview-area');
        if (previewArea) {
            previewArea.style.display = 'none';
            previewArea.removeAttribute('data-reply-user');
            previewArea.removeAttribute('data-reply-content');
            document.getElementById('reply-preview-text').textContent = '';
            document.getElementById('reply-preview-username').textContent = '';
        }
    }

    function showReportModal(postId) {
        const modal = document.createElement('div');
        modal.className = 'confirmation-modal-backdrop';
        
        const reasons = [
            { key: 'report_reason_1', val: 'İçerik rahatsız edici veya spam' },
            { key: 'report_reason_2', val: 'Nefret söylemi veya sembolleri' },
            { key: 'report_reason_3', val: 'Yasadışı veya kısıtlı ürün satışı' },
            { key: 'report_reason_4', val: 'Zorbalık veya taciz' },
            { key: 'report_reason_5', val: 'Fikri mülkiyet ihlali' },
            { key: 'report_reason_6', val: 'İntihar veya kendine zarar verme' },
            { key: 'report_reason_7', val: 'Yanlış veya yanıltıcı bilgi' },
            { key: 'report_reason_8', val: 'Çıplaklık veya cinsel içerik' }
        ];

        let optionsHTML = '';
        reasons.forEach(r => {
            const text = getLang(r.key) || r.val;
            optionsHTML += `<button class="report-option" data-reason="${r.key}">${text}</button>`;
        });

        modal.innerHTML = `
            <div class="report-modal-content">
                <div class="report-modal-header">
                    <h3>${getLang('report_title')}</h3>
                </div>
                <div class="report-options-list">
                    ${optionsHTML}
                </div>
                <div class="confirmation-modal-actions" style="margin-top:15px; justify-content: center;">
                    <button class="confirmation-modal-btn cancel">${getLang('modal_cancel')}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const closeModal = () => modal.remove();
        modal.querySelector('.cancel').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

        modal.querySelectorAll('.report-option').forEach(btn => {
            btn.addEventListener('click', async () => {
                const reason = btn.dataset.reason;
                closeModal();
                
                try {
                    const response = await fetch(`/forum/posts/${postId}/report`, {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-CSRFToken': window.getCSRFToken() 
                        },
                        body: JSON.stringify({ reason: reason })
                    });
                    
                    const result = await response.json();
                    if(response.ok) {
                        window.showToastNotification(getLang(result.message_key), 'success');
                    } else {
                        window.showToastNotification(getLang('report_error'), 'error');
                    }
                } catch (e) {
                    window.showToastNotification(getLang('report_error'), 'error');
                }
            });
        });
    }

    window.showConfirmationModal = function(title, message, onConfirm) {
        const existingModal = document.querySelector('.confirmation-modal-backdrop');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.className = 'confirmation-modal-backdrop';
        modal.innerHTML = `
            <div class="confirmation-modal-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="confirmation-modal-actions">
                    <button class="confirmation-modal-btn cancel">${getLang('modal_no')}</button>
                    <button class="confirmation-modal-btn confirm">${getLang('modal_yes')}</button>
                </div>
            </div>
        `;

        const closeModal = () => modal.remove();

        modal.querySelector('.cancel').addEventListener('click', closeModal);
        modal.querySelector('.confirm').addEventListener('click', () => {
            onConfirm();
            closeModal();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        document.body.appendChild(modal);
    }

    function showFounderPasswordModal(title, message, onConfirm) {
        const existingModal = document.querySelector('.confirmation-modal-backdrop');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.className = 'confirmation-modal-backdrop';
        modal.innerHTML = `
            <div class="confirmation-modal-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <input type="password" id="founder-password-input" class="confirmation-modal-input" placeholder="${getLang('modal_founder_password_placeholder')}" required>
                <div class="confirmation-modal-actions">
                    <button class="confirmation-modal-btn cancel">${getLang('modal_cancel')}</button>
                    <button class="confirmation-modal-btn confirm">${getLang('modal_delete_post_confirm')}</button>
                </div>
            </div>
        `;

        const closeModal = () => modal.remove();
        const passwordInput = modal.querySelector('#founder-password-input');

        modal.querySelector('.cancel').addEventListener('click', closeModal);

        modal.querySelector('.confirm').addEventListener('click', () => {
            const password = passwordInput.value;
            if (password) {
                onConfirm(password);
                closeModal();
            } else {
                passwordInput.style.border = '1px solid red';
                setTimeout(() => { passwordInput.style.border = ''; }, 2000);
            }
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        document.body.appendChild(modal);
        passwordInput.focus();
    }

    function showMuteDurationModal(onConfirm) {
        const existingModal = document.querySelector('.confirmation-modal-backdrop');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.className = 'confirmation-modal-backdrop';
        modal.innerHTML = `
            <div class="confirmation-modal-content">
                <h3>${getLang('modal_mute_user_title')}</h3>
                <p>${getLang('modal_mute_duration_message')}</p>
                <select id="mute-duration-select" class="confirmation-modal-input">
                    <option value="10m">${getLang('duration_10m')}</option>
                    <option value="30m">${getLang('duration_30m')}</option>
                    <option value="1h">${getLang('duration_1h')}</option>
                    <option value="3h">${getLang('duration_3h')}</option>
                    <option value="5h">${getLang('duration_5h')}</option>
                    <option value="1d">${getLang('duration_1d')}</option>
                    <option value="3d">${getLang('duration_3d')}</option>
                    <option value="5d">${getLang('duration_5d')}</option>
                    <option value="1w">${getLang('duration_1w')}</option>
                    <option value="1mo">${getLang('duration_1mo')}</option>
                    <option value="3mo">${getLang('duration_3mo')}</option>
                    <option value="5mo">${getLang('duration_5mo')}</option>
                    <option value="1y">${getLang('duration_1y')}</option>
                </select>
                <div class="confirmation-modal-actions">
                    <button class="confirmation-modal-btn cancel">${getLang('modal_cancel')}</button>
                    <button class="confirmation-modal-btn confirm">${getLang('modal_mute_user_confirm')}</button>
                </div>
            </div>
        `;

        const closeModal = () => modal.remove();

        modal.querySelector('.cancel').addEventListener('click', closeModal);
        modal.querySelector('.confirm').addEventListener('click', () => {
            const selectedDuration = modal.querySelector('#mute-duration-select').value;
            onConfirm(selectedDuration);
            closeModal();
        });
        document.body.appendChild(modal);
    }

    window.showDownloadSelectionModal = function(mediaFiles) {
        const existingModal = document.querySelector('.download-modal-backdrop');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.className = 'download-modal-backdrop';
        modal.innerHTML = `
            <div class="download-modal-content">
                <div class="download-modal-header">
                    <h3>${getLang('modal_download_title')}</h3>
                    <div class="select-all-container">
                        <input type="checkbox" id="download-select-all">
                        <label for="download-select-all">${getLang('select_all')}</label>
                    </div>
                    <button class="download-modal-close">&times;</button>
                </div>
                <div class="download-grid"></div>
                <div class="download-modal-actions">
                    <button id="confirm-download-btn" disabled>${getLang('download_selected')}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const grid = modal.querySelector('.download-grid');
        const downloadBtn = modal.querySelector('#confirm-download-btn');
        const selectAllCheckbox = modal.querySelector('#download-select-all');

        mediaFiles.forEach(media => {
            const item = document.createElement('div');
            item.className = 'download-item';
            item.dataset.url = media.url;
            item.dataset.filename = media.original_name;

            let previewHTML = (media.type === 'image')
                ? `<img src="${media.url}" loading="lazy" alt="${media.original_name}">`
                : `<div class="video-icon"><i class="fas fa-video"></i></div>`;

            item.innerHTML = `
                ${previewHTML}
                <div class="checkbox"><i class="fas fa-check"></i></div>
                <div class="download-item-name">${media.original_name}</div>
            `;
            grid.appendChild(item);
        });

        const updateTotal = () => {
            const selectedCount = grid.querySelectorAll('.download-item.selected').length;
            downloadBtn.disabled = selectedCount === 0;
            downloadBtn.textContent = selectedCount > 0 
                ? getLang('download_selected_count', {count: selectedCount}) 
                : getLang('download_selected');
        };

        grid.addEventListener('click', e => {
            const item = e.target.closest('.download-item');
            if (item) {
                item.classList.toggle('selected');
                selectAllCheckbox.checked = grid.querySelectorAll('.download-item:not(.selected)').length === 0;
                updateTotal();
            }
        });

        selectAllCheckbox.addEventListener('change', () => {
            grid.querySelectorAll('.download-item').forEach(item => {
                item.classList.toggle('selected', selectAllCheckbox.checked);
            });
            updateTotal();
        });

        const closeModal = () => modal.remove();
        modal.querySelector('.download-modal-close').addEventListener('click', closeModal);
        modal.addEventListener('click', e => {
            if (e.target === modal) closeModal();
        });

        downloadBtn.addEventListener('click', () => {
            const selectedItems = grid.querySelectorAll('.download-item.selected');
            selectedItems.forEach((item, index) => {
                setTimeout(() => {
                    const link = document.createElement('a');
                    link.href = item.dataset.url;
                    link.setAttribute('download', item.dataset.filename);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }, index * 300);
            });
            if (selectedItems.length > 0) {
                window.showToastNotification(getLang('files_downloading', {count: selectedItems.length}), 'success');
            }
            closeModal();
        });
    }

    function renderComment(comment, currentUserId, currentUserRole) {
        const isOwner = comment.author.id == currentUserId;
        const isKurucu = currentUserRole === 'kurucu';
        const showActions = isOwner || isKurucu;

        let actionsHTML = '';
        if (showActions) {
            actionsHTML = `
                <div class="comment-actions" style="display: none;">
                    ${isOwner || isKurucu ? `<button class="comment-delete-btn" data-comment-id="${comment.id}" title="${getLang('tooltip_delete')}"><i class="fas fa-trash"></i></button>` : ''}
                    ${isKurucu && !isOwner ? `<button class="comment-mute-btn" data-comment-id="${comment.id}" data-user-id="${comment.author.id}" title="${getLang('tooltip_mute_user')}"><i class="fas fa-volume-mute"></i></button>` : ''}
                </div>
            `;
        }

        return `
            <div class="comment" id="comment-${comment.id}" data-comment-id="${comment.id}" data-author-id="${comment.author.id}">
                ${actionsHTML}
                <img src="${comment.author.profile_pic}" alt="${comment.author.username}" class="comment-author-pic">
                <div class="comment-bubble">
                    <span class="comment-author-name">${comment.author.username}</span>
                    <p class="comment-content">${comment.content.replace(/\n/g, '<br>')}</p>
                </div>
            </div>
        `;
    }

    window.renderPost = function(post) {
        const postCard = document.createElement('div');
        postCard.className = 'post-card' + (post.pinned ? ' pinned' : '');
        postCard.dataset.postId = post.id;
        postCard.dataset.authorId = post.author.id;
        if (post.pinned_by_user_id) postCard.dataset.pinnedByUserId = post.pinned_by_user_id;

        const images = post.media_files.filter(f => f.type === 'image');
        const videos = post.media_files.filter(f => f.type === 'video');
        const audios = post.media_files.filter(f => f.type === 'audio');
        const documents = post.media_files.filter(f => f.type === 'document');
        postCard.dataset.hasImage = images.length > 0;
        postCard.dataset.imageUrl = images.length > 0 ? images[0].url : '';
        postCard.dataset.hasVideo = videos.length > 0;
        postCard.dataset.videoThumbUrl = videos.length > 0 ? (videos[0].thumbnail_url || '') : '';
        postCard.dataset.hasAudio = audios.length > 0;
        postCard.dataset.hasDocument = documents.length > 0;

        const hasExternalContent = images.length > 0 || videos.length > 0 || audios.length > 0 || documents.length > 0;

        let mediaHTML = '';

        const visualMedia = images.concat(videos);
        if (visualMedia.length > 0) {
            mediaHTML += `<div class="post-media-container" data-post-id="${post.id}"><div class="media-slider" data-current-index="0">`;
            visualMedia.forEach(media => {
                mediaHTML += `<div class="media-item" data-url="${media.url}" data-filename="${media.original_name}" data-type="${media.type}">`;
                if (media.type === 'image') {
                    mediaHTML += `<img src="${media.url}" alt="${getLang('alt_post_image')}" loading="lazy">`;
                } else if (media.type === 'video') {
                    const poster = media.thumbnail_url || '';
                    mediaHTML += `
                        <a href="#" class="video-thumbnail-container" data-video-url="${media.url}">
                            <img src="${poster}" alt="${getLang('alt_video_thumbnail')}" loading="lazy">
                            <div class="video-play-button"></div>
                        </a>
                    `;
                }
                mediaHTML += `</div>`;
            });
            mediaHTML += `</div>`;

            if (visualMedia.length > 1) {
                mediaHTML += `<button class="slider-nav prev" disabled>&lt;</button><button class="slider-nav next">&gt;</button><span class="slider-counter">1 / ${visualMedia.length}</span>`;
            }
            mediaHTML += `</div>`;
        }

        if (audios.length > 0) {
            mediaHTML += `<div class="post-audio-container">`;
            audios.forEach(audio => {
                mediaHTML += `<audio class="post-audio-player" src="${audio.url}" controls preload="none"></audio>`;
            });
            mediaHTML += `</div>`;
        }

        if (documents.length > 0) {
            mediaHTML += `<div class="post-document-container">`;
            documents.forEach(doc => {
                mediaHTML += `
                    <div class="post-document-attachment" data-url="${doc.url}" data-filename="${doc.original_name}">
                        <i class="fas fa-file-archive"></i>
                        <div class="doc-info">
                            <span class="doc-name">${doc.original_name}</span>
                            <span class="doc-action">${getLang('doc_click_to_download')}</span>
                        </div>
                    </div>`;
            });
            mediaHTML += `</div>`;
        }

        let rawContent = post.content.trim();

        const replyRegex = /\[reply id="(\d+)" user="([^"]+)"\]([\s\S]*?)\[\/reply\]/;
        const replyMatch = rawContent.match(replyRegex);
        const replyTag = replyMatch ? replyMatch[0] : '';
        const editableText = rawContent.replace(replyRegex, '').trim();
        postCard.dataset.replyTag = replyTag;

        rawContent = parseReplyTags(rawContent);

        let contentHTML = rawContent.replace(/\n/g, '<br>');
        function linkifyHTMLContent(html) {
            const container = document.createElement('div');
            container.innerHTML = html;
            const urlPattern = /(https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:\/[^\s]*)?)/g;

            const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
            const nodesToProcess = [];
            while (walker.nextNode()) nodesToProcess.push(walker.currentNode);

            nodesToProcess.forEach(textNode => {
                const text = textNode.nodeValue;
                if (!text || !urlPattern.test(text)) return;
                const frag = document.createDocumentFragment();
                let lastIndex = 0;
                text.replace(urlPattern, (match, _p1, offset) => {
                    if (offset > lastIndex) {
                        frag.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
                    }
                    let url = match;
                    if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
                    const a = document.createElement('a');
                    a.href = url;
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';
                    a.textContent = match;
                    frag.appendChild(a);
                    lastIndex = offset + match.length;
                    return match;
                });
                if (lastIndex < text.length) {
                    frag.appendChild(document.createTextNode(text.slice(lastIndex)));
                }
                textNode.parentNode.replaceChild(frag, textNode);
            });
            return container.innerHTML;
        }
        contentHTML = linkifyHTMLContent(contentHTML);

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = contentHTML;
        const textContent = tempDiv.textContent || tempDiv.innerText || '';
        const words = textContent.split(/\s+/);
        const wordLimit = 30;

        if (words.length > wordLimit) {
            const visibleText = getTruncatedHTML(contentHTML, wordLimit);
            const remainder = contentHTML.substring(visibleText.length);
            const hiddenText = remainder.replace(/^(\s*<br\s*\/?\s*>)+/i, '');
            contentHTML = `<span class="visible-text">${visibleText}</span><span class="hidden-text" style="display:none;">${hiddenText}</span><span class="read-more-toggle">${getLang('read_more')}</span>`;
        }

        let optionsHTML = '';
        const currentUserId = document.body.dataset.userId;
        const isOwner = post.author.id == currentUserId;
        const userRole = document.body.dataset.userRole;
        const isKurucu = userRole === 'kurucu';
        const canPin = ['premium','dev','kurucu','caylak_admin','usta_admin'].includes(userRole);
        const isPinnedByOther = post.pinned && post.pinned_by_user_id && String(post.pinned_by_user_id) !== String(currentUserId);

        if ((isOwner || isKurucu || canPin || hasExternalContent) && !(isPinnedByOther && !hasExternalContent)) {
            optionsHTML = `<div class="post-options"><button class="post-options-btn"><i class="fas fa-ellipsis-h"></i></button><div class="options-dropdown">`;

            if (isOwner) {
                optionsHTML += `<button class="dropdown-edit-btn">${getLang('post_edit')}</button>`;
            }

            if (isOwner || isKurucu) {
                optionsHTML += `<button class="dropdown-delete-btn">${getLang('post_delete')}</button>`;
            }

            if (isKurucu && !isOwner) {
                optionsHTML += `<button class="dropdown-mute-btn">${getLang('post_mute_user')}</button>`;
            }

            if (canPin && !isPinnedByOther) {
                if (post.pinned) {
                    const canUnpin = isKurucu || (post.pinned_by_user_id && String(post.pinned_by_user_id) === String(currentUserId));
                    if (canUnpin) {
                        optionsHTML += `<button class="dropdown-unpin-btn">${getLang('post_unpin') || 'Unpin'}</button>`;
                    }
                } else {
                    optionsHTML += `<button class="dropdown-pin-btn">${getLang('post_pin') || 'Pin to Top'}</button>`;
                }
            }

            if (hasExternalContent) {
                optionsHTML += `<button class="dropdown-download-btn">${getLang('post_download')}</button>`;
            }

            optionsHTML += `</div></div>`;
        }

        const likedClass = post.current_user_liked ? 'liked' : '';
        const likeIconClass = post.current_user_liked ? 'fas' : 'far';
        const likeText = post.current_user_liked ? getLang('action_liked') : getLang('action_like');
        const postUrl = `${window.location.origin}/forum/view/post/${post.id}`;
        const editedIndicator = post.edited_at ? `<span class="post-edited-indicator">(${getLang('post_edited')})</span>` : '';
        const roleClass = getRoleClass(post.author.role);

        let likesStatHTML = '';
        if (post.likes_count === 0) {
            likesStatHTML = `<span>${getLang('be_first_to_like')}</span>`;
        } else if (post.likes_count === 1) {
            likesStatHTML = `<span class="view-likers" data-post-id="${post.id}">${getLang('user_liked_this', {username: post.first_liker_name})}</span>`;
        } else {
            likesStatHTML = `<span class="view-likers" data-post-id="${post.id}">${getLang('users_liked_this', {username: post.first_liker_name, count: post.likes_count - 1})}</span>`;
        }

        postCard.innerHTML = `
            <div class="post-header">
                <img src="${post.author.profile_pic}" alt="${post.author.username}" class="post-author-pic">
                <div class="post-author-details">
                    <span class="post-author-name">${post.author.username}</span>
                    <div class="post-timestamp-container">
                        <span class="post-timestamp">${timeAgo(post.timestamp)}</span>${editedIndicator}
                    </div>
                </div>
                <span class="post-author-role ${roleClass}">${post.author.role}</span>
                ${post.pinned ? `<span class="pinned-badge"><i class="fas fa-thumbtack"></i> ${getLang('badge_pinned') || 'Pinned'}</span>` : ''}
                ${optionsHTML}
            </div>
            <div class="post-body">
                <div class="post-content-wrapper">
                    <div class="post-content">${contentHTML}</div>
                    <div class="post-edit-area" style="display: none;">
                        <textarea class="post-edit-textarea">${editableText}</textarea>
                        <div class="edit-actions">
                            <button class="edit-cancel-btn">${getLang('modal_cancel')}</button>
                            <button class="edit-save-btn">${getLang('post_save')}</button>
                        </div>
                    </div>
                </div>
                ${mediaHTML}
            </div>
            <div class="post-stats" id="stats-container-${post.id}">
                ${likesStatHTML}
                <span id="comments-count-${post.id}" class="comments-count">${getLang('comment_count', {count: post.comments_count})}</span>
            </div>
            <div class="post-actions">
                <button class="action-button like-button ${likedClass}" data-post-id="${post.id}">
                    <i class="${likeIconClass} fa-thumbs-up"></i> 
                    <span class="like-text">${likeText}</span>
                </button>
                <button class="action-button comment-button" data-post-id="${post.id}">
                    <i class="far fa-comment"></i> ${getLang('action_comment')}
                </button>
                <button class="action-button share-button" data-url="${postUrl}">
                    <i class="far fa-share-square"></i> ${getLang('action_share')}
                </button>
            </div>
            <div class="comments-section" id="comments-section-${post.id}" style="display: none;">
                <div class="comment-list" id="comment-list-${post.id}"></div>
                <form class="comment-form" data-post-id="${post.id}">
                    <input type="text" class="comment-input" placeholder="${getLang('comment_placeholder')}" required maxlength="${MAX_COMMENT_LENGTH}">
                    <button type="submit" class="comment-submit-btn">${getLang('comment_submit')}</button>
                </form>
            </div>
        `;
        const mediaContainerEl = postCard.querySelector('.post-media-container');
        if (mediaContainerEl) {
            const slider = mediaContainerEl.querySelector('.media-slider');
            if (slider) {
                let startX = 0;
                let deltaX = 0;
                let isDown = false;
                let baseIndex = 0;
                let width = 0;
                function begin(x) {
                    isDown = true;
                    startX = x;
                    baseIndex = parseInt(slider.dataset.currentIndex) || 0;
                    width = slider.clientWidth;
                    slider.style.transition = 'none';
                }
                function move(x) {
                    if (!isDown) return;
                    deltaX = x - startX;
                    const total = slider.children.length;
                    const lastIndex = total - 1;
                    if (baseIndex === 0 && deltaX > 0) deltaX = 0;
                    if (baseIndex === lastIndex && deltaX < 0) deltaX = 0;
                    const percent = (-baseIndex * 100) + (deltaX / width * 100);
                    slider.style.transform = `translateX(${percent}%)`;
                }
                function end() {
                    if (!isDown) return;
                    isDown = false;
                    slider.style.transition = '';
                    const total = slider.children.length;
                    let next = baseIndex;
                    const th = Math.max(40, width * 0.18);
                    if (deltaX < -th) next = baseIndex + 1;
                    if (deltaX > th) next = baseIndex - 1;
                    if (next < 0) next = 0;
                    if (next > total - 1) next = total - 1;
                    slider.dataset.currentIndex = next;
                    slider.style.transform = `translateX(-${next * 100}%)`;
                    const prevBtn = mediaContainerEl.querySelector('.prev');
                    const nextBtn = mediaContainerEl.querySelector('.next');
                    const counter = mediaContainerEl.querySelector('.slider-counter');
                    if (prevBtn) prevBtn.disabled = (next === 0);
                    if (nextBtn) nextBtn.disabled = (next === total - 1);
                    if (counter) counter.textContent = `${next + 1} / ${total}`;
                    deltaX = 0;
                }
                slider.addEventListener('touchstart', e => begin(e.touches[0].clientX), { passive: true });
                slider.addEventListener('touchmove', e => move(e.touches[0].clientX), { passive: true });
                slider.addEventListener('touchend', () => end());
                slider.addEventListener('mousedown', e => begin(e.clientX));
                slider.addEventListener('mousemove', e => move(e.clientX));
                slider.addEventListener('mouseup', () => end());
                slider.addEventListener('mouseleave', () => end());
            }
        }
        return postCard;
    }

// [reply] etiketini HTML'e çeviren ayrıştırıcı (BOŞLUKSUZ VERSİYON)
    function parseReplyTags(text) {
        // Regex supports optional media and thumb attributes
        // [reply id="123" user="ahmet" media="image" thumb="/url"]Mesaj[/reply]
        const regex = /\[reply id="(\d+)" user="([^"]+)"(?:\s+media="([^"]+)")?(?:\s+thumb="([^"]+)")?\](.*?)\[\/reply\]/g;
        return text.replace(regex, (match, id, user, media, thumb, content) => {
            let thumbHTML = '';
            if (media === 'image' && thumb) {
                thumbHTML = `<div class="post-quote-thumb"><img src="${thumb}" alt="${getLang('alt_post_image') || 'image'}" class="quote-thumb-image"></div>`;
            } else if (media === 'video') {
                thumbHTML = `<div class="post-quote-thumb"><i class="fas fa-video quote-thumb-icon"></i></div>`;
            } else if (media === 'audio') {
                thumbHTML = `<div class="post-quote-thumb"><i class="fas fa-music quote-thumb-icon"></i></div>`;
            } else if (media === 'document') {
                thumbHTML = `<div class="post-quote-thumb"><i class="fas fa-file-alt quote-thumb-icon"></i></div>`;
            }
            return `<div class="post-quote" data-quote-id="${id}"><div class="post-quote-header"><i class="fas fa-reply"></i><span class="quote-username">${user}</span></div>${thumbHTML}<div class="post-quote-content">${content}</div></div>`;
        });
    }

    function getTruncatedHTML(html, wordLimit) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        let wordCount = 0;
        let result = '';
        
        function traverseNodes(node) {
            for (const child of node.childNodes) {
                if (wordCount >= wordLimit) break;
                
                if (child.nodeType === Node.TEXT_NODE) {
                    const words = child.textContent.split(/\s+/);
                    for (const word of words) {
                        if (wordCount >= wordLimit) break;
                        if (word.trim()) {
                            result += (result.endsWith(' ') || result === '' ? '' : ' ') + word;
                            wordCount++;
                        }
                    }
                } else {
                    const tagName = child.tagName.toLowerCase();
                    const outerHTML = child.outerHTML;
                    const innerStart = outerHTML.indexOf('>') + 1;
                    const innerEnd = outerHTML.lastIndexOf('<');
                    const tagStart = outerHTML.substring(0, innerStart);
                    const tagEnd = outerHTML.substring(innerEnd);
                    
                    result += tagStart;
                    traverseNodes(child);
                    if (wordCount < wordLimit) {
                        result += tagEnd;
                    }
                }
            }
        }
        
        traverseNodes(tempDiv);
        return result;
    }

    window.scrollToPost = function(postId) {
        const targetPost = document.querySelector(`.post-card[data-post-id="${postId}"]`);

        if (targetPost) {
            targetPost.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            targetPost.classList.add('highlight-flash');
            setTimeout(() => {
                targetPost.classList.remove('highlight-flash');
            }, 1500);
        } else {
            window.showToastNotification(getLang('post_scroll_not_found') || 'Gönderi bulunamadı veya silinmiş olabilir.', 'error');
        }
    };

    function timeAgo(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        let interval = seconds / 31536000;
        
        if (interval > 1) {
            const count = Math.floor(interval);
            return getLang(count === 1 ? 'time_ago_year_singular' : 'time_ago_year_plural', {count});
        }
        interval = seconds / 2592000;
        if (interval > 1) {
            const count = Math.floor(interval);
            return getLang(count === 1 ? 'time_ago_month_singular' : 'time_ago_month_plural', {count});
        }
        interval = seconds / 86400;
        if (interval > 1) {
            const count = Math.floor(interval);
            return getLang(count === 1 ? 'time_ago_day_singular' : 'time_ago_day_plural', {count});
        }
        interval = seconds / 3600;
        if (interval > 1) {
            const count = Math.floor(interval);
            return getLang(count === 1 ? 'time_ago_hour_singular' : 'time_ago_hour_plural', {count});
        }
        interval = seconds / 60;
        if (interval > 1) {
            const count = Math.floor(interval);
            return getLang(count === 1 ? 'time_ago_minute_singular' : 'time_ago_minute_plural', {count});
        }
        return getLang('time_ago_now');
    }

    function getRoleClass(role) {
        const roleMap = { 'premium': 'role-premium', 'dev': 'role-dev', 'ücretsiz': 'role-ücretsiz', 'kurucu': 'role-kurucu', 'usta_admin': 'role-usta_admin', 'caylak_admin': 'role-caylak_admin' };
        return roleMap[role] || 'role-ücretsiz';
    }

    postFeedContainer.addEventListener('click', async (e) => {
        const target = e.target;

        const commentElement = target.closest('.comment');
        if (commentElement) {
            const actions = commentElement.querySelector('.comment-actions');
            if (actions) {
                document.querySelectorAll('.comment-actions').forEach(action => {
                    if (action !== actions) action.style.display = 'none';
                });
                actions.style.display = actions.style.display === 'flex' ? 'none' : 'flex';
            }
        }

        const commentDeleteBtn = target.closest('.comment-delete-btn');
        if (commentDeleteBtn) {
            const commentId = commentDeleteBtn.dataset.commentId;
            handleDeleteComment(commentId, commentDeleteBtn);
            return;
        }

        const commentMuteBtn = target.closest('.comment-mute-btn');
        if (commentMuteBtn) {
            const commentId = commentMuteBtn.dataset.commentId;
            const userId = commentMuteBtn.dataset.userId;
            handleMuteCommentAuthor(commentId, userId, commentMuteBtn);
            return;
        }

        const postCard = target.closest('.post-card');
        if (!postCard) return;

        const postId = postCard.dataset.postId;

        const likeButton = target.closest('.like-button');
        if (likeButton) return handleLikePost(postId, likeButton);

        const commentButton = target.closest('.comment-button');
        if (commentButton) return handleToggleComments(postId);

        const shareButton = target.closest('.share-button');
        if(shareButton) return handleSharePost(shareButton.dataset.url);

        const videoThumbnail = target.closest('.video-thumbnail-container');
        if(videoThumbnail) {
            e.preventDefault();
            handleVideoPlay(videoThumbnail);
            return;
        }

        const optionsButton = target.closest('.post-options-btn');
        if (optionsButton) {
            const dropdown = optionsButton.nextElementSibling;
            document.querySelectorAll('.options-dropdown').forEach(d => {
                if (d !== dropdown) d.style.display = 'none';
            });
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
            return;
        }


        const viewLikersBtn = target.closest('.view-likers');
        if (viewLikersBtn) return await handleViewLikers(postId);

        const deleteButton = target.closest('.dropdown-delete-btn');
        if(deleteButton) return handleDeletePost(postId, deleteButton);

        const pinButton = target.closest('.dropdown-pin-btn');
        if (pinButton) {
            fetch(`/forum/posts/${postId}/pin`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken() }})
                .then(r => r.json())
                .then(result => {
                    if (result.success) {
                        const card = document.querySelector(`.post-card[data-post-id="${postId}"]`);
                        if (card) {
                            card.classList.add('pinned');
                            card.dataset.pinnedByUserId = String(document.body.dataset.userId);
                            const header = card.querySelector('.post-header');
                            if (header && !card.querySelector('.pinned-badge')) {
                                const badge = document.createElement('span');
                                badge.className = 'pinned-badge';
                                badge.innerHTML = `<i class="fas fa-thumbtack"></i> ${getLang('badge_pinned') || 'Pinned'}`;
                                header.appendChild(badge);
                            }
                            const container = card.parentElement;
                            if (container) container.prepend(card);
                            const dropdown = card.querySelector('.options-dropdown');
                            if (dropdown) {
                                const pinBtn = dropdown.querySelector('.dropdown-pin-btn');
                                const currentUserId = document.body.dataset.userId;
                                const isKurucu = document.body.dataset.userRole === 'kurucu';
                                if (pinBtn) pinBtn.remove();
                                if (isKurucu || String(currentUserId) === String(card.dataset.pinnedByUserId)) {
                                    const unpin = document.createElement('button');
                                    unpin.className = 'dropdown-unpin-btn';
                                    unpin.textContent = getLang('post_unpin') || 'Unpin';
                                    dropdown.appendChild(unpin);
                                }
                            }
                        }
                        window.showToastNotification(getLang('post_pinned') || 'Pinned', 'success');
                        document.dispatchEvent(new Event('languageChanged'));
                    } else {
                        window.showToastNotification(getLang(result.error_key) || 'Error', 'error');
                    }
                });
            return;
        }

        const unpinButton = target.closest('.dropdown-unpin-btn');
        if (unpinButton) {
            fetch(`/forum/posts/${postId}/unpin`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken() }})
                .then(r => r.json())
                .then(result => {
                    if (result.success) {
                        const card = document.querySelector(`.post-card[data-post-id="${postId}"]`);
                        if (card) {
                            card.classList.remove('pinned');
                            const badge = card.querySelector('.pinned-badge');
                            if (badge) badge.remove();
                            delete card.dataset.pinnedByUserId;
                            const dropdown = card.querySelector('.options-dropdown');
                            if (dropdown) {
                                const unpinBtn = dropdown.querySelector('.dropdown-unpin-btn');
                                if (unpinBtn) unpinBtn.remove();
                                const canPin = ['premium','dev','kurucu','caylak_admin','usta_admin'].includes(document.body.dataset.userRole);
                                if (canPin) {
                                    const pin = document.createElement('button');
                                    pin.className = 'dropdown-pin-btn';
                                    pin.textContent = getLang('post_pin') || 'Pin to Top';
                                    dropdown.appendChild(pin);
                                }
                            }
                        }
                        window.showToastNotification(getLang('post_unpinned') || 'Unpinned', 'success');
                        document.dispatchEvent(new Event('languageChanged'));
                    } else {
                        window.showToastNotification(getLang(result.error_key) || 'Error', 'error');
                    }
                });
            return;
        }

        const muteButton = target.closest('.dropdown-mute-btn');
        if(muteButton) return handleMuteAuthor(postCard, muteButton);

        const editButton = target.closest('.dropdown-edit-btn');
        if(editButton) return handleToggleEdit(postCard, editButton);

        const downloadButton = target.closest('.dropdown-download-btn');
        if(downloadButton) return handleDownload(postCard, downloadButton);

        const cancelEditButton = target.closest('.edit-cancel-btn');
        if(cancelEditButton) return handleToggleEdit(postCard);

        const saveEditButton = target.closest('.edit-save-btn');
        if(saveEditButton) return handleEditPost(postId, postCard);

        const readMoreToggle = target.closest('.read-more-toggle');
        if(readMoreToggle) return handleReadMore(readMoreToggle);

        const navButton = target.closest('.slider-nav');
        if(navButton) return handleSlider(navButton);

        

        const documentAttachment = target.closest('.post-document-attachment');
        if(documentAttachment) return handleDocumentDownload(documentAttachment);

        const mediaImage = target.closest('.media-item img');

        if(mediaImage) {
            const clickedItem = mediaImage.closest('.media-item');
            const postCard = clickedItem.closest('.post-card');
            const allImageItems = Array.from(postCard.querySelectorAll('.media-item[data-type="image"]'));

            const galleryItems = allImageItems.map(item => ({
                url: item.dataset.url
            }));

            const startIndex = allImageItems.findIndex(item => item === clickedItem);

            showImageViewer(galleryItems, startIndex);
            return;
        }
    });

    async function handleDeleteComment(commentId, button) {
        window.showConfirmationModal(
            getLang('modal_delete_comment_title'), 
            getLang('modal_delete_comment_message'), 
            async () => {
                try {
                    const response = await fetch(`/forum/comments/${commentId}/delete`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': window.getCSRFToken() }
                    });
                    const result = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(result.error_key || 'comment_delete_error');
                    }

                    const commentElement = document.getElementById(`comment-${commentId}`);
                    if (commentElement) {
                        commentElement.style.animation = 'fadeOut 0.3s forwards';
                        setTimeout(() => commentElement.remove(), 300);
                    }

                    const postId = commentElement.closest('.comments-section').dataset.postId;
                    const commentsCountSpan = document.getElementById(`comments-count-${postId}`);
                    if (commentsCountSpan && result.comments_count !== undefined) {
                        commentsCountSpan.textContent = getLang('comment_count', {count: result.comments_count});
                    }

                    window.showToastNotification(getLang(result.message_key), 'success');
                } catch (error) {
                    window.showToastNotification(getLang(error.message), 'error');
                }
            }
        );
    }

    async function handleMuteCommentAuthor(commentId, userId, button) {
        showFounderPasswordModal(
            getLang('modal_founder_verify_title'),
            getLang('modal_founder_mute_message'),
            password => {
                showMuteDurationModal(async selectedDuration => {
                    try {
                        const response = await fetch(`/forum/comments/${commentId}/mute_author`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCSRFToken()
                            },
                            body: JSON.stringify({
                                password: password,
                                duration: selectedDuration
                            })
                        });
                        const result = await response.json();
                        
                        if (!response.ok) {
                            throw new Error(result.error_key || 'mute_server_error');
                        }
                        
                        window.showToastNotification(getLang(result.message_key), 'success');
                    } catch (error) {
                        window.showToastNotification(getLang(error.message), 'error');
                    }
                });
            }
        );
    }

    postFeedContainer.addEventListener('input', (e) => {
        if (e.target.matches('.comment-input')) {
            const input = e.target;
            const currentLength = input.value.length;

            if (currentLength > MAX_COMMENT_LENGTH) {
                input.style.borderColor = '#e74c3c';
            } else {
                input.style.borderColor = '';
            }
        }
    });

    postFeedContainer.addEventListener('submit', (e) => {
        if (e.target.matches('.comment-form')) {
            e.preventDefault();
            const form = e.target;
            const postId = form.dataset.postId;
            const input = form.querySelector('.comment-input');
            const content = input.value.trim();

            if (content) {
                handleAddComment(postId, content, form);
            }
        }
    });

    async function handleLikePost(postId, likeButton) {
        try {
            const response = await fetch(`/forum/posts/${postId}/like`, {
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCSRFToken() }
            });
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error_key || 'like_error');
            }

            const icon = likeButton.querySelector('i');
            const likeText = likeButton.querySelector('.like-text');
            const statsContainer = document.getElementById(`stats-container-${postId}`);

            likeButton.classList.toggle('liked', result.user_liked);
            icon.className = result.user_liked ? 'fas fa-thumbs-up' : 'far fa-thumbs-up';
            likeText.textContent = result.user_liked ? getLang('action_liked') : getLang('action_like');

            let newLikesHTML;
            if (result.likes_count === 0) newLikesHTML = `<span>${getLang('be_first_to_like')}</span>`;
            else if (result.likes_count === 1) newLikesHTML = `<span class="view-likers" data-post-id="${postId}">${getLang('user_liked_this', {username: result.first_liker_name})}</span>`;
            else newLikesHTML = `<span class="view-likers" data-post-id="${postId}">${getLang('users_liked_this', {username: result.first_liker_name, count: result.likes_count - 1})}</span>`;

            const firstStatElement = statsContainer.querySelector('.view-likers, span:first-child');
            if(firstStatElement) firstStatElement.outerHTML = newLikesHTML;

        } catch (error) {
            window.showToastNotification(getLang(error.message), 'error');
        }
    }

    async function handleToggleComments(postId) {
        if (document.body.dataset.isMuted === 'true') {
            window.showToastNotification(getLang('cannot_comment_while_muted'), 'error');
            return;
        }

        const commentsSection = document.getElementById(`comments-section-${postId}`);
        const commentList = document.getElementById(`comment-list-${postId}`);

        if (commentsSection.style.display === 'none') {
            try {
                const response = await fetch(`/forum/posts/${postId}/comments`);
                if (!response.ok) throw new Error(getLang('comment_load_error'));

                const comments = await response.json();
                const currentUserId = document.body.dataset.userId;
                const currentUserRole = document.body.dataset.userRole;

                commentList.innerHTML = comments.length > 0
                    ? comments.map(comment => renderComment(comment, currentUserId, currentUserRole)).join('')
                    : `<p class="no-comments">${getLang('no_comments_yet')}</p>`;

                commentsSection.style.display = 'block';

                const commentInput = commentList.nextElementSibling?.querySelector('input');
                if (commentInput) {
                    commentInput.focus();
                }
            } catch (error) {
                window.showToastNotification(error.message, 'error');
            }
        } else {
            commentsSection.style.display = 'none';

            document.querySelectorAll('.comment-actions').forEach(action => {
                action.style.display = 'none';
            });
        }
    }

    async function handleAddComment(postId, content, form) {
        if (document.body.dataset.isMuted === 'true') {
            window.showToastNotification(getLang('cannot_comment_while_muted'), 'error');
            return;
        }

        const input = form.querySelector('.comment-input');
        const submitBtn = form.querySelector('button[type="submit"]');
        input.disabled = true;
        submitBtn.disabled = true;

        try {
            const response = await fetch(`/forum/posts/${postId}/comment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.getCSRFToken() },
                body: JSON.stringify({ content })
            });
            const result = await response.json();

            if (!response.ok) {
                if (result.error_key === 'comment_limit_reached') {
                    window.showToastNotification(getLang(result.error_key, { limit: result.limit }), 'error');
                } else {
                    throw new Error(result.error_key || 'comment_create_error');
                }
                return;
            }

            const commentList = document.getElementById(`comment-list-${postId}`);
            commentList.querySelector('.no-comments')?.remove();
            const currentUserId = document.body.dataset.userId;
            const currentUserRole = document.body.dataset.userRole;
            commentList.insertAdjacentHTML('beforeend', renderComment(result.comment, currentUserId, currentUserRole));
            input.value = '';

            const commentsCountSpan = document.getElementById(`comments-count-${postId}`);
            commentsCountSpan.textContent = getLang('comment_count', {count: result.comments_count});
            commentList.scrollTop = commentList.scrollHeight;

            if (result.user_comment_count) {
            }

        } catch (error) {
            if (error.message !== 'comment_limit_reached') {
                 window.showToastNotification(getLang(error.message), 'error');
            }
        } finally {
            input.disabled = false;
            submitBtn.disabled = false;
        }
    }

    async function handleSharePost(url) {
        try {
            if (navigator.share) {
                await navigator.share({ title: getLang('share_post_title'), url });
            } else {
                await navigator.clipboard.writeText(url);
                window.showToastNotification(getLang('link_copied_to_clipboard'), 'success');
            }
        } catch (error) {
            if (error.name !== 'AbortError') window.showToastNotification(getLang('share_failed'), 'error');
        }
    }

    async function handleDeletePost(postId, button) {
        if (document.body.dataset.isMuted === 'true') {
            window.showToastNotification(getLang('cannot_delete_while_muted'), 'error');
            return;
        }

        button.closest('.options-dropdown').style.display = 'none';

        const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
        if (!postCard) return;

        const currentUserId = document.body.dataset.userId;
        const isKurucu = document.body.dataset.userRole === 'kurucu';

        if (isKurucu) {
            showFounderPasswordModal(
                getLang('modal_founder_verify_title'),
                getLang('modal_founder_delete_post_message'),
                async (password) => {
                    try {
                        const response = await fetch(`/forum/posts/${postId}/delete`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCSRFToken()
                            },
                            body: JSON.stringify({ password: password })
                        });
                        const result = await response.json();
                        
                        if (!response.ok) {
                            throw new Error(result.error_key || 'post_delete_error');
                        }

                        postCard.style.animation = 'fadeOut 0.3s forwards';
                        setTimeout(() => postCard.remove(), 300);
                        
                        window.showToastNotification(getLang(result.message_key), 'success');
                    } catch (error) {
                        window.showToastNotification(getLang(error.message), 'error');
                    }
                }
            );
        }
        else {
            window.showConfirmationModal(
                getLang('modal_delete_post_title'), 
                getLang('modal_delete_post_message'), 
                async () => {
                    try {
                        const response = await fetch(`/forum/posts/${postId}/delete`, {
                            method: 'POST',
                            headers: { 'X-CSRFToken': window.getCSRFToken() }
                        });
                        const result = await response.json();
                        
                        if (!response.ok) {
                            throw new Error(result.error_key || 'post_delete_error');
                        }

                        postCard.style.animation = 'fadeOut 0.3s forwards';
                        setTimeout(() => postCard.remove(), 300);
                        
                        window.showToastNotification(getLang(result.message_key), 'success');
                    } catch (error) {
                        window.showToastNotification(getLang(error.message), 'error');
                    }
                }
            );
        }
    }

    async function handleMuteAuthor(postCard, button) {
        button.closest('.options-dropdown').style.display = 'none';

        const userIdToMute = postCard.dataset.authorId;
        if (!userIdToMute) {
            window.showToastNotification(getLang('mute_user_id_not_found'), 'error');
            return;
        }

        showFounderPasswordModal(
            getLang('modal_founder_verify_title'),
            getLang('modal_founder_mute_message'),
            password => {
                showMuteDurationModal(async selectedDuration => {
                    try {
                        const response = await fetch(`/forum/users/${userIdToMute}/mute`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCSRFToken()
                            },
                            body: JSON.stringify({
                                password: password,
                                duration: selectedDuration
                            })
                        });
                        const result = await response.json();
                        
                        if (!response.ok) {
                            throw new Error(result.error_key || 'mute_server_error');
                        }
                        
                        window.showToastNotification(getLang(result.message_key), 'success');
                    } catch (error) {
                        window.showToastNotification(getLang(error.message), 'error');
                    }
                });
            }
        );
    }

    function handleToggleEdit(postCard, button = null) {
        if (document.body.dataset.isMuted === 'true') {
            window.showToastNotification(getLang('cannot_edit_while_muted'), 'error');
            return;
        }

        if(button) button.closest('.options-dropdown').style.display = 'none';

        const contentWrapper = postCard.querySelector('.post-content-wrapper');
        const contentDiv = contentWrapper.querySelector('.post-content');
        const editArea = contentWrapper.querySelector('.post-edit-area');

        if (editArea.style.display === 'none') {
            contentDiv.style.display = 'none';
            editArea.style.display = 'block';
            editArea.querySelector('textarea').focus();
        } else {
            contentDiv.style.display = 'block';
            editArea.style.display = 'none';
        }
    }

    async function handleEditPost(postId, postCard) {
        const editArea = postCard.querySelector('.post-edit-area');
        const textarea = editArea.querySelector('textarea');
        const newContent = textarea.value.trim();

        if (!newContent) {
            window.showToastNotification(getLang('edit_content_empty'), 'error');
            return;
        }

        try {
            const replyTag = postCard.dataset.replyTag || '';
            const combinedContent = (replyTag ? replyTag + '\n' : '') + newContent;
            const response = await fetch(`/forum/posts/${postId}/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.getCSRFToken() },
                body: JSON.stringify({ content: combinedContent })
            });
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error_key || 'post_edit_error');
            }

            const contentDiv = postCard.querySelector('.post-content');
            const parsedCombined = parseReplyTags(combinedContent).replace(/\n/g, '<br>');
            const tempDivAll = document.createElement('div');
            tempDivAll.innerHTML = parsedCombined;
            const textContentAll = tempDivAll.textContent || tempDivAll.innerText || '';
            const words = textContentAll.split(/\s+/);
            const wordLimit = 30;

            if (words.length > wordLimit) {
                const visibleText = getTruncatedHTML(parsedCombined, wordLimit);
                const remainder = parsedCombined.substring(visibleText.length);
                const hiddenText = remainder.replace(/^(\s*<br\s*\/?\s*>)+/i, '');
                contentDiv.innerHTML = `<span class="visible-text">${visibleText}</span><span class="hidden-text" style="display:none;">${hiddenText}</span><span class="read-more-toggle">${getLang('read_more')}</span>`;
            } else {
                contentDiv.innerHTML = parsedCombined;
            }

            const timestampContainer = postCard.querySelector('.post-timestamp-container');
            if (!timestampContainer.querySelector('.post-edited-indicator')) {
                timestampContainer.innerHTML += `<span class="post-edited-indicator">(${getLang('post_edited')})</span>`;
            }

            handleToggleEdit(postCard);
            
            window.showToastNotification(getLang(result.message_key), 'success');
        } catch (error) {
            window.showToastNotification(getLang(error.message), 'error');
        }
    }

    function handleReadMore(toggle) {
        const hiddenText = toggle.previousElementSibling;
        if (hiddenText) {
            if (hiddenText.style.display === 'none') {
                hiddenText.style.display = 'inline';
                toggle.textContent = getLang('read_less');
            } else {
                hiddenText.style.display = 'none';
                toggle.textContent = getLang('read_more');
            }
        }
    }

    function handleSlider(button) {
        const mediaContainer = button.closest('.post-media-container');
        if (!mediaContainer) {
            console.error("Slider container bulunamadı.");
            return;
        }

        const slider = mediaContainer.querySelector('.media-slider');
        if (!slider) {
            console.error("Slider bulunamadı.");
            return;
        }

        const currentIndex = parseInt(slider.dataset.currentIndex);
        const totalItems = slider.children.length;
        let newIndex;

        if (button.classList.contains('prev')) {
            newIndex = currentIndex - 1;
        } else {
            newIndex = currentIndex + 1;
        }

        if (newIndex < 0 || newIndex >= totalItems) {
            return;
        }

        slider.dataset.currentIndex = newIndex;
        slider.style.transform = `translateX(-${newIndex * 100}%)`;

        const prevBtn = mediaContainer.querySelector('.prev');
        const nextBtn = mediaContainer.querySelector('.next');
        const counter = mediaContainer.querySelector('.slider-counter');

        if (prevBtn) prevBtn.disabled = (newIndex === 0);
        if (nextBtn) nextBtn.disabled = (newIndex === totalItems - 1);
        if (counter) counter.textContent = `${newIndex + 1} / ${totalItems}`;
    }

    async function handleViewLikers(postId) {
        try {
            const response = await fetch(`/forum/posts/${postId}/likers`);
            
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error_key || 'likers_load_error');
            }

            const likers = await response.json();

            document.querySelector('.likers-modal-backdrop')?.remove();

            const modal = document.createElement('div');
            modal.className = 'likers-modal-backdrop';
            modal.innerHTML = `
                <div class="likers-modal-content">
                    <div class="likers-modal-header">
                        <h3>${getLang('modal_likers_title')}</h3>
                        <button class="likers-modal-close">&times;</button>
                    </div>
                    <div class="likers-modal-body">
                        ${likers.length > 0 ? likers.map(liker => `
                            <div class="liker-item">
                                <div class="liker-info">
                                    <img src="${liker.profile_pic}" alt="${liker.username}" class="liker-pic">
                                    <span class="liker-name">${liker.username}</span>
                                </div>
                                <span class="liker-role ${getRoleClass(liker.role)}">${liker.role}</span>
                            </div>
                        `).join('') : `<div class="empty-state"><p>${getLang('no_likes_yet')}</p></div>`}
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            const closeModal = () => {
                modal.classList.add('fade-out');
                setTimeout(() => modal.remove(), 300);
            };

            modal.querySelector('.likers-modal-close').addEventListener('click', closeModal);

            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeModal();
                }
            });

        } catch (error) {
            window.showToastNotification(getLang(error.message), 'error');
        }
    }

    function handleDownload(postCard, button) {
        button.closest('.options-dropdown').style.display = 'none';

        const mediaFiles = [];
        const imageItems = postCard.querySelectorAll('.media-item[data-type="image"]');
        const videoItems = postCard.querySelectorAll('.media-item[data-type="video"]');

        imageItems.forEach(item => {
            mediaFiles.push({
                url: item.dataset.url,
                original_name: item.dataset.filename,
                type: 'image'
            });
        });

        videoItems.forEach(item => {
            mediaFiles.push({
                url: item.dataset.url,
                original_name: item.dataset.filename,
                type: 'video'
            });
        });

        if (mediaFiles.length === 0) {
            window.showToastNotification(getLang('no_media_to_download'), 'error');
            return;
        }

        window.showDownloadSelectionModal(mediaFiles);
    }

    function handleDocumentDownload(documentAttachment) {
        const url = documentAttachment.dataset.url;
        const filename = documentAttachment.dataset.filename;
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function handleVideoPlay(thumbnailContainer) {
        const videoUrl = thumbnailContainer.dataset.videoUrl;
        if (!videoUrl) return;

        const existingPlayer = document.querySelector('.video-player-modal');
        if (existingPlayer) existingPlayer.remove();

        const videoModal = document.createElement('div');
        videoModal.className = 'video-player-modal';
        videoModal.innerHTML = `
            <div class="video-player-content">
                <button class="video-player-close">&times;</button>
                <video controls autoplay>
                    <source src="${videoUrl}" type="video/mp4">
                    ${getLang('video_not_supported')}
                </video>
            </div>
        `;

        document.body.appendChild(videoModal);

        const closeBtn = videoModal.querySelector('.video-player-close');
        const closeVideo = () => {
            const video = videoModal.querySelector('video');
            if (video) {
                video.pause();
                video.currentTime = 0;
            }
            videoModal.remove();
        };

        closeBtn.addEventListener('click', closeVideo);
        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) closeVideo();
        });
    }

    function showImageViewer(items, startIndex) {
        if (!items || items.length === 0) return;

        currentViewerItems = items;
        currentViewerIndex = startIndex;

        if (!document.querySelector('.viewer-nav')) {
            const prevButton = document.createElement('button');
            prevButton.className = 'viewer-nav prev';
            prevButton.innerHTML = '&lt;';
            prevButton.id = 'viewer-prev-btn';

            const nextButton = document.createElement('button');
            nextButton.className = 'viewer-nav next';
            nextButton.innerHTML = '&gt;';
            nextButton.id = 'viewer-next-btn';

            imageViewerModal.appendChild(prevButton);
            imageViewerModal.appendChild(nextButton);

            prevButton.addEventListener('click', (e) => {
                e.stopPropagation();
                navigateViewer(-1);
            });
            nextButton.addEventListener('click', (e) => {
                e.stopPropagation();
                navigateViewer(1);
            });
        }

        updateImageView();
        imageViewerModal.style.display = 'flex';
        document.addEventListener('keydown', handleKeydown);
    }

    function closeImageViewer() {
        imageViewerModal.style.display = 'none';
        document.removeEventListener('keydown', handleKeydown);
    }

    function navigateViewer(direction) {
        const newIndex = currentViewerIndex + direction;
        if (newIndex >= 0 && newIndex < currentViewerItems.length) {
            currentViewerIndex = newIndex;
            updateImageView();
        }
    }

    function updateImageView() {
        viewerImageContent.style.opacity = '0';

        setTimeout(() => {
            viewerImageContent.src = currentViewerItems[currentViewerIndex].url;
            viewerImageContent.onload = () => {
                viewerImageContent.style.opacity = '1';
            };
        }, 150);

        document.getElementById('viewer-prev-btn').disabled = (currentViewerIndex === 0);
        document.getElementById('viewer-next-btn').disabled = (currentViewerIndex === currentViewerItems.length - 1);
    }

    function handleKeydown(e) {
        if (e.key === 'ArrowLeft') {
            navigateViewer(-1);
        } else if (e.key === 'ArrowRight') {
            navigateViewer(1);
        } else if (e.key === 'Escape') {
            closeImageViewer();
        }
    }

    if (imageViewerClose) {
        imageViewerClose.addEventListener('click', closeImageViewer);
    }

    if (imageViewerModal) {
        imageViewerModal.addEventListener('click', (e) => {
            if (e.target === imageViewerModal) {
                closeImageViewer();
            }
        });
    }

    document.addEventListener('click', (e) => {
        const quoteBox = e.target.closest('.post-quote');
        
        if (quoteBox) {
            e.preventDefault();
            const postId = quoteBox.dataset.quoteId;
            if (postId) {
                scrollToPost(postId);
            }
        }
    });
});