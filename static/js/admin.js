/* © 2025 ToolVision. All Rights Reserved. Unauthorized copying is prohibited. */
document.addEventListener('DOMContentLoaded', () => {
    // --- GÜVENLİK KATMANI: Geliştirici araçları, sağ tık ve kopyalama engelleme ---
    (() => {
        document.addEventListener('contextmenu', event => event.preventDefault());

        document.addEventListener('keydown', function(e) {
            if (e.key === "F12" || 
                (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "J" || e.key === "C")) || 
                (e.ctrlKey && e.key === "U")) {
                e.preventDefault();
            }
        });
    })();

    // --- GENEL ELEMANLAR ---
    const userManagementTable = document.querySelector('.user-management-table tbody');

    // Susturulan Kullanıcılar Elemanları
    const mutesLoading = document.getElementById('mutes-loading');
    const activeMutesBody = document.getElementById('active-mutes-body');
    const inactiveMutesBody = document.getElementById('inactive-mutes-body');
    
    // Niyetler (Intentions) Elemanları
    const intentsLoading = document.getElementById('intents-loading');
    const activeIntentsBody = document.getElementById('active-intents-body');
    const passiveIntentsBody = document.getElementById('passive-intents-body');
    
    // Niyet Modalları
    const intentInfoModal = document.getElementById('intentInfoModal');
    const intentReceiptModal = document.getElementById('intentReceiptModal');
    const intentPreferenceModal = document.getElementById('intentPreferenceModal');
    const intentActionFooter = document.getElementById('intent-action-footer');
    const intentStatusDisplay = document.getElementById('intent-status-display');

    // --- ROL DÜZENLEME MODALI ---
    const roleModal = document.getElementById('roleModal');
    const roleSelect = document.getElementById('role-select');
    const durationGroup = document.getElementById('duration-group');

    // --- CİHAZ YÖNETİM MODALI ---
    const deviceModal = document.getElementById('deviceModal');
    const deviceModalBody = document.getElementById('modal-device-body');

    // --- GLOBAL DEĞİŞKENLER ---
    const currentAdminUsername = window.CURRENT_ADMIN_USERNAME || 'Siz';
    
    // Susturma sayaçlarını takip etmek için bir obje
    let muteCountdownIntervals = {};

    // --- CSRF TOKEN FONKSİYONU ---
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }

    if (typeof window.getCSRFToken !== 'function') {
        window.getCSRFToken = getCSRFToken;
    }

    if (typeof window.showToastNotification !== 'function') {
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
    }

    // --- GÜVENLİK FONKSİYONLARI ---
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function safeCreateElement(tag, className, textContent) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (textContent) element.textContent = textContent;
        return element;
    }

    function safeSetAttribute(element, attribute, value) {
        element.setAttribute(attribute, value);
    }

    // --- SUSTURULAN KULLANICI YÖNETİMİ FONKSİYONLARI ---
    async function fetchMutedUsers() {
        try {
            const response = await fetch('/admin/muted_users');
            if (!response.ok) throw new Error('Susturulan kullanıcılar alınamadı.');
            const data = await response.json();
            renderMutedUsers(data.active_mutes, data.inactive_mutes);
            if (mutesLoading) mutesLoading.style.display = 'none';
        } catch (error) {
            console.error(error);
            if (mutesLoading) mutesLoading.textContent = 'Susturulan kullanıcılar yüklenirken bir hata oluştu.';
        }
    }

    function renderMutedUsers(activeMutes = [], inactiveMutes = []) {
        // Önceki sayaçları temizle
        Object.values(muteCountdownIntervals).forEach(clearInterval);
        muteCountdownIntervals = {};

        // Aktif Susturulanlar
        if (activeMutesBody) {
            activeMutesBody.innerHTML = '';
            if (activeMutes.length === 0) {
                activeMutesBody.innerHTML = '<tr><td colspan="3" class="no-muted-users">Aktif olarak susturulmuş kullanıcı bulunmuyor.</td></tr>';
            } else {
                activeMutes.forEach(mute => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>
                            <div class="user-cell">
                                <img src="${mute.user.profile_pic}" class="user-profile-thumb" alt="${mute.user.username}">
                                <div><strong>${escapeHtml(mute.user.username)}</strong><br><small>${escapeHtml(mute.user.email)}</small></div>
                            </div>
                        </td>
                        <td><div class="role-display role-${mute.user.role.replace('_', '-')}">${escapeHtml(mute.user.role.replace('_', ' '))}</div></td>
                        <td><span class="mute-countdown" id="countdown-${mute.id}" data-expiry="${mute.mute_end_time}">--:--:--</span></td>
                    `;
                    activeMutesBody.appendChild(tr);
                    // Geri sayım sayacını başlat
                    const countdownElement = document.getElementById(`countdown-${mute.id}`);
                    startMuteCountdown(countdownElement, mute.mute_end_time);
                });
            }
        }

        // Pasif Susturulanlar (Geçmiş)
        if (inactiveMutesBody) {
            inactiveMutesBody.innerHTML = '';
            if (inactiveMutes.length === 0) {
                inactiveMutesBody.innerHTML = '<tr><td colspan="3" class="no-muted-users">Geçmişte susturulmuş kullanıcı kaydı bulunmuyor.</td></tr>';
            } else {
                inactiveMutes.forEach(mute => {
                    const tr = document.createElement('tr');
                    const formattedEndDate = new Date(mute.mute_end_time).toLocaleString('tr-TR');
                    tr.innerHTML = `
                        <td>
                            <div class="user-cell">
                                <img src="${mute.user.profile_pic}" class="user-profile-thumb" alt="${mute.user.username}">
                                <div><strong>${escapeHtml(mute.user.username)}</strong><br><small>${escapeHtml(mute.user.email)}</small></div>
                            </div>
                        </td>
                        <td><div class="role-display role-${mute.user.role.replace('_', '-')}">${escapeHtml(mute.user.role.replace('_', ' '))}</div></td>
                        <td>${formattedEndDate}</td>
                    `;
                    inactiveMutesBody.appendChild(tr);
                });
            }
        }
    }

    function startMuteCountdown(element, expiryDateISO) {
        const expiryTime = new Date(expiryDateISO).getTime();

        const updateCountdown = () => {
            const now = new Date().getTime();
            const distance = expiryTime - now;

            if (distance < 0) {
                clearInterval(muteCountdownIntervals[element.id]);
                element.textContent = "Süre Doldu";
                // Süre dolduğunda listeyi yenilemek için 2 saniye bekle
                setTimeout(fetchMutedUsers, 2000);
                return;
            }

            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            element.textContent =
                hours.toString().padStart(2, '0') + ":" +
                minutes.toString().padStart(2, '0') + ":" +
                seconds.toString().padStart(2, '0');
        };

        updateCountdown();
        muteCountdownIntervals[element.id] = setInterval(updateCountdown, 1000);
    }

    // --- ÖDEME NİYETİ (INTENTIONS) YÖNETİMİ ---
    async function fetchIntents() {
        try {
            const response = await fetch('/admin/get_intents');
            if (!response.ok) throw new Error('Onay bekleyen kayıtlar alınamadı.');
            const data = await response.json();
            renderIntents(data.active_intents, data.passive_intents);
            if (intentsLoading) intentsLoading.style.display = 'none';
        } catch (error) {
            console.error(error);
            if (intentsLoading) intentsLoading.textContent = 'Onay bekleyen kayıtlar yüklenirken bir hata oluştu.';
        }
    }

    function renderIntents(activeIntents = [], passiveIntents = []) {
        // Aktif Niyetler
        if (activeIntentsBody) {
            activeIntentsBody.innerHTML = '';
            if (activeIntents.length === 0) {
                activeIntentsBody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 15px;">Onay bekleyen aktif bir kayıt bulunmuyor.</td></tr>';
            } else {
                activeIntents.forEach(intent => {
                    const tr = document.createElement('tr');
                    tr.id = `intent-row-${intent.id}`;
                    
                    const safeInfoData = escapeHtml(JSON.stringify({
                        name: intent.customer_name, // Bu artık Kullanıcı Adı
                        // phone: intent.customer_phone, // SİLİNDİ
                        email: intent.customer_email
                    }));
                    const safePrefData = escapeHtml(JSON.stringify({
                        role: intent.role,
                        duration: intent.duration,
                        price: intent.price
                    }));

                    tr.innerHTML = `
                        <td>
                            <div class="user-cell">
                                <img src="${intent.user.profile_pic}" class="user-profile-thumb" alt="${escapeHtml(intent.user.username)}">
                                <div><strong>${escapeHtml(intent.user.username)}</strong><br><small>${escapeHtml(intent.user.email)}</small></div>
                            </div>
                        </td>
                        <td><div class="role-display role-${intent.user.current_role.replace('_', '-')}">${escapeHtml(intent.user.current_role.replace('_', ' '))}</div></td>
                        <td>
                            <div class="action-buttons-cell">
                                <button class="action-btn intent-info-btn" 
                                        data-info='${safeInfoData}'>
                                    <i class="fas fa-user"></i> Bilgiler
                                </button>
                                <button class="action-btn intent-receipt-btn" 
                                        data-receipt-path="${intent.receipt_image_path}">
                                    <i class="fas fa-receipt"></i> Dekont
                                </button>
                                <button class="action-btn intent-preference-btn"
                                        data-intent-id="${intent.id}"
                                        data-status="${intent.status}"
                                        data-preference='${safePrefData}'>
                                    <i class="fas fa-star"></i> Tercih
                                </button>
                            </div>
                        </td>
                    `;
                    activeIntentsBody.appendChild(tr);
                });
            }
        }

        // Pasif Niyetler
        if (passiveIntentsBody) {
            passiveIntentsBody.innerHTML = '';
            if (passiveIntents.length === 0) {
                passiveIntentsBody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 15px;">İşlenmiş (pasif) bir kayıt bulunmuyor.</td></tr>';
            } else {
                passiveIntents.forEach(intent => {
                    const tr = document.createElement('tr');
                    
                    const safeInfoData = escapeHtml(JSON.stringify({
                        name: intent.customer_name, // Bu artık Kullanıcı Adı
                        // phone: intent.customer_phone, // SİLİNDİ
                        email: intent.customer_email
                    }));
                    const safePrefData = escapeHtml(JSON.stringify({
                        role: intent.role,
                        duration: intent.duration,
                        price: intent.price
                    }));
                    
                    const statusText = intent.status === 'COMPLETED' ? 'Onaylandı' : 'Reddedildi';
                    const statusClass = intent.status === 'COMPLETED' ? 'status-completed' : 'status-cancelled';

                    tr.innerHTML = `
                        <td>
                            <div class="user-cell">
                                <img src="${intent.user.profile_pic}" class="user-profile-thumb" alt="${escapeHtml(intent.user.username)}">
                                <div><strong>${escapeHtml(intent.user.username)}</strong><br><small>${escapeHtml(intent.user.email)}</small></div>
                            </div>
                        </td>
                        <td>
                            <span class="intent-status-badge ${statusClass}">${statusText}</span>
                        </td>
                        <td>
                            <div class="action-buttons-cell">
                                <button class="action-btn intent-info-btn" data-info='${safeInfoData}'>
                                    <i class="fas fa-user"></i> Bilgiler
                                </button>
                                <button class="action-btn intent-receipt-btn" data-receipt-path="${intent.receipt_image_path}">
                                    <i class="fas fa-receipt"></i> Dekont
                                </button>
                                <button class="action-btn intent-preference-btn"
                                        data-intent-id="${intent.id}"
                                        data-status="${intent.status}"
                                        data-preference='${safePrefData}'>
                                    <i class="fas fa-eye"></i> İncele
                                </button>
                            </div>
                        </td>
                    `;
                    passiveIntentsBody.appendChild(tr);
                });
            }
        }
    }

    function handleIntentButtonClick(e) {
        const target = e.target;
        const isKurucu = (window.CURRENT_ADMIN_ROLE === 'kurucu');

        // 1. Bilgiler Butonu
        const infoBtn = target.closest('.intent-info-btn');
        if (infoBtn) {
            try {
                const info = JSON.parse(infoBtn.dataset.info);
                document.getElementById('intent-info-name').value = info.name || 'Girilmemiş';
                // document.getElementById('intent-info-phone').value = ... // SİLİNDİ
                document.getElementById('intent-info-email').value = info.email || 'Girilmemiş';
                intentInfoModal.style.display = 'flex';
            } catch (err) {
                console.error("Bilgi verisi okunamadı:", err);
                alert("Kullanıcı bilgileri yüklenirken bir hata oluştu.");
            }
            return;
        }

        // 2. Dekont Butonu
        const receiptBtn = target.closest('.intent-receipt-btn');
        if (receiptBtn) {
            const receiptPath = receiptBtn.dataset.receiptPath;
            if (receiptPath && receiptPath !== 'null') {
                document.getElementById('intent-receipt-image').src = receiptPath;
                intentReceiptModal.style.display = 'flex';
            } else {
                alert('Bu kayıt için bir dekont görüntüsü bulunmuyor.');
            }
            return;
        }

        // 3. Tercih / İncele Butonu
        const prefBtn = target.closest('.intent-preference-btn');
        if (prefBtn) {
            try {
                const pref = JSON.parse(prefBtn.dataset.preference);
                const intentId = prefBtn.dataset.intentId;
                const status = prefBtn.dataset.status;

                // Modal içeriğini doldur
                document.getElementById('intent-pref-role').value = pref.role || 'N/A';
                document.getElementById('intent-pref-duration').value = pref.duration || 'N/A';
                document.getElementById('intent-pref-price').value = pref.price || 'N/A';

                // Modal'ın eylem butonlarını ve ID'sini ayarla
                const approveBtn = document.getElementById('intent-approve-btn');
                const rejectBtn = document.getElementById('intent-reject-btn');
                
                // data-intent-id'yi her iki butona da ata
                approveBtn.dataset.intentId = intentId;
                rejectBtn.dataset.intentId = intentId;

                if (status === 'WAITING_FOR_ADMIN') {
                    // --- AKTİF KAYIT ---
                    intentActionFooter.style.display = 'flex';
                    intentStatusDisplay.style.display = 'none';

                    // Sadece Kurucu butonları kullanabilir
                    if (isKurucu) {
                        approveBtn.disabled = false;
                        rejectBtn.disabled = false;
                        approveBtn.title = "Ödemeyi onayla ve rolü ata";
                        rejectBtn.title = "Ödemeyi reddet";
                    } else {
                        // Kurucu değilse butonları KİLİTLE
                        approveBtn.disabled = true;
                        rejectBtn.disabled = true;
                        approveBtn.title = "Bu işlemi sadece 'Kurucu' rolü yapabilir.";
                        rejectBtn.title = "Bu işlemi sadece 'Kurucu' rolü yapabilir.";
                    }
                } else {
                    // --- PASİF KAYIT ---
                    intentActionFooter.style.display = 'none';
                    intentStatusDisplay.style.display = 'block';
                    
                    const statusTextEl = document.getElementById('intent-status-text');
                    if (status === 'COMPLETED') {
                        statusTextEl.textContent = 'Onaylandı';
                        statusTextEl.className = 'role-display status-completed';
                    } else {
                        statusTextEl.textContent = 'Reddedildi';
                        statusTextEl.className = 'role-display status-cancelled';
                    }
                }
                
                intentPreferenceModal.style.display = 'flex';

            } catch (err) {
                console.error("Tercih verisi okunamadı:", err);
                alert("Kayıt tercihleri yüklenirken bir hata oluştu.");
            }
            return;
        }
    }
    
    // Niyet tablolarına (aktif ve pasif) tek bir olay dinleyici ata
    if (activeIntentsBody) activeIntentsBody.addEventListener('click', handleIntentButtonClick);
    if (passiveIntentsBody) passiveIntentsBody.addEventListener('click', handleIntentButtonClick);

    async function processIntent(intentId, action) {
        const approveBtn = document.getElementById('intent-approve-btn');
        const rejectBtn = document.getElementById('intent-reject-btn');
        
        approveBtn.disabled = true;
        rejectBtn.disabled = true;
        
        const originalBtnText = (action === 'approve') ? approveBtn.innerHTML : rejectBtn.innerHTML;
        const targetBtn = (action === 'approve') ? approveBtn : rejectBtn;
        targetBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> İşleniyor...`;

        try {
            const csrfToken = getCSRFToken();
            const response = await fetch('/admin/process_intent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    intent_id: intentId,
                    action: action
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Bilinmeyen bir sunucu hatası.');
            }
            
            alert(result.message);
            intentPreferenceModal.style.display = 'none';
            fetchIntents();

        } catch (error) {
            alert('Hata: ' + error.message);
            targetBtn.innerHTML = originalBtnText;
            // Kurucu ise butonları tekrar aktif et
            if (window.CURRENT_ADMIN_ROLE === 'kurucu') {
                 approveBtn.disabled = false;
                 rejectBtn.disabled = false;
            }
        }
    }

    // Modal içerisindeki Onay/Reddet butonlarına olay dinleyici ata
    document.getElementById('intent-approve-btn').addEventListener('click', (e) => {
        const intentId = e.currentTarget.dataset.intentId;
        processIntent(intentId, 'approve');
    });
    
    document.getElementById('intent-reject-btn').addEventListener('click', (e) => {
        const intentId = e.currentTarget.dataset.intentId;
        processIntent(intentId, 'reject');
    });

    // --- GENEL MODAL VE TAB YÖNETİMİ ---
    document.querySelectorAll('.card-tabs').forEach(tabContainer => {
        const tabBtns = tabContainer.querySelectorAll('.tab-btn');
        const card = tabContainer.closest('.card');
        const contentDivs = card.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                contentDivs.forEach(c => c.classList.remove('active'));
                const targetContent = card.querySelector('#' + btn.dataset.tab + '-content');
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    });

    document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-backdrop');
        if (modal) {
            modal.style.display = 'none';
        }
    }));

    // --- KULLANICI YÖNETİMİ TABLOSU İŞLEVLERİ ---
    if (userManagementTable) {
        userManagementTable.addEventListener('click', async (e) => {
            const target = e.target;
            
            const logButton = target.closest('.view-logs-btn');
            if (logButton) {
                const logModal = document.getElementById('logModal');
                const userId = logButton.dataset.userId;
                const userName = logButton.dataset.userName;
                document.getElementById('modal-title-user').textContent = userName;
                const modalBody = document.getElementById('modal-body-content');
                
                modalBody.innerHTML = '';
                const loadingP = safeCreateElement('p', null, 'Yükleniyor...');
                modalBody.appendChild(loadingP);
                
                logModal.style.display = 'flex';
                try {
                    const response = await fetch(`/admin/get_logs/${userId}`);
                    const logs = await response.json();
                    if (logs.error) throw new Error(logs.error);
                    
                    modalBody.innerHTML = '';
                    
                    if (logs.length) {
                        const logList = safeCreateElement('ul', 'log-list');
                        
                        logs.forEach(log => {
                            const logItem = safeCreateElement('li', 'log-item');
                            
                            const timestampSpan = safeCreateElement('span', 'timestamp', log.timestamp);
                            const actionSpan = safeCreateElement('span', null, log.action);
                            
                            logItem.appendChild(timestampSpan);
                            logItem.appendChild(actionSpan);
                            logList.appendChild(logItem);
                        });
                        
                        modalBody.appendChild(logList);
                    } else {
                        const noLogsP = safeCreateElement('p', null, 'Bu kullanıcı için aktivite bulunamadı.');
                        modalBody.appendChild(noLogsP);
                    }
                } catch(err) {
                    modalBody.innerHTML = '';
                    const errorP = safeCreateElement('p', null, 'Loglar yüklenemedi veya bu logları görme yetkiniz yok.');
                    errorP.style.color = 'var(--color-accent-red)';
                    modalBody.appendChild(errorP);
                }
            }

            const deviceButton = target.closest('.manage-devices-btn');
            if (deviceButton) {
                const userId = deviceButton.dataset.userId;
                const userName = deviceButton.dataset.userName;

                document.getElementById('modal-device-user').textContent = userName;
                deviceModal.dataset.userId = userId; 
                
                deviceModalBody.innerHTML = '';
                const loadingP = safeCreateElement('p', null, 'Cihazlar yükleniyor...');
                deviceModalBody.appendChild(loadingP);
                
                if(deviceModal) deviceModal.style.display = 'flex';

                try {
                    const response = await fetch(`/admin/get_devices/${userId}`);
                    const devices = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(devices.error || 'Cihazlar alınamadı.');
                    }
                    
                    deviceModalBody.innerHTML = '';
                    
                    if (devices.length === 0) {
                        const noDevicesP = safeCreateElement('p', null, 'Kullanıcının kayıtlı cihazı bulunmuyor.');
                        deviceModalBody.appendChild(noDevicesP);
                        return;
                    }
                    
                    const deviceList = safeCreateElement('ul', 'device-list');
                    
                    devices.forEach(device => {
                        const deviceItem = safeCreateElement('li', 'device-item');
                        safeSetAttribute(deviceItem, 'id', `device-item-slot-${device.slot_index}`);
                        
                        const deviceInfo = safeCreateElement('div', 'device-info');
                        const deviceIcon = safeCreateElement('i', 'fas fa-desktop');
                        const deviceDetails = safeCreateElement('div', 'device-details');
                        
                        const deviceName = safeCreateElement('strong', null, device.name);
                        const lastLogin = safeCreateElement('small', null, `Son Giriş: ${device.last_login}`);
                        
                        deviceDetails.appendChild(deviceName);
                        deviceDetails.appendChild(lastLogin);
                        deviceInfo.appendChild(deviceIcon);
                        deviceInfo.appendChild(deviceDetails);
                        deviceItem.appendChild(deviceInfo);
                        
                        if (window.CURRENT_ADMIN_ROLE === 'kurucu') {
                            const removeBtn = safeCreateElement('button', 'action-btn remove-device-btn');
                            safeSetAttribute(removeBtn, 'data-slot-index', device.slot_index);
                            safeSetAttribute(removeBtn, 'title', 'Cihazı Kaldır ve Oturumu Sonlandır');
                            
                            const trashIcon = safeCreateElement('i', 'fas fa-trash');
                            removeBtn.appendChild(trashIcon);
                            removeBtn.appendChild(document.createTextNode(' Kaldır'));
                            
                            deviceItem.appendChild(removeBtn);
                        }
                        
                        deviceList.appendChild(deviceItem);
                    });
                    
                    deviceModalBody.appendChild(deviceList);
                } catch (error) {
                    deviceModalBody.innerHTML = '';
                    const errorP = safeCreateElement('p', null, error.message);
                    errorP.style.color = 'var(--danger-color)';
                    deviceModalBody.appendChild(errorP);
                }
            }

            const roleButton = target.closest('.edit-role-btn');
            if (roleButton) {
                const userId = roleButton.dataset.userId;
                const userName = roleButton.dataset.userName;
                const currentRole = roleButton.dataset.currentRole;

                document.getElementById('modal-user-id').value = userId;
                document.getElementById('modal-role-user').textContent = userName;
                roleSelect.value = currentRole;
                roleSelect.dispatchEvent(new Event('change'));
                roleModal.style.display = 'flex';
            }

            const deleteButton = target.closest('.emergency-delete-btn');
            if (deleteButton) {
                const userId = deleteButton.dataset.userId;
                const userName = deleteButton.dataset.userName;
                if (confirm(`'${userName}' kullanıcısını devre dışı bırakmak istediğinizden emin misiniz? Bu işlem geri alınamaz.`)) {
                    try {
                        const csrfToken = getCSRFToken();
                        const response = await fetch('/admin/emergency_delete', { 
                            method: 'POST', 
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            }, 
                            body: JSON.stringify({ user_id: userId }) 
                        });

                        const contentType = response.headers.get("content-type");
                        if (contentType && contentType.indexOf("application/json") !== -1) {
                            const result = await response.json();
                            if (!response.ok) {
                                throw new Error(result.error || 'Bilinmeyen bir sunucu hatası.');
                            }
                            alert(result.message);
                            const row = deleteButton.closest('tr');
                            row.classList.add('deleted-user-row');
                            
                            const actionCell = row.querySelector('.action-buttons-cell');
                            actionCell.innerHTML = '';
                            actionCell.appendChild(document.createTextNode('Devre Dışı'));
                        } else {
                            throw new Error('Sunucudan beklenmeyen bir yanıt alındı. Lütfen tekrar giriş yapıp deneyin.');
                        }
                    } catch (error) {
                        alert('Hata: ' + error.message);
                    }
                }
            }

            const copyBtn = target.closest('.copy-btn');
            if (copyBtn) {
                navigator.clipboard.writeText(copyBtn.dataset.code).then(() => {
                    const icon = copyBtn.querySelector('i');
                    if (icon) {
                        icon.className = 'fas fa-check';
                        setTimeout(() => { icon.className = 'far fa-copy'; }, 1500);
                    }
                });
            }
        });

        // Yetki ekleme formunun 'change' olayını dinle
        userManagementTable.addEventListener('change', (e) => {
            if (e.target.classList.contains('permission-select')) {
                const form = e.target.closest('form');
                if (form) {
                    form.submit();
                }
            }
        });
    }

    // --- CİHAZ SİLME - YENİ SLOT SİSTEME UYUMLU HALİ ---
    if (deviceModalBody) {
        deviceModalBody.addEventListener('click', async (e) => {
            const removeButton = e.target.closest('.remove-device-btn');
            if (removeButton) {
                const slotIndex = removeButton.dataset.slotIndex;
                const userId = deviceModal.dataset.userId;

                if (!confirm(`Bu cihazı kalıcı olarak kaldırmak istediğinizden emin misiniz? Bu işlem, kullanıcının TÜM AKTİF OTURUMLARINI sonlandıracaktır.`)) return;
    
                removeButton.disabled = true;
                removeButton.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;
    
                try {
                    const csrfToken = getCSRFToken();
                    const response = await fetch('/admin/delete_device', { 
                        method: 'POST', 
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        }, 
                        body: JSON.stringify({ user_id: userId, slot_index: parseInt(slotIndex) }) 
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Bilinmeyen bir sunucu hatası.');
                    
                    const deviceItem = document.getElementById(`device-item-slot-${slotIndex}`);
                    if(deviceItem) {
                        deviceItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        deviceItem.style.opacity = '0';
                        deviceItem.style.transform = 'translateX(-20px)';
                        setTimeout(() => deviceItem.remove(), 300);
                    }

                } catch (error) {
                    alert('Hata: ' + error.message);
                    removeButton.disabled = false;
                    removeButton.innerHTML = `<i class="fas fa-trash"></i> Kaldır`;
                }
            }
        });
    }

    // --- ROL MODALI SÜRE GÖSTERİMİ ---
    if (roleSelect) {
        roleSelect.addEventListener('change', () => {
            const rolesWithDuration = ['premium', 'dev', 'caylak_admin', 'usta_admin'];
            durationGroup.style.display = rolesWithDuration.includes(roleSelect.value) ? 'block' : 'none';
        });
    }

    // --- PASTA GRAFİK ---
    const pieChartCanvas = document.getElementById('potentialPieChart');
    if (pieChartCanvas && window.PIE_CHART_LABELS && window.PIE_CHART_DATA) {
        new Chart(pieChartCanvas.getContext('2d'), {
            type: 'pie',
            data: {
                labels: window.PIE_CHART_LABELS,
                datasets: [{
                    label: 'Kullanıcı Potansiyeli',
                    data: window.PIE_CHART_DATA,
                    backgroundColor: ['rgba(245, 54, 92, 0.8)', 'rgba(251, 99, 64, 0.8)', 'rgba(45, 206, 137, 0.8)'],
                    borderColor: ['#f5365c', '#fb6340', '#2dce89'],
                    borderWidth: 1
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { 
                    legend: { 
                        position: 'top', 
                        labels: { 
                            color: 'white', 
                            font: { size: 13 } 
                        } 
                    } 
                } 
            }
        });
    }

    // --- UYGULAMAYI BAŞLAT ---
    fetchMutedUsers();
    fetchIntents();
    fetchReportedPosts();
});

    function parseReplyTags(text) {
        const regex = /\[reply id="(\d+)" user="([^"]+)"\](.*?)\[\/reply\]/g;
        return text.replace(regex, (match, id, user, content) => {
            return `<div class="post-quote" data-quote-id="${id}"><div class="post-quote-header"><i class="fas fa-reply"></i><span class="quote-username">${user}</span></div><div class="post-quote-content">${content}</div></div>`;
        });
    }
    let __reportsCache = { active: [], inactive: [] };
    async function fetchReportedPosts() {
        const reportsLoading = document.getElementById('reports-loading');
        if (reportsLoading) reportsLoading.style.display = 'block';
        try {
            let res = await fetch('/admin/reported_posts');
            if (!res.ok) {
                // Fallback alias path
                res = await fetch('/admin/reports');
            }
            if (!res.ok) throw new Error('Raporlar yüklenemedi.');
            const data = await res.json();
            __reportsCache.active = data.active_reports || [];
            __reportsCache.inactive = data.inactive_reports || [];
            renderReportedPosts(__reportsCache.active, __reportsCache.inactive);
            if (reportsLoading) reportsLoading.style.display = 'none';
        } catch (e) {
            if (reportsLoading) reportsLoading.textContent = 'Reported posts could not be loaded.';
        }
    }

    function renderReportedPosts(active, inactive) {
        const activeBody = document.getElementById('active-reports-body');
        const passiveBody = document.getElementById('passive-reports-body');
        if (!activeBody || !passiveBody) return;

        activeBody.innerHTML = '';
        passiveBody.innerHTML = '';

        active.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="user-cell">
                    <div class="reporter-card"><img src="${r.reporter.profile_pic}" class="rc-avatar" alt="" loading="lazy"><div class="rc-info"><span class="rc-name">${r.reporter.username}</span><span class="rc-email">${r.reporter.email}</span></div></div>
                </td>
                <td><span class="reporter-role-badge">${r.reporter.role || 'Reporter'}</span></td>
                <td class="action-buttons-cell"><button class="action-btn details-report" data-report-id="${r.id}" data-report-status="active"><i class="fas fa-info-circle"></i> Details</button></td>
            `;
            activeBody.appendChild(tr);
        });

        inactive.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="user-cell">
                    <div class="reporter-card"><img src="${r.reporter.profile_pic}" class="rc-avatar" alt="" loading="lazy"><div class="rc-info"><span class="rc-name">${r.reporter.username}</span><span class="rc-email">${r.reporter.email}</span></div></div>
                </td>
                <td><span class="reporter-role-badge">${r.reporter.role || 'Reporter'}</span></td>
                <td><button class="action-btn details-report" data-report-id="${r.id}" data-report-status="inactive"><i class="fas fa-info-circle"></i> Details</button></td>
                <td><small>${r.processed_by_text || '-'}</small></td>
            `;
            passiveBody.appendChild(tr);
        });

        const wrapper = document.querySelector('.reported-posts-wrapper');
        if (!wrapper || wrapper.__listenerAttached) return;
        wrapper.__listenerAttached = true;
        wrapper.addEventListener('click', async (e) => {
            const target = e.target.closest('button');
            if (!target) return;
            if (target.classList.contains('details-report')) {
                const id = target.dataset.reportId;
                const status = target.dataset.reportStatus;
                const list = status === 'inactive' ? __reportsCache.inactive : __reportsCache.active;
                const r = list.find(x => String(x.id) === String(id));
                const modal = document.getElementById('reportDetailsModal');
                const body = document.getElementById('report-details-body');
                const footer = document.getElementById('report-details-footer');
                if (!r || !modal || !body || !footer) return;
                body.innerHTML = `<div style="text-align:center; padding: 10px; color: var(--color-text-secondary);">Generating preview...</div>`;
                try {
                    const url = await buildPostPhoto(r);
                    body.innerHTML = `<img src="${url}" alt="Post Preview" class="snapshot-photo">`;
                } catch (_) {
                    body.innerHTML = `
                        <div class="details-post">
                            <div class="details-post-text">${parseReplyTags((r.post.content || '').replace(/\n/g, '<br>'))}</div>
                            ${r.post.media && r.post.media.length ? `<div class="details-media">${r.post.media.map(m => `<img src="${m.thumbnail_url || m.url}" alt="">`).join('')}</div>` : ''}
                        </div>
                    `;
                }
                body.insertAdjacentHTML('beforeend', `<div class="reason-section"><span class="reason-title">Sebep</span><span class="reason-chip">${mapReason(r.reason_text || r.reason)}</span></div>`);
                const approveBtn = document.getElementById('report-approve-btn');
                const rejectBtn = document.getElementById('report-reject-btn');
                if (status === 'inactive') {
                    approveBtn.style.display = 'none';
                    rejectBtn.style.display = 'none';
                } else {
                    approveBtn.style.display = '';
                    rejectBtn.style.display = '';
                    approveBtn.onclick = async () => {
                        approveBtn.disabled = true;
                        try {
                            let res = await fetch(`/admin/reported_posts/${id}/approve`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
                            if (!res.ok) res = await fetch(`/admin/reports/${id}/approve`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
                            const data = await res.json();
                            if (res.ok) { window.showToastNotification('Report approved and post deleted.', 'success'); fetchReportedPosts(); modal.style.display = 'none'; }
                            else { window.showToastNotification(data.error || 'Approval failed.', 'error'); }
                        } finally { approveBtn.disabled = false; }
                    };
                    rejectBtn.onclick = async () => {
                        rejectBtn.disabled = true;
                        try {
                            let res = await fetch(`/admin/reported_posts/${id}/reject`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
                            if (!res.ok) res = await fetch(`/admin/reports/${id}/reject`, { method: 'POST', headers: { 'X-CSRFToken': window.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
                            const data = await res.json();
                            if (res.ok) { window.showToastNotification('Report rejected.', 'success'); fetchReportedPosts(); modal.style.display = 'none'; }
                            else { window.showToastNotification(data.error || 'Rejection failed.', 'error'); }
                        } finally { rejectBtn.disabled = false; }
                    };
                }
                modal.style.display = 'flex';
                modal.querySelector('.modal-close')?.addEventListener('click', () => { modal.style.display = 'none'; });
                modal.addEventListener('click', (evt) => { if (evt.target === modal) modal.style.display = 'none'; });
                return;
            }
            if (target.classList.contains('approve-report')) {
                const id = target.dataset.reportId;
                try {
                    target.disabled = true;
                    const original = target.innerHTML;
                    target.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing';
                    let res = await fetch(`/admin/reported_posts/${id}/approve`, { 
                        method: 'POST', 
                        headers: { 
                            'X-CSRFToken': window.getCSRFToken(),
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json'
                        }
                    });
                    if (!res.ok) {
                        res = await fetch(`/admin/reports/${id}/approve`, { 
                            method: 'POST', 
                            headers: { 
                                'X-CSRFToken': window.getCSRFToken(),
                                'X-Requested-With': 'XMLHttpRequest',
                                'Accept': 'application/json'
                            }
                        });
                    }
                    const data = await res.json();
                    if (res.ok) {
                        window.showToastNotification('Report approved and post deleted.', 'success');
                        fetchReportedPosts();
                    } else {
                        window.showToastNotification(data.error || 'Approval failed.', 'error');
                    }
                    target.disabled = false;
                    target.innerHTML = original;
                } catch (_) {
                    window.showToastNotification('Approval failed.', 'error');
                    target.disabled = false;
                }
            }
            if (target.classList.contains('reject-report')) {
                const id = target.dataset.reportId;
                try {
                    target.disabled = true;
                    const original = target.innerHTML;
                    target.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing';
                    let res = await fetch(`/admin/reported_posts/${id}/reject`, { 
                        method: 'POST', 
                        headers: { 
                            'X-CSRFToken': window.getCSRFToken(),
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json'
                        }
                    });
                    if (!res.ok) {
                        res = await fetch(`/admin/reports/${id}/reject`, { 
                            method: 'POST', 
                            headers: { 
                                'X-CSRFToken': window.getCSRFToken(),
                                'X-Requested-With': 'XMLHttpRequest',
                                'Accept': 'application/json'
                            }
                        });
                    }
                    const data = await res.json();
                    if (res.ok) {
                        window.showToastNotification('Report rejected.', 'success');
                        fetchReportedPosts();
                    } else {
                        window.showToastNotification(data.error || 'Rejection failed.', 'error');
                    }
                    target.disabled = false;
                    target.innerHTML = original;
                } catch (_) {
                    window.showToastNotification('Rejection failed.', 'error');
                    target.disabled = false;
                }
            }
            const goto = e.target.closest('.goto-user');
            if (goto) {
                e.preventDefault();
                const userId = goto.dataset.userId;
                const row = document.getElementById(`user-row-${userId}`);
                if (row) {
                    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    row.classList.add('highlight-flash');
                    setTimeout(() => row.classList.remove('highlight-flash'), 1500);
                }
            }
        });
    }
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;
        const container = btn.closest('.card');
        if (!container) return;
        container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        container.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        const content = container.querySelector(`#${tab}-content`);
        if (content) content.classList.add('active');
    });

    async function buildPostPhoto(r) {
        const width = 720;
        const padding = 18;
        const lineHeight = 22;
        const avatarSize = 40;
        const mediaSize = 68;
        const bg = getComputedStyle(document.documentElement).getPropertyValue('--color-card-bg') || '#1f2533';
        const fg = getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary') || '#ffffff';
        const secondary = getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary') || '#a0a7b3';
        const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--color-border') || '#2a3140';
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const font = '14px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        ctx.font = font;
        const content = (r.post && r.post.content) ? r.post.content : '';
        function wrap(text, maxWidth) {
            const words = text.replace(/<br>/g, '\n').replace(/\r/g, '').split(/\s+/);
            const lines = [];
            let line = '';
            for (let i = 0; i < words.length; i++) {
                const test = line ? line + ' ' + words[i] : words[i];
                if (ctx.measureText(test).width > maxWidth || words[i].includes('\n')) {
                    lines.push(line);
                    line = words[i].replace('\n', '');
                } else {
                    line = test;
                }
            }
            if (line) lines.push(line);
            return lines;
        }
        const textLines = wrap(parseReplyTags(content).replace(/<[^>]*>/g, ''), width - padding * 2 - avatarSize - 12);
        const mediaCount = (r.post && r.post.media) ? Math.min(r.post.media.length, 3) : 0;
        const height = padding * 2 + Math.max(avatarSize, 20) + 8 + textLines.length * lineHeight + (mediaCount ? mediaSize + 10 : 0) + 20;
        canvas.width = width;
        canvas.height = height;
        function roundRect(x, y, w, h, r) {
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.arcTo(x + w, y, x + w, y + h, r);
            ctx.arcTo(x + w, y + h, x, y + h, r);
            ctx.arcTo(x, y + h, x, y, r);
            ctx.arcTo(x, y, x + w, y, r);
            ctx.closePath();
        }
        ctx.fillStyle = bg.trim();
        roundRect(0, 0, width, height, 12);
        ctx.fill();
        ctx.strokeStyle = borderColor.trim();
        ctx.stroke();
        const avatar = await loadImage(r.reported.profile_pic);
        ctx.save();
        ctx.beginPath();
        ctx.arc(padding + avatarSize / 2, padding + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
        ctx.closePath();
        ctx.clip();
        ctx.drawImage(avatar, padding, padding, avatarSize, avatarSize);
        ctx.restore();
        ctx.fillStyle = fg.trim();
        ctx.font = '600 16px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        ctx.fillText(r.reported.username || '', padding + avatarSize + 12, padding + 18);
        ctx.font = font;
        ctx.fillStyle = secondary.trim();
        ctx.fillText(r.reported.email || '', padding + avatarSize + 12, padding + 18 + 18);
        ctx.fillStyle = fg.trim();
        let ty = padding + avatarSize + 18;
        textLines.forEach((ln, i) => {
            ctx.fillText(ln, padding, ty + i * lineHeight);
        });
        if (mediaCount) {
            const mY = ty + textLines.length * lineHeight + 10;
            const gap = 8;
            for (let i = 0; i < mediaCount; i++) {
                const m = r.post.media[i];
                const img = await loadImage(m.thumbnail_url || m.url);
                const x = padding + i * (mediaSize + gap);
                ctx.drawImage(img, x, mY, mediaSize, mediaSize);
            }
        }
        return canvas.toDataURL('image/png');
    }

    function loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = src;
        });
    }

    function mapReason(code) {
        const map = {
            'report_reason_1': 'Spam',
            'report_reason_2': 'Taciz/Kötüye Kullanım',
            'report_reason_3': 'Nefret Söylemi',
            'report_reason_4': 'Müstehcen İçerik',
            'report_reason_5': 'Şiddet/Tehdit',
            'report_reason_6': 'Dolandırıcılık/Yanıltma',
            'report_reason_7': 'Kişisel Bilgi',
            'report_reason_8': 'Diğer'
        };
        if (!code) return '-';
        const key = String(code).trim();
        return map[key] || key;
    }