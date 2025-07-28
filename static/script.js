// Global state
let selectedTemplate = null;
let templates = [];
let placeholders = [];
let currentPresentation = null;
let currentSlideIndex = 0;
let isEditMode = false;
let viewerMode = 'slides'; // 'slides', 'text', 'fullscreen'

// API base URL - automatically detect based on current location
const API_BASE_URL = window.location.origin;

// DOM elements
const templateSection = document.getElementById('template-section');
const promptSection = document.getElementById('prompt-section');
const outputSection = document.getElementById('output-section');
const templatesGrid = document.getElementById('templates-grid');
const templatesLoading = document.getElementById('templates-loading');
const selectedTemplateInfo = document.getElementById('selected-template-info');
const placeholdersList = document.getElementById('placeholders-list');
const promptInput = document.getElementById('prompt-input');
const charCount = document.getElementById('char-count');
const generationStatus = document.getElementById('generation-status');
const outputContent = document.getElementById('output-content');
const contentPreview = document.getElementById('content-preview');
const errorModal = document.getElementById('error-modal');
const errorMessage = document.getElementById('error-message');

// Progress indicator
const progressSteps = document.querySelectorAll('.progress-step');

// Buttons
const continueToPromptBtn = document.getElementById('continue-to-prompt');
const backToTemplatesBtn = document.getElementById('back-to-templates');
const generateContentBtn = document.getElementById('generate-content');
const startOverBtn = document.getElementById('start-over');
const closeErrorModalBtn = document.getElementById('close-error-modal');
const errorOkBtn = document.getElementById('error-ok-btn');

// Presentation viewer elements
const viewModeBtn = document.getElementById('view-mode-btn');
const editModeBtn = document.getElementById('edit-mode-btn');
const savePresentationBtn = document.getElementById('save-presentation');
const exportPresentationBtn = document.getElementById('export-presentation');
const slidesThumbnails = document.getElementById('slides-thumbnails');
const currentSlideDiv = document.getElementById('current-slide');
const editPanel = document.getElementById('edit-panel');
const editableElements = document.getElementById('editable-elements');
const slideCount = document.getElementById('slide-count');

// Presentation viewer mode elements
const presentationViewerModes = document.getElementById('presentation-viewer-modes');
const slidesModeBtn = document.getElementById('slides-mode-btn');
const textModeBtn = document.getElementById('text-mode-btn');
const fullscreenModeBtn = document.getElementById('fullscreen-mode-btn');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    continueToPromptBtn.addEventListener('click', goToPromptSection);
    backToTemplatesBtn.addEventListener('click', goToTemplateSection);
    generateContentBtn.addEventListener('click', generateContent);
    startOverBtn.addEventListener('click', startOver);
    closeErrorModalBtn.addEventListener('click', closeErrorModal);
    errorOkBtn.addEventListener('click', closeErrorModal);
    
    // Presentation viewer event listeners
    if (viewModeBtn) viewModeBtn.addEventListener('click', () => setViewMode(false));
    if (editModeBtn) editModeBtn.addEventListener('click', () => setViewMode(true));
    if (savePresentationBtn) savePresentationBtn.addEventListener('click', savePresentation);
    
    // Presentation viewer mode listeners
    if (slidesModeBtn) slidesModeBtn.addEventListener('click', () => setViewerMode('slides'));
    if (textModeBtn) textModeBtn.addEventListener('click', () => setViewerMode('text'));
    if (fullscreenModeBtn) fullscreenModeBtn.addEventListener('click', () => setViewerMode('fullscreen'));
    
    // Character counter for prompt input
    promptInput.addEventListener('input', updateCharCounter);
    
    // Close modal when clicking outside
    errorModal.addEventListener('click', function(e) {
        if (e.target === errorModal) {
            closeErrorModal();
        }
    });
}

