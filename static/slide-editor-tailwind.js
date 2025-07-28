// Enhanced Slide Editor for Tailwind CSS Frontend
// Global editor state
let slideEditor = {
    canvas: null,
    selectedElement: null,
    isEditingText: false,
    dragStartPos: null,
    history: [],
    historyIndex: -1,
    clipboard: null,
    tools: {
        selection: true,
        text: false,
        shape: false,
        image: false
    }
};

// Initialize enhanced editor when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeSlideEditor, 1000); // Delay to ensure DOM is ready
    setupEditorEventListeners();
});

// Initialize the slide editor
function initializeSlideEditor() {
    const canvasElement = document.getElementById('slide-canvas');
    if (!canvasElement) {
        console.log('Canvas element not found, retrying...');
        setTimeout(initializeSlideEditor, 500);
        return;
    }
    
    try {
        // Initialize Fabric.js canvas
        slideEditor.canvas = new fabric.Canvas('slide-canvas', {
            width: 800,
            height: 600,
            backgroundColor: '#ffffff',
            preserveObjectStacking: true
        });
        
        console.log('Slide editor canvas initialized successfully');
        
        // Setup canvas event handlers
        setupCanvasEvents();
        
        // Resize canvas to fit container
        resizeCanvas();
        
    } catch (error) {
        console.error('Failed to initialize slide editor:', error);
    }
}

// Resize canvas to fit container
function resizeCanvas() {
    if (!slideEditor.canvas) return;
    
    const canvasWrapper = document.getElementById('slide-canvas-wrapper');
    if (!canvasWrapper) return;
    
    const rect = canvasWrapper.getBoundingClientRect();
    const aspectRatio = 800 / 600;
    
    let newWidth = rect.width;
    let newHeight = newWidth / aspectRatio;
    
    if (newHeight > rect.height) {
        newHeight = rect.height;
        newWidth = newHeight * aspectRatio;
    }
    
    slideEditor.canvas.setWidth(newWidth);
    slideEditor.canvas.setHeight(newHeight);
    slideEditor.canvas.renderAll();
}

// Setup canvas event handlers
function setupCanvasEvents() {
    const canvas = slideEditor.canvas;
    if (!canvas) return;
    
    // Object selection
    canvas.on('selection:created', function(e) {
        handleElementSelection(e.selected[0]);
    });
    
    canvas.on('selection:updated', function(e) {
        handleElementSelection(e.selected[0]);
    });
    
    canvas.on('selection:cleared', function() {
        hidePropertiesPanel();
    });
    
    // Object modification
    canvas.on('object:modified', function(e) {
        saveToHistory('Object Modified');
        updateElementProperties(e.target);
    });
    
    // Double-click for text editing
    canvas.on('mouse:dblclick', function(e) {
        if (e.target && e.target.type === 'textbox') {
            enterTextEditMode(e.target);
        }
    });
    
    // Mouse events for better interaction
    canvas.on('mouse:down', function(e) {
        if (!e.target) {
            hidePropertiesPanel();
        }
    });
}

// Setup enhanced editor event listeners
function setupEditorEventListeners() {
    // Image upload
    const imageFileInput = document.getElementById('image-file-input');
    if (imageFileInput) {
        imageFileInput.addEventListener('change', handleImageUpload);
    }
    
    // Modal handlers
    setupModalHandlers();
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Window resize
    window.addEventListener('resize', resizeCanvas);
    
    // Animation delay slider
    const animationDelaySlider = document.getElementById('animation-delay');
    const delayValue = document.getElementById('delay-value');
    if (animationDelaySlider && delayValue) {
        animationDelaySlider.addEventListener('input', function() {
            delayValue.textContent = this.value + 'ms';
        });
    }
}

// Handle element selection
function handleElementSelection(element) {
    slideEditor.selectedElement = element;
    showPropertiesPanel(element);
}

