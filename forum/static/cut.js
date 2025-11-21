window.showImageCropper = function(files, onComplete) {
    if (typeof Croppie === 'undefined') {
        console.error('[CutJS] KRİTİK HATA: Croppie kütüphanesi bulunamadı!');
        alert('Resim düzenleme aracı yüklenemedi.');
        onComplete([]);
        return;
    }
    new CroppieModal(files, onComplete).show();
};

class CroppieModal {
    constructor(files, onComplete) {
        this.files = files;
        this.onComplete = onComplete;
        this.currentIndex = 0;
        this.croppieInstance = null;
        this.cachedCropData = new Array(files.length).fill(null);
        this.elements = {};
    }

    show() {
        this._createModal();
        this._attachEventListeners();
        document.body.appendChild(this.elements.backdrop);
        document.body.style.overflow = 'hidden';

        this._initializeCroppie();
        this._loadImage(this.currentIndex);
    }

    close(isCancelled = true) {
        if (this.croppieInstance) this.croppieInstance.destroy();
        document.body.style.overflow = '';
        this.elements.backdrop.style.animation = 'croppieFadeIn 0.3s reverse forwards';
        setTimeout(() => {
            if (this.elements.backdrop.parentElement) {
                this.elements.backdrop.remove();
            }
            if (isCancelled) this.onComplete([]);
        }, 300);
    }

    _initializeCroppie() {
        const croppieContainer = this.elements.croppieContainer;
        this.croppieInstance = new Croppie(croppieContainer, {
            viewport: { width: 250, height: 250, type: 'square' },
            boundary: { width: 300, height: 300 },
            enableExif: true
        });
    }
    
    _loadImage(index) {
        if (index < 0 || index >= this.files.length) return;
        this.currentIndex = index;

        const file = this.files[index];
        const reader = new FileReader();

        reader.onload = (e) => {
           
            this.croppieInstance.bind({
                url: e.target.result
            }).then(() => {
               
                if (this.cachedCropData[index]) {
                    this.croppieInstance.bind({
                        url: e.target.result,
                        points: this.cachedCropData[index].points,
                        zoom: this.cachedCropData[index].zoom
                    });
                }
            });
        };
        reader.readAsDataURL(file);
        this._updateUI();
    }

    _updateUI() {
        this.elements.counter.textContent = `${this.currentIndex + 1} / ${this.files.length}`;
        this.elements.prevBtn.disabled = this.currentIndex === 0;

        if (this.currentIndex === this.files.length - 1) {
            this.elements.nextBtn.textContent = getLang('cropper_finish') || 'Bitir';
            this.elements.nextBtn.classList.add('croppie-finish-btn');
        } else {
            this.elements.nextBtn.textContent = getLang('cropper_next') || 'İleri';
            this.elements.nextBtn.classList.remove('croppie-finish-btn');
        }
    }

    _saveCurrentCropData() {
        if (this.croppieInstance) {
            const cropData = this.croppieInstance.get();
            this.cachedCropData[this.currentIndex] = {
                x: cropData.points[0],
                y: cropData.points[1],
                width: cropData.points[2] - cropData.points[0],
                height: cropData.points[3] - cropData.points[1]
            };
        }
    }

    _attachEventListeners() {
        this.elements.closeBtn.addEventListener('click', () => this.close());
        this.elements.backdrop.addEventListener('click', (e) => {
            if (e.target === this.elements.backdrop) this.close();
        });

        this.elements.prevBtn.addEventListener('click', () => {
            this._saveCurrentCropData();
            this._loadImage(this.currentIndex - 1);
        });
        
        this.elements.nextBtn.addEventListener('click', () => {
            this._saveCurrentCropData();
            if (this.currentIndex < this.files.length - 1) {
                this._loadImage(this.currentIndex + 1);
            } else {
                this.onComplete(this.cachedCropData);
                this.close(false);
            }
        });
    }

    _createModal() {
        const E = (tag, attributes, children = []) => {
            const el = document.createElement(tag);
            Object.assign(el, attributes);
            const childrenArray = Array.isArray(children) ? children : [children];
            childrenArray.forEach(child => {
                if(child) el.appendChild(child instanceof Node ? child : document.createTextNode(child));
            });
            return el;
        };

        this.elements.backdrop = E('div', { className: 'croppie-modal-backdrop' }, [
            this.elements.content = E('div', { className: 'croppie-modal-content' }, [
                E('div', { className: 'croppie-modal-header' }, [
                    E('h3', { textContent: getLang('cropper_title') || 'Resimleri Ayarla' }),
                    this.elements.closeBtn = E('button', { className: 'croppie-modal-close', textContent: '×' })
                ]),
                E('div', { className: 'croppie-modal-body' }, [
                    this.elements.croppieContainer = E('div', { id: 'croppie-main-container' })
                ]),
                E('div', { className: 'croppie-modal-footer' }, [
                    this.elements.prevBtn = E('button', { className: 'croppie-nav-btn', textContent: getLang('cropper_back') || 'Geri' }),
                    this.elements.counter = E('span', { className: 'croppie-counter' }),
                    this.elements.nextBtn = E('button', { className: 'croppie-nav-btn', textContent: getLang('cropper_next') || 'İleri' })
                ])
            ])
        ]);
    }
}