// Load templates from API
async function loadTemplates() {
    try {
        templatesLoading.style.display = 'block';
        templatesGrid.style.display = 'none';
        
        const response = await fetch(`${API_BASE_URL}/templates`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        templates = await response.json();
        displayTemplates(templates);
        
        templatesLoading.style.display = 'none';
        templatesGrid.style.display = 'grid';
    } catch (error) {
        console.error('Error loading templates:', error);
        templatesLoading.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                Failed to load templates. Please check your connection and try again.
                <br><br>
                <button class="btn btn-primary" onclick="loadTemplates()">
                    <i class="fas fa-redo"></i>
                    Retry
                </button>
            </div>
        `;
    }
}

// Display templates in the grid
function displayTemplates(templates) {
    if (templates.length === 0) {
        templatesGrid.innerHTML = `
            <div class="error-message">
                <i class="fas fa-info-circle"></i>
                No templates found. Please make sure templates are available in your Google Drive.
            </div>
        `;
        return;
    }
    
    templatesGrid.innerHTML = templates.map(template => `
        <div class="template-card" data-template-id="${template.id}" onclick="selectTemplate('${template.id}')">
            <div class="template-thumbnail">
                ${template.thumbnailLink ? 
                    `<img src="${template.thumbnailLink}" alt="${template.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                     <i class="fas fa-presentation" style="display: none;"></i>` :
                    `<i class="fas fa-presentation"></i>`
                }
            </div>
            <h3>${template.name}</h3>
            <p>Click to select this template</p>
        </div>
    `).join('');
}

// Select a template
function selectTemplate(templateId) {
    // Remove previous selection
    document.querySelectorAll('.template-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Add selection to clicked template
    const selectedCard = document.querySelector(`[data-template-id="${templateId}"]`);
    selectedCard.classList.add('selected');
    
    // Store selected template
    selectedTemplate = templates.find(t => t.id === templateId);
    
    // Enable continue button
    continueToPromptBtn.disabled = false;
    
    console.log('Selected template:', selectedTemplate);
}

// Navigate to prompt section
async function goToPromptSection() {
    if (!selectedTemplate) {
        showError('Please select a template first.');
        return;
    }
    
    try {
        // Load placeholders for the selected template
        await loadPlaceholders(selectedTemplate.id);
        
        // Update UI
        showSection('prompt');
        updateProgressIndicator(2);
        
        // Show selected template info
        selectedTemplateInfo.innerHTML = `
            <h3>Selected Template: ${selectedTemplate.name}</h3>
            <p>Fill in the prompt below to generate content for this template.</p>
        `;
        
        // Display placeholders
        displayPlaceholders(placeholders);
        
    } catch (error) {
        console.error('Error loading placeholders:', error);
        showError('Failed to load template placeholders. Please try again.');
    }
}

// Load placeholders for a template
async function loadPlaceholders(templateId) {
    const response = await fetch(`${API_BASE_URL}/templates/${templateId}/placeholders`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    placeholders = await response.json();
    console.log('Loaded placeholders:', placeholders);
}

// Display placeholders
function displayPlaceholders(placeholders) {
    if (placeholders.length === 0) {
        placeholdersList.innerHTML = `
            <div class="error-message">
                <i class="fas fa-info-circle"></i>
                No placeholders found in this template.
            </div>
        `;
        return;
    }
    
    placeholdersList.innerHTML = placeholders.map(placeholder => `
        <div class="placeholder-item">
            <div class="placeholder-name">{{${placeholder.name}}}</div>
            <div class="placeholder-instruction">${placeholder.instruction || 'No specific instructions'}</div>
            <div class="placeholder-meta">
                Slide ${placeholder.slide_index || 'Unknown'} • ${placeholder.element_type || 'text'}
                ${placeholder.min_words || placeholder.max_words ? 
                    `• ${placeholder.min_words || 0}-${placeholder.max_words || '∞'} words` : 
                    ''
                }
            </div>
        </div>
    `).join('');
}

// Navigate back to template section
function goToTemplateSection() {
    showSection('template');
    updateProgressIndicator(1);
}

// Generate content
async function generateContent() {
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showError('Please enter a description of your business or idea.');
        return;
    }
    
    if (!selectedTemplate) {
        showError('Please select a template first.');
        return;
    }
    
    try {
        // Show output section with loading state
        showSection('output');
        updateProgressIndicator(3);
        
        generationStatus.style.display = 'block';
        outputContent.style.display = 'none';
        
        // Add dynamic loading messages
        showLoadingMessages();
        
        // Make API call to generate content
        const response = await fetch(`${API_BASE_URL}/generate-content`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                template_id: selectedTemplate.id,
                prompt: prompt
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Generation result:', result);
        
        // Hide loading and show results
        generationStatus.style.display = 'none';
        outputContent.style.display = 'block';
        
        // Display the results
        displayGenerationResults(result);
        
        // Load presentation slides if we have a presentation ID
        if (result.presentation_id) {
            // Add the generated content to the result for the slides
            result.generated_content = result.results;
            loadPresentationSlides(result.presentation_id, result.generated_content);
            
            // Initialize chat mode for the new presentation
            onPresentationGenerated(result);
        }
        
    } catch (error) {
        console.error('Error generating content:', error);
        generationStatus.style.display = 'none';
        showError(`Failed to generate content: ${error.message}`);
    }
}

// Display generation results
function displayGenerationResults(result) {
    // Update presentation info - check if elements exist first
    const presentationTitle = document.getElementById('presentation-title');
    const presentationDescription = document.getElementById('presentation-description');
    const viewPresentationBtn = document.getElementById('view-presentation');
    const editPresentationBtn = document.getElementById('edit-presentation');
    
    if (presentationTitle) {
        presentationTitle.textContent = `Generated Presentation - ${new Date().toLocaleDateString()}`;
    }
    
    // Check if this is demo mode
    const isDemoMode = result.presentation_id && result.presentation_id.startsWith('demo-');
    
    if (isDemoMode) {
        if (presentationDescription) {
            presentationDescription.textContent = 'Demo presentation generated successfully! In production mode, this would create an actual Google Slides presentation.';
        }
        if (viewPresentationBtn) viewPresentationBtn.style.display = 'none';
        if (editPresentationBtn) editPresentationBtn.style.display = 'none';
    } else {
        if (presentationDescription) {
            presentationDescription.textContent = 'Your AI-generated presentation is ready to view and edit.';
        }
        
        if (viewPresentationBtn) {
            if (result.presentation_view_url && result.presentation_view_url !== '#demo-presentation') {
                viewPresentationBtn.href = result.presentation_view_url;
                viewPresentationBtn.style.display = 'inline-flex';
            } else {
                viewPresentationBtn.style.display = 'none';
            }
        }
        
        if (editPresentationBtn) {
            if (result.presentation_url && result.presentation_url !== '#demo-presentation') {
                editPresentationBtn.href = result.presentation_url;
                editPresentationBtn.style.display = 'inline-flex';
            } else {
                editPresentationBtn.style.display = 'none';
            }
        }
    }
    
    // Display generated content
    const contentPreview = document.getElementById('content-preview');
    if (contentPreview) {
        if (result.results && Object.keys(result.results).length > 0) {
            contentPreview.innerHTML = Object.entries(result.results).map(([placeholder, content]) => `
                <div class="content-item">
                    <h5>{{${placeholder}}}</h5>
                    <p>${content}</p>
                </div>
            `).join('');
        } else {
            contentPreview.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-info-circle"></i>
                    No content was generated. Please try again with a different prompt.
                </div>
            `;
        }
    }
    
    // Show any errors
    if (result.errors && result.errors.length > 0 && contentPreview) {
        // Filter out word count errors that are within tolerance
        const significantErrors = result.errors.filter(error => {
            // Only show word count errors if they're significantly off
            if (error.includes('word count') || error.includes('words, but')) {
                // Extract numbers from error message
                const numbers = error.match(/\d+/g);
                if (numbers && numbers.length >= 2) {
                    const actual = parseInt(numbers[0]);
                    const expected = parseInt(numbers[1]);
                    const difference = Math.abs(actual - expected);
                    // Only show if difference is more than 3 words
                    return difference > 3;
                }
            }
            return true; // Show all non-word-count errors
        });
        
        if (significantErrors.length > 0) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'warning-message';
            errorDiv.innerHTML = `
                <i class="fas fa-info-circle"></i>
                <strong>Content Notes:</strong>
                <ul>
                    ${significantErrors.map(error => `<li>${error}</li>`).join('')}
                </ul>
                <p><small>These are minor formatting notes and don't affect the presentation quality.</small></p>
            `;
            contentPreview.appendChild(errorDiv);
        }
    }
}