// Show properties panel for selected element
function showPropertiesPanel(element) {
    const propertiesPanel = document.getElementById('properties-panel');
    const elementProperties = document.getElementById('element-properties');
    
    if (!propertiesPanel || !elementProperties || !element) return;
    
    let propertiesHtml = '';
    
    // Position and Size properties
    propertiesHtml += `
        <div class="space-y-3 p-3 bg-gray-50 rounded-lg">
            <h4 class="text-sm font-semibold text-gray-800">Position & Size</h4>
            <div class="grid grid-cols-2 gap-2">
                <div>
                    <label class="block text-xs text-gray-600 mb-1">X Position</label>
                    <input type="number" value="${Math.round(element.left)}" onchange="updateElementProperty('left', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Y Position</label>
                    <input type="number" value="${Math.round(element.top)}" onchange="updateElementProperty('top', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Width</label>
                    <input type="number" value="${Math.round(element.width * (element.scaleX || 1))}" onchange="updateElementSize('width', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Height</label>
                    <input type="number" value="${Math.round(element.height * (element.scaleY || 1))}" onchange="updateElementSize('height', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
            </div>
            <div>
                <label class="block text-xs text-gray-600 mb-1">Rotation: <span class="font-medium">${element.angle || 0}°</span></label>
                <input type="range" min="0" max="360" value="${element.angle || 0}" onchange="updateElementProperty('angle', this.value)" 
                       class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
            </div>
        </div>
    `;
    
    // Element-specific properties
    if (element.type === 'textbox') {
        propertiesHtml += `
            <div class="space-y-3 p-3 bg-blue-50 rounded-lg">
                <h4 class="text-sm font-semibold text-gray-800">Text Properties</h4>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Font Size</label>
                    <input type="number" value="${element.fontSize}" onchange="updateElementProperty('fontSize', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Font Family</label>
                    <select onchange="updateElementProperty('fontFamily', this.value)" 
                            class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                        <option value="Inter" ${element.fontFamily === 'Inter' ? 'selected' : ''}>Inter</option>
                        <option value="Arial" ${element.fontFamily === 'Arial' ? 'selected' : ''}>Arial</option>
                        <option value="Helvetica" ${element.fontFamily === 'Helvetica' ? 'selected' : ''}>Helvetica</option>
                        <option value="Times New Roman" ${element.fontFamily === 'Times New Roman' ? 'selected' : ''}>Times New Roman</option>
                        <option value="Georgia" ${element.fontFamily === 'Georgia' ? 'selected' : ''}>Georgia</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Text Color</label>
                    <input type="color" value="${element.fill || '#000000'}" onchange="updateElementProperty('fill', this.value)" 
                           class="w-full h-8 border border-gray-300 rounded cursor-pointer">
                </div>
                <div class="flex space-x-2">
                    <button onclick="updateElementProperty('fontWeight', '${element.fontWeight === 'bold' ? 'normal' : 'bold'}')" 
                            class="flex-1 px-2 py-1 text-xs rounded border transition-colors ${element.fontWeight === 'bold' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}">
                        <i class="fas fa-bold"></i>
                    </button>
                    <button onclick="updateElementProperty('fontStyle', '${element.fontStyle === 'italic' ? 'normal' : 'italic'}')"
                            class="flex-1 px-2 py-1 text-xs rounded border transition-colors ${element.fontStyle === 'italic' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}">
                        <i class="fas fa-italic"></i>
                    </button>
                    <button onclick="updateElementProperty('underline', ${!element.underline})"
                            class="flex-1 px-2 py-1 text-xs rounded border transition-colors ${element.underline ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}">
                        <i class="fas fa-underline"></i>
                    </button>
                </div>
                <div class="flex space-x-2">
                    <button onclick="updateElementProperty('textAlign', 'left')" class="flex-1 px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                        <i class="fas fa-align-left"></i>
                    </button>
                    <button onclick="updateElementProperty('textAlign', 'center')" class="flex-1 px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                        <i class="fas fa-align-center"></i>
                    </button>
                    <button onclick="updateElementProperty('textAlign', 'right')" class="flex-1 px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                        <i class="fas fa-align-right"></i>
                    </button>
                </div>
            </div>
        `;
    } else if (element.type === 'rect' || element.type === 'circle' || element.type === 'triangle') {
        propertiesHtml += `
            <div class="space-y-3 p-3 bg-green-50 rounded-lg">
                <h4 class="text-sm font-semibold text-gray-800">Shape Properties</h4>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Fill Color</label>
                    <input type="color" value="${element.fill || '#ffffff'}" onchange="updateElementProperty('fill', this.value)" 
                           class="w-full h-8 border border-gray-300 rounded cursor-pointer">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Border Color</label>
                    <input type="color" value="${element.stroke || '#000000'}" onchange="updateElementProperty('stroke', this.value)" 
                           class="w-full h-8 border border-gray-300 rounded cursor-pointer">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Border Width</label>
                    <input type="number" value="${element.strokeWidth || 1}" onchange="updateElementProperty('strokeWidth', this.value)" 
                           class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-primary-500">
                </div>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Opacity: <span class="font-medium">${Math.round((element.opacity || 1) * 100)}%</span></label>
                    <input type="range" min="0" max="1" step="0.1" value="${element.opacity || 1}" onchange="updateElementProperty('opacity', this.value)" 
                           class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                </div>
            </div>
        `;
    } else if (element.type === 'image') {
        propertiesHtml += `
            <div class="space-y-3 p-3 bg-purple-50 rounded-lg">
                <h4 class="text-sm font-semibold text-gray-800">Image Properties</h4>
                <div>
                    <label class="block text-xs text-gray-600 mb-1">Opacity: <span class="font-medium">${Math.round((element.opacity || 1) * 100)}%</span></label>
                    <input type="range" min="0" max="1" step="0.1" value="${element.opacity || 1}" onchange="updateElementProperty('opacity', this.value)" 
                           class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                </div>
                <div class="flex space-x-2">
                    <button onclick="cropImage()" class="flex-1 px-3 py-2 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                        <i class="fas fa-crop mr-1"></i>Crop
                    </button>
                    <button onclick="filterImage()" class="flex-1 px-3 py-2 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                        <i class="fas fa-adjust mr-1"></i>Filters
                    </button>
                </div>
            </div>
        `;
    }
    
    elementProperties.innerHTML = propertiesHtml;
    propertiesPanel.classList.remove('hidden');
}