// Start over
function startOver() {
    // Reset state
    selectedTemplate = null;
    templates = [];
    placeholders = [];
    
    // Reset UI
    promptInput.value = '';
    updateCharCounter();
    continueToPromptBtn.disabled = true;
    
    // Go back to template section
    showSection('template');
    updateProgressIndicator(1);
    
    // Reload templates
    loadTemplates();
}

// Show specific section
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.step-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(`${sectionName}-section`);
    targetSection.classList.add('active');
}

// Update progress indicator
function updateProgressIndicator(activeStep) {
    progressSteps.forEach((step, index) => {
        if (index + 1 <= activeStep) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

// Example prompts
const examplePrompts = [
    "We're developing an AI-powered fitness app that creates personalized workout plans based on user goals, fitness level, and available equipment. Our target market includes busy professionals aged 25-45 who want effective workouts but have limited time. The app uses machine learning to adapt workouts based on user feedback and progress. Our business model includes freemium subscriptions with premium features like nutrition planning and personal trainer consultations.",
    
    "Our company sells sustainable home products through an online marketplace, focusing on eco-friendly alternatives to everyday items. We target environmentally conscious consumers who are willing to pay premium prices for sustainable products. Our value proposition includes carbon-neutral shipping, plastic-free packaging, and partnerships with certified sustainable manufacturers. Revenue comes from direct sales with 40% gross margins and affiliate partnerships.",
    
    "We provide digital marketing consulting services for small businesses, specializing in social media strategy, content creation, and paid advertising campaigns. Our target clients are local businesses with 10-50 employees who lack in-house marketing expertise. We offer monthly retainer packages ranging from $2,000 to $10,000, including strategy development, campaign management, and performance reporting. Our competitive advantage is our focus on measurable ROI and local market expertise."
];

// Fill example prompt
function fillExamplePrompt(index) {
    if (index >= 0 && index < examplePrompts.length) {
        promptInput.value = examplePrompts[index];
        updateCharCounter();
        
        // Close the details element
        const details = document.querySelector('.prompt-help details');
        if (details) {
            details.open = false;
        }
        
        // Add visual feedback
        promptInput.focus();
        promptInput.style.borderColor = '#667eea';
        setTimeout(() => {
            promptInput.style.borderColor = '';
        }, 1000);
    }
}

// Update character counter
function updateCharCounter() {
    const count = promptInput.value.length;
    charCount.textContent = count;
    
    // Add visual feedback for character count
    if (count < 50) {
        charCount.style.color = '#c33';
    } else if (count < 200) {
        charCount.style.color = '#f90';
    } else {
        charCount.style.color = '#363';
    }
}

// Show error modal
function showError(message) {
    errorMessage.textContent = message;
    errorModal.style.display = 'block';
}

// Show about information
function showAbout() {
    const aboutText = `
AI Pitchdeck Generator

This application uses Google's Gemini AI to automatically generate professional presentation content based on your business description.

Features:
• Template-based content generation
• AI-powered content creation
• Google Slides integration
• Responsive design
• Demo mode for testing

Technology Stack:
• Frontend: HTML, CSS, JavaScript
• Backend: FastAPI (Python)
• AI: Google Gemini
• Integration: Google Slides API

Version: 1.0.0
    `;
    
    showError(aboutText.trim());
}

// Close error modal
function closeErrorModal() {
    errorModal.style.display = 'none';
}

// Show dynamic loading messages
function showLoadingMessages() {
    const loadingMessages = [
        "Analyzing your business description...",
        "Generating creative content...",
        "Optimizing for your template...",
        "Finalizing your presentation..."
    ];
    
    const progressText = document.querySelector('.progress-text');
    let messageIndex = 0;
    
    const messageInterval = setInterval(() => {
        if (progressText && generationStatus.style.display !== 'none') {
            progressText.textContent = loadingMessages[messageIndex];
            messageIndex = (messageIndex + 1) % loadingMessages.length;
        } else {
            clearInterval(messageInterval);
        }
    }, 2000);
}

// Utility function to format text
function formatText(text, maxLength = 200) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Add some visual feedback for better UX
document.addEventListener('click', function(e) {
    // Add ripple effect to buttons
    if (e.target.classList.contains('btn')) {
        const button = e.target;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
});

// Add ripple effect CSS
const style = document.createElement('style');
style.textContent = `
    .btn {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ===== PRESENTATION VIEWER FUNCTIONS =====

// Load presentation slides data
async function loadPresentationSlides(presentationId, generatedContent = null) {
    try {
        // Show loading state
        if (currentSlideDiv) {
            currentSlideDiv.innerHTML = `
                <div class="slide-loading">
                    <i class="fas fa-spinner"></i>
                    <span>Loading presentation slides...</span>
                </div>
            `;
        }
        
        const response = await fetch(`${API_BASE_URL}/presentations/${presentationId}/slides`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        currentPresentation = await response.json();
        console.log('Loaded presentation:', currentPresentation);
        
        // If we have generated content, update the slide elements with actual content
        if (generatedContent && presentationId.startsWith('demo-')) {
            updateDemoSlidesWithGeneratedContent(currentPresentation, generatedContent);
        }
        
        // Show presentation viewer modes
        if (presentationViewerModes) {
            presentationViewerModes.style.display = 'flex';
        }
        
        // Display slides
        displaySlidesThumbnails();
        
        // Show first slide
        if (currentPresentation.slides.length > 0) {
            showSlide(0);
        }
        
        // Update export link
        if (exportPresentationBtn && currentPresentation.presentation_id) {
            if (!currentPresentation.presentation_id.startsWith('demo-')) {
                exportPresentationBtn.href = `https://docs.google.com/presentation/d/${currentPresentation.presentation_id}/edit`;
                exportPresentationBtn.style.display = 'inline-flex';
            } else {
                exportPresentationBtn.style.display = 'none';
            }
        }
        
    } catch (error) {
        console.error('Error loading presentation slides:', error);
        showError(`Failed to load presentation slides: ${error.message}`);
    }
}