// Hide properties panel
function hidePropertiesPanel() {
    const propertiesPanel = document.getElementById('properties-panel');
    if (propertiesPanel) {
        propertiesPanel.classList.add('hidden');
    }
    slideEditor.selectedElement = null;
}

// Update element property
function updateElementProperty(property, value) {
    if (!slideEditor.selectedElement) return;
    
    const element = slideEditor.selectedElement;
    
    // Convert value to appropriate type
    if (typeof element[property] === 'number') {
        value = parseFloat(value);
    } else if (typeof element[property] === 'boolean') {
        value = value === 'true' || value === true;
    }
    
    element.set(property, value);
    slideEditor.canvas.renderAll();
    saveToHistory('Property Updated');
    
    // Update properties panel to reflect changes
    showPropertiesPanel(element);
}

// Update element size
function updateElementSize(dimension, value) {
    if (!slideEditor.selectedElement) return;
    
    const element = slideEditor.selectedElement;
    const size = parseFloat(value);
    
    if (dimension === 'width') {
        const scale = size / element.width;
        element.set('scaleX', scale);
    } else if (dimension === 'height') {
        const scale = size / element.height;
        element.set('scaleY', scale);
    }
    
    slideEditor.canvas.renderAll();
    saveToHistory('Size Updated');
}

// Toolbar functions
function formatText(format) {
    const element = slideEditor.selectedElement;
    if (!element || element.type !== 'textbox') return;
    
    switch (format) {
        case 'bold':
            element.set('fontWeight', element.fontWeight === 'bold' ? 'normal' : 'bold');
            break;
        case 'italic':
            element.set('fontStyle', element.fontStyle === 'italic' ? 'normal' : 'italic');
            break;
        case 'underline':
            element.set('underline', !element.underline);
            break;
    }
    
    slideEditor.canvas.renderAll();
    saveToHistory('Text Formatted');
    showPropertiesPanel(element);
}

function changeFontSize(size) {
    const element = slideEditor.selectedElement;
    if (!element || element.type !== 'textbox') return;
    
    element.set('fontSize', parseInt(size));
    slideEditor.canvas.renderAll();
    saveToHistory('Font Size Changed');
    showPropertiesPanel(element);
}

function changeTextColor(color) {
    const element = slideEditor.selectedElement;
    if (!element || element.type !== 'textbox') return;
    
    element.set('fill', color);
    slideEditor.canvas.renderAll();
    saveToHistory('Text Color Changed');
}

function changeBackgroundColor(color) {
    if (!slideEditor.canvas) return;
    
    slideEditor.canvas.setBackgroundColor(color, slideEditor.canvas.renderAll.bind(slideEditor.canvas));
    saveToHistory('Background Color Changed');
}

// Add text box
function addTextBox() {
    if (!slideEditor.canvas) return;
    
    const textbox = new fabric.Textbox('Click to edit text', {
        left: 100,
        top: 100,
        width: 200,
        fontSize: 18,
        fontFamily: 'Inter',
        fill: '#000000',
        editable: true
    });
    
    slideEditor.canvas.add(textbox);
    slideEditor.canvas.setActiveObject(textbox);
    saveToHistory('Text Box Added');
}

// Open image upload
function openImageUpload() {
    const modal = document.getElementById('image-upload-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

// Handle image upload
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        fabric.Image.fromURL(e.target.result, function(img) {
            img.set({
                left: 100,
                top: 100,
                scaleX: 0.5,
                scaleY: 0.5
            });
            
            slideEditor.canvas.add(img);
            slideEditor.canvas.setActiveObject(img);
            saveToHistory('Image Added');
        });
    };
    reader.readAsDataURL(file);
    
    // Close modal
    closeImageModal();
}

// Insert image from URL
function insertImageFromUrl() {
    const urlInput = document.getElementById('image-url-input');
    const url = urlInput.value.trim();
    
    if (!url) return;
    
    fabric.Image.fromURL(url, function(img) {
        img.set({
            left: 100,
            top: 100,
            scaleX: 0.5,
            scaleY: 0.5
        });
        
        slideEditor.canvas.add(img);
        slideEditor.canvas.setActiveObject(img);
        saveToHistory('Image Added');
    }, {
        crossOrigin: 'anonymous'
    });
    
    closeImageModal();
    urlInput.value = '';
}

// Add shape
function addShape() {
    // For simplicity, just add a rectangle
    insertShape('rectangle');
}

// Insert shape
function insertShape(shapeType) {
    if (!slideEditor.canvas) return;
    
    let shape;
    
    switch (shapeType) {
        case 'rectangle':
            shape = new fabric.Rect({
                left: 100,
                top: 100,
                width: 100,
                height: 60,
                fill: '#3b82f6',
                stroke: '#1e40af',
                strokeWidth: 2
            });
            break;
        case 'circle':
            shape = new fabric.Circle({
                left: 100,
                top: 100,
                radius: 50,
                fill: '#10b981',
                stroke: '#059669',
                strokeWidth: 2
            });
            break;
        case 'triangle':
            shape = new fabric.Triangle({
                left: 100,
                top: 100,
                width: 80,
                height: 80,
                fill: '#f59e0b',
                stroke: '#d97706',
                strokeWidth: 2
            });
            break;
    }
    
    if (shape) {
        slideEditor.canvas.add(shape);
        slideEditor.canvas.setActiveObject(shape);
        saveToHistory('Shape Added');
    }
}

// Add chart (placeholder)
function addChart() {
    addTextBox(); // For now, just add a text box
}