// Display slides thumbnails in sidebar
function displaySlidesThumbnails() {
    if (!currentPresentation || !slidesThumbnails) return;
    
    // Update slide count if element exists
    const slideCountElement = document.getElementById('slide-count');
    if (slideCountElement) {
        slideCountElement.textContent = currentPresentation.slides.length;
    }
    
    const isRealPresentation = currentPresentation.presentation_id && !currentPresentation.presentation_id.startsWith('demo-');
    
    slidesThumbnails.innerHTML = currentPresentation.slides.map((slide, index) => {
        let thumbnailContent = '';
        
        if (isRealPresentation && slide.thumbnail_url) {
            // Use actual slide thumbnail for real presentations
            thumbnailContent = `
                <div class="slide-thumbnail-image">
                    <img src="${slide.thumbnail_url}" alt="Slide ${slide.slide_index}" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="slide-thumbnail-fallback" style="display: none;">
                        <i class="fas fa-file-powerpoint"></i>
                        <span>Slide ${slide.slide_index}</span>
                    </div>
                </div>
            `;
        } else {
            // Use text-based thumbnail for demo presentations
            thumbnailContent = `
                <div class="slide-number">Slide ${slide.slide_index}</div>
                <div class="slide-title">${slide.title || 'Untitled'}</div>
            `;
        }
        
        return `
            <div class="slide-thumbnail ${isRealPresentation ? 'real-presentation' : ''} ${index === currentSlideIndex ? 'active' : ''}" 
                 onclick="showSlide(${index})" 
                 data-slide-index="${index}">
                ${thumbnailContent}
            </div>
        `;
    }).join('');
}