// Alignment functions
function alignElements(alignment) {
    const activeObjects = slideEditor.canvas.getActiveObjects();
    if (activeObjects.length < 2) return;
    
    const first = activeObjects[0];
    activeObjects.forEach(obj => {
        if (obj === first) return;
        
        switch (alignment) {
            case 'left':
                obj.set('left', first.left);
                break;
            case 'center':
                obj.set('left', first.left + (first.width - obj.width) / 2);
                break;
            case 'right':
                obj.set('left', first.left + first.width - obj.width);
                break;
        }
    });
    
    slideEditor.canvas.renderAll();
    saveToHistory('Elements Aligned');
}

// Layer functions
function bringToFront() {
    const activeObject = slideEditor.canvas.getActiveObject();
    if (activeObject) {
        activeObject.bringToFront();
        saveToHistory('Brought to Front');
    }
}

function sendToBack() {
    const activeObject = slideEditor.canvas.getActiveObject();
    if (activeObject) {
        activeObject.sendToBack();
        saveToHistory('Sent to Back');
    }
}

// Duplicate element
function duplicateElement() {
    const activeObject = slideEditor.canvas.getActiveObject();
    if (activeObject) {
        activeObject.clone(function(cloned) {
            cloned.set({
                left: cloned.left + 20,
                top: cloned.top + 20,
            });
            slideEditor.canvas.add(cloned);
            slideEditor.canvas.setActiveObject(cloned);
            saveToHistory('Element Duplicated');
        });
    }
}

// Delete selected element
function deleteSelected() {
    const activeObject = slideEditor.canvas.getActiveObject();
    if (activeObject) {
        slideEditor.canvas.remove(activeObject);
        saveToHistory('Element Deleted');
        hidePropertiesPanel();
    }
}

// Load slide into canvas
function loadSlideIntoCanvas(slide) {
    if (!slideEditor.canvas || !slide) return;
    
    const canvas = slideEditor.canvas;
    
    // Clear existing objects
    canvas.clear();
    
    // Set canvas background
    if (slide.background_color) {
        canvas.setBackgroundColor(slide.background_color, canvas.renderAll.bind(canvas));
    }
    
    // Load slide elements into canvas
    if (slide.elements && slide.elements.length > 0) {
        slide.elements.forEach(element => {
            loadElementIntoCanvas(element);
        });
    }
    
    canvas.renderAll();
}

// Load individual element into canvas
function loadElementIntoCanvas(element) {
    if (!slideEditor.canvas) return;
    
    const canvas = slideEditor.canvas;
    let fabricObject;
    
    try {
        const left = element.position ? element.position.x || 100 : 100;
        const top = element.position ? element.position.y || 100 : 100;
        const width = element.size ? element.size.width || 200 : 200;
        const height = element.size ? element.size.height || 50 : 50;
        
        switch (element.type) {
            case 'text':
            case 'textbox':
                fabricObject = new fabric.Textbox(element.content || 'Sample text', {
                    left: left,
                    top: top,
                    width: width,
                    fontSize: element.font_size || 18,
                    fontFamily: element.font_family || 'Inter',
                    fill: element.color || '#000000',
                    fontWeight: element.font_weight || 'normal',
                    fontStyle: element.font_style || 'normal',
                    textAlign: element.text_align || 'left',
                    editable: true
                });
                break;
                
            case 'image':
                if (element.content || element.src) {
                    fabric.Image.fromURL(element.content || element.src, function(img) {
                        img.set({
                            left: left,
                            top: top,
                            scaleX: width / img.width,
                            scaleY: height / img.height
                        });
                        canvas.add(img);
                        canvas.renderAll();
                    });
                    return;
                }
                break;
                
            default:
                fabricObject = new fabric.Textbox(element.content || element.placeholder_name || 'Text', {
                    left: left,
                    top: top,
                    width: width,
                    fontSize: 16,
                    fontFamily: 'Inter',
                    fill: '#000000',
                    editable: true
                });
        }
        
        if (fabricObject) {
            fabricObject.set({
                elementId: element.element_id,
                placeholderName: element.placeholder_name,
                originalType: element.type
            });
            
            canvas.add(fabricObject);
        }
        
    } catch (error) {
        console.error('Error loading element into canvas:', error);
    }
}

// Save to history
function saveToHistory(action) {
    if (!slideEditor.canvas) return;
    
    const state = JSON.stringify(slideEditor.canvas.toJSON());
    
    slideEditor.history = slideEditor.history.slice(0, slideEditor.historyIndex + 1);
    slideEditor.history.push({ state, action, timestamp: new Date() });
    slideEditor.historyIndex++;
    
    if (slideEditor.history.length > 50) {
        slideEditor.history.shift();
        slideEditor.historyIndex--;
    }
}

// Keyboard shortcuts
function handleKeyboardShortcuts(e) {
    if (!slideEditor.canvas || slideEditor.isEditingText) return;
    
    if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
            case 'z':
                e.preventDefault();
                if (e.shiftKey) {
                    redo();
                } else {
                    undo();
                }
                break;
            case 'c':
                e.preventDefault();
                copy();
                break;
            case 'v':
                e.preventDefault();
                paste();
                break;
            case 'd':
                e.preventDefault();
                duplicateElement();
                break;
        }
    } else if (e.key === 'Delete') {
        e.preventDefault();
        deleteSelected();
    }
}

// Undo/Redo
function undo() {
    if (slideEditor.historyIndex > 0) {
        slideEditor.historyIndex--;
        const historyState = slideEditor.history[slideEditor.historyIndex];
        slideEditor.canvas.loadFromJSON(historyState.state, function() {
            slideEditor.canvas.renderAll();
        });
    }
}

function redo() {
    if (slideEditor.historyIndex < slideEditor.history.length - 1) {
        slideEditor.historyIndex++;
        const historyState = slideEditor.history[slideEditor.historyIndex];
        slideEditor.canvas.loadFromJSON(historyState.state, function() {
            slideEditor.canvas.renderAll();
        });
    }
}

// Copy/Paste
function copy() {
    const activeObject = slideEditor.canvas.getActiveObject();
    if (activeObject) {
        activeObject.clone(function(cloned) {
            slideEditor.clipboard = cloned;
        });
    }
}

function paste() {
    if (slideEditor.clipboard) {
        slideEditor.clipboard.clone(function(cloned) {
            cloned.set({
                left: cloned.left + 20,
                top: cloned.top + 20,
            });
            slideEditor.canvas.add(cloned);
            slideEditor.canvas.setActiveObject(cloned);
            slideEditor.canvas.renderAll();
            saveToHistory('Element Pasted');
        });
    }
}

// Enter text edit mode
function enterTextEditMode(textObject) {
    slideEditor.isEditingText = true;
    textObject.enterEditing();
}

// Modal handlers
function setupModalHandlers() {
    // Image modal
    const imageModal = document.getElementById('image-upload-modal');
    const cancelImageBtn = document.getElementById('cancel-image-btn');
    
    if (cancelImageBtn) {
        cancelImageBtn.addEventListener('click', closeImageModal);
    }
    
    // Click outside modal to close
    if (imageModal) {
        imageModal.addEventListener('click', function(e) {
            if (e.target === imageModal) {
                closeImageModal();
            }
        });
    }
}

function closeImageModal() {
    const modal = document.getElementById('image-upload-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Export functions for global use
window.slideEditor = slideEditor;
window.loadSlideIntoCanvas = loadSlideIntoCanvas;
window.formatText = formatText;
window.changeFontSize = changeFontSize;
window.changeTextColor = changeTextColor;
window.changeBackgroundColor = changeBackgroundColor;
window.addTextBox = addTextBox;
window.openImageUpload = openImageUpload;
window.insertImageFromUrl = insertImageFromUrl;
window.addShape = addShape;
window.insertShape = insertShape;
window.addChart = addChart;
window.alignElements = alignElements;
window.bringToFront = bringToFront;
window.sendToBack = sendToBack;
window.duplicateElement = duplicateElement;
window.deleteSelected = deleteSelected;
window.updateElementProperty = updateElementProperty;
window.updateElementSize = updateElementSize;