// Show specific slide
function showSlide(index) {
    if (!currentPresentation || index < 0 || index >= currentPresentation.slides.length) return;
    
    currentSlideIndex = index;
    const slide = currentPresentation.slides[index];
    
    // Update thumbnail selection
    document.querySelectorAll('.slide-thumbnail').forEach((thumb, i) => {
        thumb.classList.toggle('active', i === index);
    });
    
    // Display slide content
    displaySlideContent(slide);
    
    // Update edit panel if in edit mode
    if (isEditMode) {
        displayEditPanel(slide);
    }
}

// Display slide content in the main viewer
function displaySlideContent(slide) {
    if (!currentSlideDiv) return;
    
    // Check viewer mode and presentation type
    const isRealPresentation = currentPresentation.presentation_id && !currentPresentation.presentation_id.startsWith('demo-');
    
    if (viewerMode === 'fullscreen' && isRealPresentation) {
        displayFullPresentationEmbed();
    } else if (viewerMode === 'slides' && isRealPresentation) {
        displayGoogleSlidesEmbed(slide);
    } else {
        displayTextSlideContent(slide);
    }
}

// Display actual Google Slides embed
function displayGoogleSlidesEmbed(slide) {
    const presentationId = currentPresentation.presentation_id;
    const slideId = slide.slide_id;
    
    // Create embed URL for specific slide
    const embedUrl = `https://docs.google.com/presentation/d/${presentationId}/embed?start=false&loop=false&delayms=3000&slide=id.${slideId}`;
    
    let slideHtml = `
        <div class="google-slides-container">
            <div class="slide-header">
                <h3>${slide.title || `Slide ${currentSlideIndex + 1}`}</h3>
                <div class="slide-controls">
                    ${isEditMode ? `<button class="btn btn-sm btn-primary" onclick="openSlideForEditing('${slideId}')">
                        <i class="fas fa-edit"></i> Edit in Google Slides
                    </button>` : ''}
                </div>
            </div>
            <div class="slide-embed-wrapper">
                <iframe 
                    src="${embedUrl}" 
                    frameborder="0" 
                    width="100%" 
                    height="500" 
                    allowfullscreen="true" 
                    mozallowfullscreen="true" 
                    webkitallowfullscreen="true"
                    class="google-slides-iframe">
                </iframe>
            </div>
        </div>
    `;
    
    // Add navigation
    slideHtml += `
        <div class="slide-navigation">
            <button class="slide-nav-btn" onclick="previousSlide()" ${currentSlideIndex === 0 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
            <span class="slide-indicator">${currentSlideIndex + 1} / ${currentPresentation.slides.length}</span>
            <button class="slide-nav-btn" onclick="nextSlide()" ${currentSlideIndex === currentPresentation.slides.length - 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;
    
    currentSlideDiv.innerHTML = slideHtml;
}

// Display text-based slide content (for demo mode)
function displayTextSlideContent(slide) {
    let slideHtml = `<div class="slide-content">`;
    
    // Add slide title
    if (slide.title) {
        slideHtml += `<h2 class="slide-title">${slide.title}</h2>`;
    }
    
    // Add slide elements
    slide.elements.forEach(element => {
        const elementClass = isEditMode && element.editable ? 'slide-element editable' : 'slide-element';
        const clickHandler = isEditMode && element.editable ? `onclick="editElement('${element.element_id}')"` : '';
        
        slideHtml += `
            <div class="${elementClass}" 
                 data-element-id="${element.element_id}" 
                 ${clickHandler}>
                ${formatSlideContent(element.content, element.type)}
            </div>
        `;
    });
    
    slideHtml += `</div>`;
    
    // Add navigation
    slideHtml += `
        <div class="slide-navigation">
            <button class="slide-nav-btn" onclick="previousSlide()" ${currentSlideIndex === 0 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
            <span class="slide-indicator">${currentSlideIndex + 1} / ${currentPresentation.slides.length}</span>
            <button class="slide-nav-btn" onclick="nextSlide()" ${currentSlideIndex === currentPresentation.slides.length - 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;
    
    currentSlideDiv.innerHTML = slideHtml;
}

// Open specific slide for editing in Google Slides
function openSlideForEditing(slideId) {
    const presentationId = currentPresentation.presentation_id;
    const editUrl = `https://docs.google.com/presentation/d/${presentationId}/edit#slide=id.${slideId}`;
    window.open(editUrl, '_blank');
}

// Format slide content based on type
function formatSlideContent(content, type) {
    if (!content) return '<p class="empty-content">No content</p>';
    
    switch (type) {
        case 'title':
            return `<h1>${content}</h1>`;
        case 'subtitle':
            return `<h2 class="slide-subtitle">${content}</h2>`;
        case 'bullet_points':
            const points = content.split('\n').filter(line => line.trim());
            return `<ul class="slide-bullet-points">${points.map(point => `<li>${point}</li>`).join('')}</ul>`;
        default:
            return `<div class="slide-text">${content.replace(/\n/g, '<br>')}</div>`;
    }
}

// Set view/edit mode
function setViewMode(editMode) {
    isEditMode = editMode;
    
    // Update button states
    if (viewModeBtn && editModeBtn) {
        viewModeBtn.classList.toggle('active', !editMode);
        viewModeBtn.classList.toggle('btn-primary', !editMode);
        viewModeBtn.classList.toggle('btn-secondary', editMode);
        
        editModeBtn.classList.toggle('active', editMode);
        editModeBtn.classList.toggle('btn-primary', editMode);
        editModeBtn.classList.toggle('btn-secondary', !editMode);
    }
    
    // Show/hide edit panel and save button
    if (editPanel) {
        editPanel.style.display = editMode ? 'block' : 'none';
    }
    if (savePresentationBtn) {
        savePresentationBtn.style.display = editMode ? 'inline-flex' : 'none';
    }
    
    // Refresh current slide display
    if (currentPresentation && currentPresentation.slides[currentSlideIndex]) {
        showSlide(currentSlideIndex);
    }
}

// Display edit panel for current slide
function displayEditPanel(slide) {
    if (!editableElements) return;
    
    editableElements.innerHTML = slide.elements
        .filter(element => element.editable)
        .map(element => `
            <div class="element-editor" data-element-id="${element.element_id}">
                <label for="edit-${element.element_id}">
                    ${element.placeholder_name || element.element_id} (${element.type})
                </label>
                <textarea 
                    id="edit-${element.element_id}" 
                    rows="4"
                    placeholder="Enter content for this element..."
                >${element.content}</textarea>
            </div>
        `).join('');
}

// Edit element (when clicked in edit mode)
function editElement(elementId) {
    const editInput = document.getElementById(`edit-${elementId}`);
    if (editInput) {
        editInput.focus();
        editInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Save presentation changes
async function savePresentation() {
    if (!currentPresentation || !isEditMode) return;
    
    try {
        const slide = currentPresentation.slides[currentSlideIndex];
        const updates = {};
        
        // Collect changes from edit panel
        slide.elements.forEach(element => {
            if (element.editable) {
                const editInput = document.getElementById(`edit-${element.element_id}`);
                if (editInput && editInput.value !== element.content) {
                    updates[element.element_id] = editInput.value;
                    // Update local data
                    element.content = editInput.value;
                }
            }
        });
        
        if (Object.keys(updates).length === 0) {
            showError('No changes to save.');
            return;
        }
        
        // Save to backend
        const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/slides/${slide.slide_id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                slide_id: slide.slide_id,
                elements: updates
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Refresh slide display
            showSlide(currentSlideIndex);
            
            // Show success message
            const successDiv = document.createElement('div');
            successDiv.className = 'success-message';
            successDiv.innerHTML = '<i class="fas fa-check"></i> Changes saved successfully!';
            editPanel.insertBefore(successDiv, editPanel.firstChild);
            
            setTimeout(() => {
                successDiv.remove();
            }, 3000);
        } else {
            throw new Error(result.message || 'Failed to save changes');
        }
        
    } catch (error) {
        console.error('Error saving presentation:', error);
        showError(`Failed to save changes: ${error.message}`);
    }
}

// Navigation functions
function previousSlide() {
    if (currentSlideIndex > 0) {
        showSlide(currentSlideIndex - 1);
    }
}

function nextSlide() {
    if (currentSlideIndex < currentPresentation.slides.length - 1) {
        showSlide(currentSlideIndex + 1);
    }
}

// Keyboard navigation
document.addEventListener('keydown', function(e) {
    if (!currentPresentation) return;
    
    switch(e.key) {
        case 'ArrowLeft':
            if (!isEditMode) {
                e.preventDefault();
                previousSlide();
            }
            break;
        case 'ArrowRight':
            if (!isEditMode) {
                e.preventDefault();
                nextSlide();
            }
            break;
        case 'Escape':
            if (isEditMode) {
                setViewMode(false);
            }
            break;
    }
});

// Update demo slides with actual generated content
function updateDemoSlidesWithGeneratedContent(presentation, generatedContent) {
    presentation.slides.forEach(slide => {
        slide.elements.forEach(element => {
            if (element.placeholder_name && generatedContent[element.placeholder_name]) {
                element.content = generatedContent[element.placeholder_name];
            }
        });
    });
}

// Set presentation viewer mode
function setViewerMode(mode) {
    viewerMode = mode;
    
    // Update button states
    if (slidesModeBtn && textModeBtn && fullscreenModeBtn) {
        slidesModeBtn.classList.toggle('active', mode === 'slides');
        textModeBtn.classList.toggle('active', mode === 'text');
        fullscreenModeBtn.classList.toggle('active', mode === 'fullscreen');
    }
    
    // Update display based on mode
    if (currentPresentation && currentPresentation.slides[currentSlideIndex]) {
        if (mode === 'fullscreen') {
            // Hide sidebar in fullscreen mode
            const slidesSidebar = document.querySelector('.slides-sidebar');
            if (slidesSidebar) slidesSidebar.style.display = 'none';
        } else {
            // Show sidebar in other modes
            const slidesSidebar = document.querySelector('.slides-sidebar');
            if (slidesSidebar) slidesSidebar.style.display = 'block';
        }
        
        showSlide(currentSlideIndex);
    }
}

// Display full presentation embed
function displayFullPresentationEmbed() {
    const presentationId = currentPresentation.presentation_id;
    const fullEmbedUrl = `https://docs.google.com/presentation/d/${presentationId}/embed?start=false&loop=false&delayms=3000`;
    
    let slideHtml = `
        <div class="google-slides-container">
            <div class="slide-header">
                <h3>${currentPresentation.title}</h3>
                <div class="slide-controls">
                    <button class="btn btn-sm btn-primary" onclick="window.open('https://docs.google.com/presentation/d/${presentationId}/edit', '_blank')">
                        <i class="fas fa-external-link-alt"></i> Open in Google Slides
                    </button>
                </div>
            </div>
            <div class="slide-embed-wrapper" style="height: 600px;">
                <iframe 
                    src="${fullEmbedUrl}" 
                    frameborder="0" 
                    width="100%" 
                    height="100%" 
                    allowfullscreen="true" 
                    mozallowfullscreen="true" 
                    webkitallowfullscreen="true"
                    class="full-presentation-embed">
                </iframe>
            </div>
        </div>
    `;
    
    currentSlideDiv.innerHTML = slideHtml;
}

// ================================
// CHAT FUNCTIONALITY
// ================================

let chatThreadId = null;
let isChatMode = false;

// Chat DOM elements
const chatModeBtn = document.getElementById('chat-mode-btn');
const chatPanel = document.getElementById('chat-panel');
const chatMessages = document.getElementById('chat-messages');
const chatMessageInput = document.getElementById('chat-message-input');
const sendChatMessageBtn = document.getElementById('send-chat-message');
const quickActionBtns = document.querySelectorAll('.quick-action-btn');

// Initialize chat functionality
function initializeChatMode() {
    if (!chatModeBtn || !chatPanel) return;
    
    // Chat mode button click
    chatModeBtn.addEventListener('click', () => {
        if (isChatMode) {
            exitChatMode();
        } else {
            enterChatMode();
        }
    });
    
    // Send message button
    if (sendChatMessageBtn) {
        sendChatMessageBtn.addEventListener('click', sendChatMessage);
    }
    
    // Enter key in chat input
    if (chatMessageInput) {
        chatMessageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
    
    // Quick action buttons
    quickActionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            if (message) {
                chatMessageInput.value = message;
                sendChatMessage();
            }
        });
    });
}

// Enter chat mode
function enterChatMode() {
    if (!currentPresentation) {
        showError('No presentation available', 'Please generate a presentation first before using chat editing.');
        return;
    }
    
    isChatMode = true;
    
    // Update button states
    viewModeBtn.classList.remove('active');
    editModeBtn.classList.remove('active');
    chatModeBtn.classList.add('active');
    
    // Hide other panels
    editPanel.style.display = 'none';
    
    // Show chat panel
    chatPanel.style.display = 'block';
    
    // Initialize chat session if not already done
    if (!chatThreadId) {
        initializeChatSession();
    }
    
    // Focus on chat input
    if (chatMessageInput) {
        setTimeout(() => chatMessageInput.focus(), 100);
    }
}

// Exit chat mode
function exitChatMode() {
    isChatMode = false;
    
    // Update button states
    chatModeBtn.classList.remove('active');
    viewModeBtn.classList.add('active');
    
    // Hide chat panel
    chatPanel.style.display = 'none';
    
    // Reset to view mode
    isEditMode = false;
    editPanel.style.display = 'none';
}

// Initialize chat session
async function initializeChatSession() {
    if (!currentPresentation || !currentPresentation.presentation_id) {
        return;
    }
    
    try {
        showChatTyping();
        
        const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        hideChatTyping();
        
        if (response.ok) {
            chatThreadId = data.thread_id;
            
            // Add welcome message
            addChatMessage('assistant', data.message);
            
            console.log('Chat session initialized:', chatThreadId);
        } else {
            addChatMessage('system', `Error initializing chat: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        hideChatTyping();
        addChatMessage('system', `Error: ${error.message}`);
        console.error('Chat initialization error:', error);
    }
}

// Send chat message
async function sendChatMessage() {
    const message = chatMessageInput.value.trim();
    if (!message) return;
    
    if (!currentPresentation || !currentPresentation.presentation_id) {
        addChatMessage('system', 'No presentation available. Please generate a presentation first.');
        return;
    }
    
    // Clear input
    chatMessageInput.value = '';
    
    // Add user message to chat
    addChatMessage('user', message);
    
    // Show typing indicator
    showChatTyping();
    
    // Disable send button
    if (sendChatMessageBtn) {
        sendChatMessageBtn.disabled = true;
    }
    
    try {
        const requestBody = {
            message: message,
            thread_id: chatThreadId
        };
        
        const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/chat-edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        hideChatTyping();
        
        if (response.ok) {
            // Update thread ID
            chatThreadId = data.thread_id;
            
            // Add response message
            addChatMessage('assistant', data.message);
            
            // Add changes made
            if (data.changes_made && data.changes_made.length > 0) {
                const changesText = "✅ Changes applied:\n" + data.changes_made.map(change => `• ${change}`).join('\n');
                addChatMessage('system', changesText);
                
                // Refresh the presentation view after changes
                setTimeout(() => {
                    reloadPresentationSlides();
                }, 1000);
            }
            
            // Add any errors
            if (data.errors && data.errors.length > 0) {
                const errorsText = "⚠️ Issues encountered:\n" + data.errors.map(error => `• ${error}`).join('\n');
                addChatMessage('system', errorsText);
            }
        } else {
            addChatMessage('system', `❌ Error: ${data.detail || 'Failed to process request'}`);
        }
    } catch (error) {
        hideChatTyping();
        addChatMessage('system', `❌ Error: ${error.message}`);
        console.error('Chat message error:', error);
    } finally {
        // Re-enable send button
        if (sendChatMessageBtn) {
            sendChatMessageBtn.disabled = false;
        }
    }
}

// Add message to chat
function addChatMessage(sender, text) {
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    let avatarIcon = 'fas fa-robot';
    if (sender === 'user') {
        avatarIcon = 'fas fa-user';
    } else if (sender === 'system') {
        avatarIcon = 'fas fa-info-circle';
    }
    
    const messageHtml = `
        <div class="message-avatar">
            <i class="${avatarIcon}"></i>
        </div>
        <div class="message-content">
            <div class="message-text">${text.replace(/\n/g, '<br>')}</div>
        </div>
    `;
    
    messageDiv.innerHTML = messageHtml;
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showChatTyping() {
    if (!chatMessages) return;
    
    const typingDiv = document.createElement('div');
    typingDiv.id = 'chat-typing-indicator';
    typingDiv.className = 'chat-message assistant-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-text">AI is thinking...</div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide typing indicator
function hideChatTyping() {
    const typingIndicator = document.getElementById('chat-typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Reload presentation slides for chat updates
async function reloadPresentationSlides() {
    if (!currentPresentation || !currentPresentation.presentation_id) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/slides`);
        const data = await response.json();
        
        if (response.ok) {
            currentPresentation = data;
            // Refresh the display
            displaySlidesThumbnails();
            showSlide(currentSlideIndex); // Show the current slide again
            console.log('Presentation slides reloaded for chat mode');
        } else {
            console.error('Failed to reload slides:', data.detail);
        }
    } catch (error) {
        console.error('Error reloading slides:', error);
    }
}

// Initialize chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize chat after a short delay to ensure all elements are ready
    setTimeout(initializeChatMode, 100);
});

// Auto-initialize chat mode when presentation is generated
function onPresentationGenerated(presentationData) {
    // Store presentation data
    currentPresentation = presentationData;
    
    // Reset chat session for new presentation
    chatThreadId = null;
    
    // Clear previous chat messages (keep the initial welcome message)
    if (chatMessages) {
        const welcomeMessage = chatMessages.querySelector('.assistant-message');
        chatMessages.innerHTML = '';
        if (welcomeMessage) {
            chatMessages.appendChild(welcomeMessage);
        }
    }
    
    console.log('Presentation generated, chat ready for:', presentationData.presentation_id);
}