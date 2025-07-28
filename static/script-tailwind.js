// Main application script for Tailwind CSS frontend
// Global state
let selectedTemplate = null;
let templates = [];
let placeholders = [];
let currentPresentation = null;
let currentSlideIndex = 0;
let isEditMode = false;
let viewerMode = 'slides';

// API base URL
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
const errorModal = document.getElementById('error-modal');
const errorMessage = document.getElementById('error-message');

// Progress steps
const progressSteps = document.querySelectorAll('.progress-step');

// Buttons
const continueToPromptBtn = document.getElementById('continue-to-prompt');
const backToTemplatesBtn = document.getElementById('back-to-templates');
const generateContentBtn = document.getElementById('generate-content');
const startOverBtn = document.getElementById('start-over');
const errorOkBtn = document.getElementById('error-ok-btn');

// Presentation viewer elements
const viewModeBtn = document.getElementById('view-mode-btn');
const editModeBtn = document.getElementById('edit-mode-btn');
const savePresentationBtn = document.getElementById('save-presentation');
const slidesThumbnails = document.getElementById('slides-thumbnails');
const currentSlideDiv = document.getElementById('current-slide');
const editPanel = document.getElementById('edit-panel');
const editableElements = document.getElementById('editable-elements');
const slideCount = document.getElementById('slide-count');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
    setupEventListeners();
    setupAdvancedOptions();
});

// Setup event listeners
function setupEventListeners() {
    // Navigation
    if (continueToPromptBtn) continueToPromptBtn.addEventListener('click', goToPromptSection);
    if (backToTemplatesBtn) backToTemplatesBtn.addEventListener('click', goToTemplateSection);
    if (generateContentBtn) generateContentBtn.addEventListener('click', generateContent);
    if (startOverBtn) startOverBtn.addEventListener('click', startOver);
    if (errorOkBtn) errorOkBtn.addEventListener('click', closeErrorModal);
    
    // Presentation viewer
    if (viewModeBtn) viewModeBtn.addEventListener('click', () => setViewMode(false));
    if (editModeBtn) editModeBtn.addEventListener('click', () => setViewMode(true));
    if (savePresentationBtn) savePresentationBtn.addEventListener('click', savePresentation);
    
    // Character counter
    if (promptInput) promptInput.addEventListener('input', updateCharCounter);
    
    // Modal close
    if (errorModal) {
        errorModal.addEventListener('click', function(e) {
            if (e.target === errorModal) closeErrorModal();
        });
    }
}

// Setup advanced options toggle
function setupAdvancedOptions() {
    const advancedOptionsToggle = document.getElementById('advanced-options-toggle');
    const advancedOptions = document.getElementById('advanced-options');
    
    if (advancedOptionsToggle && advancedOptions) {
        advancedOptionsToggle.addEventListener('click', function() {
            const isHidden = advancedOptions.classList.contains('hidden');
            advancedOptions.classList.toggle('hidden');
            
            const chevron = advancedOptionsToggle.querySelector('.fa-chevron-down');
            if (chevron) {
                chevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        });
    }
}

// Load templates from API
async function loadTemplates() {
    try {
        templatesLoading.style.display = 'flex';
        templatesGrid.style.display = 'none';
        
        const response = await fetch(`${API_BASE_URL}/templates`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        templates = await response.json();
        displayTemplates(templates);
        
    } catch (error) {
        console.error('Error loading templates:', error);
        showError('Failed to load templates. Please try again.');
    } finally {
        templatesLoading.style.display = 'none';
    }
}

// Display templates in grid
function displayTemplates(templateList) {
    if (!templatesGrid) return;
    
    templatesGrid.innerHTML = templateList.map(template => `
        <div class="template-card group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:border-primary-300 transition-all duration-200" 
             onclick="selectTemplate('${template.id}', '${template.name}', '${template.thumbnailLink || ''}')"
             data-template-id="${template.id}">
            <div class="aspect-w-16 aspect-h-9 rounded-t-xl overflow-hidden bg-gray-100">
                ${template.thumbnailLink ? 
                    `<img src="${template.thumbnailLink}" alt="${template.name}" class="w-full h-32 object-cover group-hover:scale-105 transition-transform duration-200">` :
                    `<div class="w-full h-32 bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
                        <i class="fas fa-presentation text-primary-400 text-3xl"></i>
                    </div>`
                }
            </div>
            <div class="p-4">
                <h3 class="font-semibold text-gray-900 mb-2 group-hover:text-primary-600 transition-colors">${template.name}</h3>
                <p class="text-sm text-gray-600">Professional presentation template</p>
                <div class="mt-3 flex items-center text-xs text-gray-500">
                    <i class="fas fa-star text-yellow-400 mr-1"></i>
                    <span>4.8 (${Math.floor(Math.random() * 50) + 10} reviews)</span>
                </div>
            </div>
        </div>
    `).join('');
    
    templatesGrid.style.display = 'grid';
    
    // Add selection animation
    requestAnimationFrame(() => {
        templatesGrid.classList.add('slide-in-up');
    });
}

// Select a template
async function selectTemplate(templateId, templateName, thumbnailLink) {
    selectedTemplate = { id: templateId, name: templateName, thumbnailLink };
    
    // Add visual feedback
    document.querySelectorAll('.template-card').forEach(card => {
        card.classList.remove('ring-2', 'ring-primary-500', 'bg-primary-50');
    });
    
    const selectedCard = document.querySelector(`[data-template-id="${templateId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('ring-2', 'ring-primary-500', 'bg-primary-50');
    }
    
    try {
        // Load placeholders
        const response = await fetch(`${API_BASE_URL}/templates/${templateId}/placeholders`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        placeholders = await response.json();
        showSelectedTemplate();
        
    } catch (error) {
        console.error('Error loading placeholders:', error);
        showError('Failed to load template details. Please try again.');
    }
}

// Show selected template info
function showSelectedTemplate() {
    if (!selectedTemplateInfo) return;
    
    // Update template info
    const templateThumbnail = document.getElementById('selected-template-thumbnail');
    const templateName = document.getElementById('selected-template-name');
    
    if (templateThumbnail && selectedTemplate.thumbnailLink) {
        templateThumbnail.src = selectedTemplate.thumbnailLink;
    }
    if (templateName) {
        templateName.textContent = selectedTemplate.name;
    }
    
    // Display placeholders
    if (placeholdersList) {
        placeholdersList.innerHTML = placeholders.map(placeholder => `
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                ${placeholder.name}
            </span>
        `).join('');
    }
    
    selectedTemplateInfo.classList.remove('hidden');
    selectedTemplateInfo.classList.add('slide-in-up');
}

// Navigate to prompt section
function goToPromptSection() {
    if (!selectedTemplate) {
        showError('Please select a template first.');
        return;
    }
    
    templateSection.classList.add('hidden');
    promptSection.classList.remove('hidden');
    promptSection.classList.add('slide-in-up');
    
    updateProgressSteps(1);
    
    // Focus on prompt input
    setTimeout(() => {
        if (promptInput) promptInput.focus();
    }, 300);
}

// Navigate back to template section
function goToTemplateSection() {
    promptSection.classList.add('hidden');
    templateSection.classList.remove('hidden');
    templateSection.classList.add('slide-in-up');
    
    updateProgressSteps(0);
}

// Update progress steps
function updateProgressSteps(activeStep) {
    progressSteps.forEach((step, index) => {
        const circle = step.querySelector('div');
        const text = step.querySelector('span');
        
        if (index <= activeStep) {
            step.classList.add('active');
            circle.classList.remove('bg-gray-300', 'text-gray-600');
            circle.classList.add('bg-primary-600', 'text-white');
            text.classList.remove('text-gray-500');
            text.classList.add('text-primary-600');
        } else {
            step.classList.remove('active');
            circle.classList.remove('bg-primary-600', 'text-white');
            circle.classList.add('bg-gray-300', 'text-gray-600');
            text.classList.remove('text-primary-600');
            text.classList.add('text-gray-500');
        }
    });
}

// Update character counter
function updateCharCounter() {
    const length = promptInput.value.length;
    const maxLength = 2000;
    
    if (charCount) {
        charCount.textContent = `${length} / ${maxLength} characters`;
        
        if (length > maxLength * 0.9) {
            charCount.classList.add('text-red-500');
        } else {
            charCount.classList.remove('text-red-500');
        }
    }
}

// Generate content
async function generateContent() {
    const prompt = promptInput?.value?.trim();
    if (!prompt) {
        showError('Please enter a description of your business or project.');
        return;
    }
    
    if (!selectedTemplate) {
        showError('Please select a template first.');
        return;
    }
    
    try {
        // Show generation status
        generationStatus.classList.remove('hidden');
        generateContentBtn.disabled = true;
        generateContentBtn.innerHTML = '<i class="fas fa-spinner animate-spin mr-2"></i>Generating...';
        
        const requestData = {
            template_id: selectedTemplate.id,
            prompt: prompt,
            color_updates: {} // Add color customization if needed
        };
        
        const response = await fetch(`${API_BASE_URL}/generate-content`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const result = await response.json();
        
        if (result.errors && result.errors.length > 0) {
            console.warn('Generation completed with warnings:', result.errors);
        }
        
        // Load presentation data
        await loadPresentationData(result);
        
        // Navigate to editor
        promptSection.classList.add('hidden');
        outputSection.classList.remove('hidden');
        outputSection.classList.add('slide-in-up');
        
        updateProgressSteps(2);
        
    } catch (error) {
        console.error('Error generating content:', error);
        showError(`Failed to generate content: ${error.message}`);
    } finally {
        generationStatus.classList.add('hidden');
        generateContentBtn.disabled = false;
        generateContentBtn.innerHTML = '<i class="fas fa-magic mr-2"></i>Generate Presentation';
    }
}

// Load presentation data
async function loadPresentationData(generationResult) {
    try {
        currentPresentation = {
            presentation_id: generationResult.presentation_id,
            presentation_url: generationResult.presentation_url,
            presentation_view_url: generationResult.presentation_view_url,
            title: selectedTemplate.name,
            slides: []
        };
        
        // For demo presentations, create mock slide data
        if (generationResult.presentation_id && generationResult.presentation_id.startsWith('demo-')) {
            createDemoSlideData(generationResult);
        } else {
            // Load real presentation data
            const response = await fetch(`${API_BASE_URL}/presentations/${generationResult.presentation_id}/slides`);
            if (response.ok) {
                currentPresentation = await response.json();
            } else {
                createDemoSlideData(generationResult);
            }
        }
        
        displayPresentationThumbnails();
        if (currentPresentation.slides.length > 0) {
            showSlide(0);
        }
        
    } catch (error) {
        console.error('Error loading presentation data:', error);
        createDemoSlideData(generationResult);
    }
}

// Create demo slide data with realistic content
function createDemoSlideData(generationResult) {
    const results = generationResult.results || {};
    const slideTemplates = [
        {
            title: 'Company Overview',
            type: 'title',
            elements: [
                {
                    element_id: 'title_1',
                    type: 'text',
                    content: Object.values(results)[0] || 'Revolutionary AI-Powered Business Solution',
                    placeholder_name: 'Company Title',
                    editable: true
                },
                {
                    element_id: 'subtitle_1',
                    type: 'text',
                    content: 'Transforming industries through intelligent automation',
                    placeholder_name: 'Subtitle',
                    editable: true
                },
                {
                    element_id: 'company_1',
                    type: 'text',
                    content: 'Presented by: Tech Innovations Inc.',
                    placeholder_name: 'Company Name',
                    editable: true
                }
            ]
        },
        {
            title: 'Problem Statement',
            type: 'content',
            elements: [
                {
                    element_id: 'title_2',
                    type: 'text',
                    content: 'Problem Statement',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'problem_2',
                    type: 'text',
                    content: results.problem || `• 73% of businesses struggle with manual processes
• $2.8 trillion lost annually due to inefficient workflows  
• Average employee spends 4 hours daily on repetitive tasks
• Current solutions are fragmented and expensive
• Small businesses lack access to enterprise-grade automation`,
                    placeholder_name: 'Problem Description',
                    editable: true
                }
            ]
        },
        {
            title: 'Our Solution',
            type: 'two-column',
            elements: [
                {
                    element_id: 'title_3',
                    type: 'text',
                    content: 'Our Solution',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'solution_3a',
                    type: 'text',
                    content: results.solution || `**AI-Powered Automation Platform**

• Intelligent workflow optimization
• Natural language processing
• Seamless integration capabilities
• Real-time analytics and insights`,
                    placeholder_name: 'Solution Features',
                    editable: true
                },
                {
                    element_id: 'benefits_3b',
                    type: 'text',
                    content: `**Key Benefits**

• 85% reduction in manual work
• $50K+ annual savings per employee
• 99.9% uptime guarantee
• Enterprise-grade security`,
                    placeholder_name: 'Key Benefits',
                    editable: true
                }
            ]
        },
        {
            title: 'Market Opportunity',
            type: 'chart',
            elements: [
                {
                    element_id: 'title_4',
                    type: 'text',
                    content: 'Market Opportunity',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'market_4',
                    type: 'text',
                    content: results.market || `The global business process automation market is experiencing unprecedented growth:

• **$12.6 billion** current market size
• **15.1% CAGR** through 2028
• **$19.6 billion** projected by 2028
• **60%** of companies planning automation investments

Our addressable market represents a **$2.3 billion** opportunity.`,
                    placeholder_name: 'Market Analysis',
                    editable: true
                }
            ]
        },
        {
            title: 'Business Model',
            type: 'content',
            elements: [
                {
                    element_id: 'title_5',
                    type: 'text',
                    content: 'Business Model',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'model_5',
                    type: 'text',
                    content: results.business_model || `**SaaS Subscription Model**

• **Starter Plan**: $99/month - Up to 10 users
• **Professional**: $299/month - Up to 50 users  
• **Enterprise**: $999/month - Unlimited users
• **Custom Solutions**: Tailored pricing

**Revenue Streams:**
• Monthly recurring revenue (85%)
• Professional services (10%)
• Training and certification (5%)`,
                    placeholder_name: 'Business Model',
                    editable: true
                }
            ]
        },
        {
            title: 'Team',
            type: 'image',
            elements: [
                {
                    element_id: 'title_6',
                    type: 'text',
                    content: 'Our Team',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'team_6',
                    type: 'text',
                    content: results.team || `**Leadership Team**

• **Sarah Chen** - CEO & Co-founder  
  Former VP of Engineering at Google, 15 years experience

• **Michael Rodriguez** - CTO & Co-founder  
  Ex-Principal Architect at Microsoft, AI/ML expert

• **Lisa Wang** - Head of Sales  
  Former Enterprise Sales Director at Salesforce

• **David Kumar** - Head of Product  
  Product leader with 3 successful exits`,
                    placeholder_name: 'Team Description',
                    editable: true
                }
            ]
        },
        {
            title: 'Financial Projections',
            type: 'chart',
            elements: [
                {
                    element_id: 'title_7',
                    type: 'text',
                    content: 'Financial Projections',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'financials_7',
                    type: 'text',
                    content: results.financials || `**5-Year Revenue Projection**

• **Year 1**: $250K - Product launch & early customers
• **Year 2**: $1.2M - Market expansion  
• **Year 3**: $4.5M - Scale operations
• **Year 4**: $12M - International expansion
• **Year 5**: $28M - Market leadership

**Key Metrics:**
• Customer Acquisition Cost: $850
• Lifetime Value: $15,000
• Monthly Churn Rate: <2%
• Gross Margin: 85%`,
                    placeholder_name: 'Financial Data',
                    editable: true
                }
            ]
        },
        {
            title: 'Investment Ask',
            type: 'content',
            elements: [
                {
                    element_id: 'title_8',
                    type: 'text',
                    content: 'Investment Opportunity',
                    placeholder_name: 'Title',
                    editable: true
                },
                {
                    element_id: 'investment_8',
                    type: 'text',
                    content: results.investment || `**Seeking $3.5M Series A Funding**

**Use of Funds:**
• Product Development (40%) - $1.4M
• Sales & Marketing (35%) - $1.2M  
• Team Expansion (15%) - $525K
• Operations & Infrastructure (10%) - $350K

**Expected Outcomes:**
• 10x revenue growth in 24 months
• Expand to 3 new markets
• Build strategic partnerships
• Achieve profitability by month 30

**Join us in revolutionizing business automation!**`,
                    placeholder_name: 'Investment Details',
                    editable: true
                }
            ]
        }
    ];
    
    currentPresentation.slides = slideTemplates.map((template, index) => ({
        slide_id: `demo_slide_${index + 1}`,
        slide_index: index + 1,
        title: template.title,
        type: template.type,
        elements: template.elements,
        theme: 'professional'
    }));
}

// Display presentation thumbnails
function displayPresentationThumbnails() {
    if (!slidesThumbnails || !currentPresentation) return;
    
    slidesThumbnails.innerHTML = currentPresentation.slides.map((slide, index) => `
        <div class="slide-thumbnail cursor-pointer p-3 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors ${index === currentSlideIndex ? 'active border-primary-500 bg-primary-50' : ''}"
             onclick="showSlide(${index})" data-slide-index="${index}">
            <div class="slide-thumbnail-preview">
                ${renderSlideThumbnail(slide, index)}
            </div>
            <p class="text-xs text-gray-700 font-medium truncate mt-2">${slide.title}</p>
        </div>
    `).join('');
    
    // Update slide count
    if (slideCount) {
        slideCount.textContent = `${currentPresentation.slides.length} slides`;
    }
}

// Render slide thumbnail with proper preview
function renderSlideThumbnail(slide, index) {
    const slideType = determineSlideType(slide);
    const titleEl = slide.elements?.find(el => el.placeholder_name && el.placeholder_name.toLowerCase().includes('title'));
    const title = (titleEl ? titleEl.content : slide.title) || `Slide ${index + 1}`;
    const shortTitle = title.length > 25 ? title.substring(0, 25) + '...' : title;
    
    switch (slideType) {
        case 'title':
            return `
                <div class="w-full h-full bg-gradient-to-br from-blue-600 to-blue-800 relative rounded overflow-hidden">
                    <div class="absolute inset-0 flex flex-col items-center justify-center p-2 text-white text-center">
                        <div class="text-xs font-bold mb-1">${shortTitle}</div>
                        <div class="w-8 h-0.5 bg-white/60 rounded"></div>
                    </div>
                    <div class="absolute top-1 left-1 w-4 h-1 bg-white/40 rounded text-xs"></div>
                </div>
            `;
            
        case 'chart':
            return `
                <div class="w-full h-full bg-white relative rounded overflow-hidden border">
                    <div class="absolute top-1 left-1 right-1 h-2 bg-blue-600 rounded-sm"></div>
                    <div class="absolute top-4 left-1 w-0.5 h-12 bg-blue-600"></div>
                    <div class="p-1">
                        <div class="text-xs font-semibold text-gray-800 mb-1 truncate">${shortTitle}</div>
                        <div class="flex items-end space-x-0.5 mb-1">
                            <div class="w-1 h-3 bg-blue-400"></div>
                            <div class="w-1 h-4 bg-blue-500"></div>
                            <div class="w-1 h-2 bg-blue-300"></div>
                            <div class="w-1 h-5 bg-blue-600"></div>
                        </div>
                        <div class="grid grid-cols-2 gap-0.5 text-xs">
                            <div class="bg-gray-100 p-0.5 rounded text-center">$2.5M</div>
                            <div class="bg-gray-100 p-0.5 rounded text-center">150%</div>
                        </div>
                    </div>
                </div>
            `;
            
        case 'image':
            return `
                <div class="w-full h-full bg-white relative rounded overflow-hidden border">
                    <div class="absolute top-1 left-1 right-1 h-1 bg-blue-600 rounded-sm"></div>
                    <div class="absolute top-3 left-1 w-0.5 h-12 bg-blue-600"></div>
                    <div class="p-1">
                        <div class="text-xs font-semibold text-gray-800 mb-1 truncate">${shortTitle}</div>
                        <div class="w-full h-6 bg-gradient-to-br from-blue-100 to-blue-200 rounded flex items-center justify-center mb-1">
                            <svg class="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path>
                            </svg>
                        </div>
                        <div class="space-y-0.5">
                            <div class="w-full h-0.5 bg-gray-200 rounded"></div>
                            <div class="w-3/4 h-0.5 bg-gray-200 rounded"></div>
                        </div>
                    </div>
                </div>
            `;
            
        case 'two-column':
            return `
                <div class="w-full h-full bg-white relative rounded overflow-hidden border">
                    <div class="absolute top-1 left-1 right-1 h-1 bg-blue-600 rounded-sm"></div>
                    <div class="absolute top-3 left-1 w-0.5 h-12 bg-blue-600"></div>
                    <div class="p-1">
                        <div class="text-xs font-semibold text-gray-800 mb-1 truncate">${shortTitle}</div>
                        <div class="grid grid-cols-2 gap-1">
                            <div class="space-y-0.5">
                                <div class="w-full h-0.5 bg-gray-300 rounded"></div>
                                <div class="w-3/4 h-0.5 bg-gray-300 rounded"></div>
                                <div class="w-full h-0.5 bg-gray-300 rounded"></div>
                            </div>
                            <div class="space-y-0.5">
                                <div class="w-full h-0.5 bg-gray-300 rounded"></div>
                                <div class="w-2/3 h-0.5 bg-gray-300 rounded"></div>
                                <div class="w-full h-0.5 bg-gray-300 rounded"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
        default: // content slide
            return `
                <div class="w-full h-full bg-white relative rounded overflow-hidden border">
                    <div class="absolute top-1 left-1 right-1 h-1 bg-blue-600 rounded-sm"></div>
                    <div class="absolute top-3 left-1 w-0.5 h-12 bg-blue-600"></div>
                    <div class="p-1">
                        <div class="text-xs font-semibold text-gray-800 mb-1 truncate">${shortTitle}</div>
                        <div class="space-y-0.5">
                            <div class="flex items-center space-x-1">
                                <div class="w-1 h-1 bg-blue-500 rounded-full"></div>
                                <div class="w-8 h-0.5 bg-gray-300 rounded"></div>
                            </div>
                            <div class="flex items-center space-x-1">
                                <div class="w-1 h-1 bg-blue-500 rounded-full"></div>
                                <div class="w-10 h-0.5 bg-gray-300 rounded"></div>
                            </div>
                            <div class="flex items-center space-x-1">
                                <div class="w-1 h-1 bg-blue-500 rounded-full"></div>
                                <div class="w-6 h-0.5 bg-gray-300 rounded"></div>
                            </div>
                            <div class="w-full h-3 bg-gray-100 rounded mt-1"></div>
                        </div>
                    </div>
                </div>
            `;
    }
}

// Show specific slide
function showSlide(index) {
    if (!currentPresentation || index < 0 || index >= currentPresentation.slides.length) return;
    
    currentSlideIndex = index;
    const slide = currentPresentation.slides[index];
    
    // Update thumbnail selection
    document.querySelectorAll('.slide-thumbnail').forEach((thumb, i) => {
        if (i === index) {
            thumb.classList.add('active', 'border-primary-500', 'bg-primary-50');
            thumb.classList.remove('border-gray-200');
        } else {
            thumb.classList.remove('active', 'border-primary-500', 'bg-primary-50');
            thumb.classList.add('border-gray-200');
        }
    });
    
    // Display slide content
    displaySlideContent(slide);
    
    // Update edit panel if in edit mode
    if (isEditMode) {
        displayEditPanel(slide);
    }
    
    // Update slide indicator
    const slideIndicator = document.getElementById('slide-indicator');
    if (slideIndicator) {
        slideIndicator.textContent = `Slide ${index + 1} of ${currentPresentation.slides.length}`;
    }
}

// Display slide content
function displaySlideContent(slide) {
    const slideRenderer = document.getElementById('slide-renderer');
    const slideCanvas = document.getElementById('slide-canvas-wrapper');
    const slidesIframe = document.getElementById('slides-iframe');
    
    if (isEditMode) {
        // Show canvas editor
        slideRenderer.style.display = 'none';
        slidesIframe.style.display = 'none';
        slideCanvas.style.display = 'block';
        
        // Load into canvas if editor is initialized
        if (window.slideEditor && window.slideEditor.canvas) {
            loadSlideIntoCanvas(slide);
        }
    } else if (currentPresentation.presentation_view_url && !currentPresentation.presentation_id.startsWith('demo-')) {
        // Show Google Slides iframe for real presentations
        slideRenderer.style.display = 'none';
        slideCanvas.style.display = 'none';
        slidesIframe.style.display = 'block';
        
        // Load Google Slides with specific slide
        const slideUrl = `${currentPresentation.presentation_view_url}#slide=id.${slide.slide_id}`;
        slidesIframe.src = slideUrl;
    } else {
        // Show custom slide renderer
        slideRenderer.style.display = 'block';
        slideCanvas.style.display = 'none';
        slidesIframe.style.display = 'none';
        
        renderSlideContent(slide);
    }
}

// Render slide content with professional design
function renderSlideContent(slide) {
    if (!currentSlideDiv) return;
    
    const slideType = determineSlideType(slide);
    const slideContent = generateSlideLayout(slide, slideType);
    
    currentSlideDiv.innerHTML = slideContent;
}

// Determine slide type based on content and position
function determineSlideType(slide) {
    const title = slide.title.toLowerCase();
    const slideIndex = currentSlideIndex;
    
    if (slideIndex === 0 || title.includes('title') || title.includes('cover') || title.includes('overview')) {
        return 'title';
    } else if (title.includes('problem') || title.includes('solution') || title.includes('market')) {
        return 'content';
    } else if (title.includes('team') || title.includes('about') || title.includes('company')) {
        return 'image';
    } else if (title.includes('financial') || title.includes('revenue') || title.includes('growth')) {
        return 'chart';
    } else if (slideIndex % 3 === 0) {
        return 'two-column';
    } else {
        return 'content';
    }
}

// Generate professional slide layouts
function generateSlideLayout(slide, slideType) {
    const elements = slide.elements || [];
    const titleEl = elements.find(el => el.placeholder_name && el.placeholder_name.toLowerCase().includes('title'));
    const contentEls = elements.filter(el => el !== titleEl);
    
    switch (slideType) {
        case 'title':
            return generateTitleSlide(slide, titleEl, contentEls);
        case 'content':
            return generateContentSlide(slide, titleEl, contentEls);
        case 'two-column':
            return generateTwoColumnSlide(slide, titleEl, contentEls);
        case 'image':
            return generateImageSlide(slide, titleEl, contentEls);
        case 'chart':
            return generateChartSlide(slide, titleEl, contentEls);
        default:
            return generateContentSlide(slide, titleEl, contentEls);
    }
}

// Title slide layout
function generateTitleSlide(slide, titleEl, contentEls) {
    const title = titleEl ? titleEl.content : slide.title;
    const subtitle = contentEls.find(el => el.placeholder_name && el.placeholder_name.toLowerCase().includes('subtitle'));
    const company = contentEls.find(el => el.placeholder_name && (el.placeholder_name.toLowerCase().includes('company') || el.placeholder_name.toLowerCase().includes('author')));
    
    return `
        <div class="slide-template slide-layout-title w-full h-full relative">
            <div class="logo-placeholder">COMPANY</div>
            <h1 class="slide-title-main">${title}</h1>
            ${subtitle ? `<p class="slide-subtitle">${subtitle.content}</p>` : ''}
            ${company ? `<div class="mt-12 text-white/80 text-lg">${company.content}</div>` : ''}
            <div class="absolute bottom-8 text-white/60 text-sm">
                ${new Date().toLocaleDateString()} • AI Generated Presentation
            </div>
        </div>
    `;
}

// Content slide layout
function generateContentSlide(slide, titleEl, contentEls) {
    const title = titleEl ? titleEl.content : slide.title;
    
    return `
        <div class="slide-template slide-layout-content w-full h-full relative">
            <div class="slide-header-bar"></div>
            <div class="slide-accent-bar"></div>
            
            <h2 class="slide-title-secondary">${title}</h2>
            
            <div class="slide-content-area">
                ${renderContentElements(contentEls)}
            </div>
            
            <div class="slide-footer">
                <div class="logo-placeholder">COMPANY</div>
                <div>Slide ${currentSlideIndex + 1}</div>
            </div>
        </div>
    `;
}

// Two column slide layout
function generateTwoColumnSlide(slide, titleEl, contentEls) {
    const title = titleEl ? titleEl.content : slide.title;
    const leftContent = contentEls.slice(0, Math.ceil(contentEls.length / 2));
    const rightContent = contentEls.slice(Math.ceil(contentEls.length / 2));
    
    return `
        <div class="slide-template slide-layout-content w-full h-full relative">
            <div class="slide-header-bar"></div>
            <div class="slide-accent-bar"></div>
            
            <h2 class="slide-title-secondary">${title}</h2>
            
            <div class="slide-layout-two-column">
                <div class="flex-1">
                    ${renderContentElements(leftContent)}
                </div>
                <div class="flex-1">
                    ${renderContentElements(rightContent)}
                </div>
            </div>
            
            <div class="slide-footer">
                <div class="logo-placeholder">COMPANY</div>
                <div>Slide ${currentSlideIndex + 1}</div>
            </div>
        </div>
    `;
}

// Image slide layout
function generateImageSlide(slide, titleEl, contentEls) {
    const title = titleEl ? titleEl.content : slide.title;
    
    return `
        <div class="slide-template slide-layout-image w-full h-full relative">
            <div class="slide-header-bar"></div>
            <div class="slide-accent-bar"></div>
            
            <h2 class="slide-title-secondary">${title}</h2>
            
            <div class="image-placeholder">
                <i class="fas fa-image text-4xl mb-4"></i><br>
                Team Photo / Company Image
            </div>
            
            <div class="slide-content-area">
                ${renderContentElements(contentEls)}
            </div>
            
            <div class="slide-footer">
                <div class="logo-placeholder">COMPANY</div>
                <div>Slide ${currentSlideIndex + 1}</div>
            </div>
        </div>
    `;
}

// Chart slide layout
function generateChartSlide(slide, titleEl, contentEls) {
    const title = titleEl ? titleEl.content : slide.title;
    
    return `
        <div class="slide-template slide-layout-content w-full h-full relative">
            <div class="slide-header-bar"></div>
            <div class="slide-accent-bar"></div>
            
            <h2 class="slide-title-secondary">${title}</h2>
            
            <div class="chart-placeholder">
                <div class="text-center">
                    <i class="fas fa-chart-line text-4xl mb-4"></i><br>
                    Interactive Chart Visualization<br>
                    <small>Revenue Growth • Market Size • Financial Projections</small>
                </div>
            </div>
            
            ${renderFinancialStats()}
            
            <div class="slide-content-area">
                ${renderContentElements(contentEls)}
            </div>
            
            <div class="slide-footer">
                <div class="logo-placeholder">COMPANY</div>
                <div>Slide ${currentSlideIndex + 1}</div>
            </div>
        </div>
    `;
}

// Render content elements professionally
function renderContentElements(elements) {
    if (!elements || elements.length === 0) {
        return '<div class="content-block">No content available for this slide</div>';
    }
    
    return elements.map(element => {
        const content = element.content || '';
        const name = element.placeholder_name || '';
        
        if (isListContent(content)) {
            return `
                <div class="content-block">
                    ${name ? `<h3 class="text-lg font-semibold text-gray-800 mb-4">${name}</h3>` : ''}
                    <ul class="slide-bullet-list">
                        ${parseListItems(content).map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        } else if (isHighlightContent(name)) {
            return `
                <div class="highlight-box">
                    ${name ? `<h3 class="text-lg font-semibold text-blue-800 mb-3">${name}</h3>` : ''}
                    <div class="slide-body-text text-blue-700">${formatTextContent(content)}</div>
                </div>
            `;
        } else {
            return `
                <div class="content-block">
                    ${name ? `<h3 class="text-lg font-semibold text-gray-800 mb-3">${name}</h3>` : ''}
                    <div class="slide-body-text">${formatTextContent(content)}</div>
                </div>
            `;
        }
    }).join('');
}

// Helper functions for content formatting
function isListContent(content) {
    return content.includes('\n•') || content.includes('\n-') || content.includes('\n*') || 
           content.match(/^\d+\./) || content.split('\n').length > 2;
}

function isHighlightContent(name) {
    const highlightKeywords = ['key', 'important', 'highlight', 'value', 'proposition', 'benefit'];
    return highlightKeywords.some(keyword => name.toLowerCase().includes(keyword));
}

function parseListItems(content) {
    const lines = content.split('\n').filter(line => line.trim());
    return lines.map(line => line.replace(/^[•\-\*\d+\.]\s*/, '').trim()).filter(line => line);
}

function formatTextContent(content) {
    if (!content) return '';
    
    // Format bold text
    let formatted = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Format line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Format numbers/percentages
    formatted = formatted.replace(/(\d+%)/g, '<span class="font-semibold text-blue-600">$1</span>');
    formatted = formatted.replace(/(\$[\d,]+)/g, '<span class="font-semibold text-green-600">$1</span>');
    
    return formatted;
}

// Render financial statistics
function renderFinancialStats() {
    return `
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-number">$2.5M</span>
                <div class="stat-label">Revenue Target</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">150%</span>
                <div class="stat-label">Growth Rate</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">10K+</span>
                <div class="stat-label">Customers</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">25</span>
                <div class="stat-label">Team Size</div>
            </div>
        </div>
    `;
}

// Render slide elements
function renderSlideElements(elements) {
    if (!elements || elements.length === 0) {
        return '<div class="flex items-center justify-center h-full text-white/70">No content available</div>';
    }
    
    return elements.map(element => {
        switch (element.type) {
            case 'text':
                return `<div class="mb-4">
                    <h3 class="text-sm font-semibold text-white/90 mb-2">${element.placeholder_name || 'Content'}</h3>
                    <div class="text-white/80">${formatSlideText(element.content)}</div>
                </div>`;
            case 'image':
                return `<div class="mb-4">
                    <img src="${element.content}" alt="${element.placeholder_name}" class="max-w-full h-auto rounded">
                </div>`;
            case 'list':
                const items = element.content.split('\n').filter(item => item.trim());
                return `<div class="mb-4">
                    <h3 class="text-sm font-semibold text-white/90 mb-2">${element.placeholder_name || 'List'}</h3>
                    <ul class="space-y-2 text-white/80">
                        ${items.map(item => `<li class="flex items-start"><i class="fas fa-check text-white/60 mr-2 mt-1"></i><span>${item.trim()}</span></li>`).join('')}
                    </ul>
                </div>`;
            default:
                return `<div class="mb-4">
                    <h3 class="text-sm font-semibold text-white/90 mb-2">${element.placeholder_name || element.type}</h3>
                    <div class="text-white/80">${formatSlideText(element.content)}</div>
                </div>`;
        }
    }).join('');
}

// Format slide text
function formatSlideText(text) {
    if (!text) return '';
    
    // Convert line breaks to HTML
    let formatted = text.replace(/\n/g, '<br>');
    
    // Format bullet points
    formatted = formatted.replace(/^[•\-\*]\s+/gm, '<i class="fas fa-check text-white/60 mr-2"></i>');
    
    // Format bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    return formatted;
}

// Get slide theme based on content
function getSlideTheme(slide) {
    const slideIndex = currentSlideIndex;
    const themes = ['corporate', 'creative', 'minimal', 'dark'];
    return themes[slideIndex % themes.length];
}

// Render slide decorations
function renderSlideDecorations(theme) {
    switch (theme) {
        case 'corporate':
            return '<div class="absolute bottom-4 right-4"><div class="w-16 h-16 bg-white/10 rounded-full"></div></div>';
        case 'creative':
            return '<div class="absolute top-4 right-4"><div class="w-12 h-12 bg-white/20 rounded-lg rotate-45"></div></div>';
        case 'minimal':
            return '<div class="absolute bottom-0 left-0 w-full h-2 bg-white/20"></div>';
        case 'dark':
            return '<div class="absolute top-0 left-0 w-2 h-full bg-white/30"></div>';
        default:
            return '';
    }
}

// Set view mode
function setViewMode(editMode) {
    isEditMode = editMode;
    
    // Update button states
    if (viewModeBtn && editModeBtn) {
        if (editMode) {
            viewModeBtn.classList.remove('bg-primary-600', 'text-white');
            viewModeBtn.classList.add('border-gray-300', 'text-gray-600', 'hover:bg-gray-50');
            editModeBtn.classList.remove('border-gray-300', 'text-gray-600', 'hover:bg-gray-50');
            editModeBtn.classList.add('bg-primary-600', 'text-white');
        } else {
            editModeBtn.classList.remove('bg-primary-600', 'text-white');
            editModeBtn.classList.add('border-gray-300', 'text-gray-600', 'hover:bg-gray-50');
            viewModeBtn.classList.remove('border-gray-300', 'text-gray-600', 'hover:bg-gray-50');
            viewModeBtn.classList.add('bg-primary-600', 'text-white');
        }
    }
    
    // Show/hide edit elements
    const editingToolbar = document.getElementById('editing-toolbar');
    if (editingToolbar) {
        editingToolbar.classList.toggle('hidden', !editMode);
    }
    
    if (editPanel) {
        editPanel.classList.toggle('hidden', !editMode);
    }
    
    if (savePresentationBtn) {
        savePresentationBtn.classList.toggle('hidden', !editMode);
    }
    
    // Initialize or update canvas editor
    if (editMode && window.slideEditor && window.slideEditor.canvas) {
        loadSlideIntoCanvas(currentPresentation.slides[currentSlideIndex]);
    }
    
    // Refresh current slide display
    if (currentPresentation && currentPresentation.slides[currentSlideIndex]) {
        showSlide(currentSlideIndex);
    }
}

// Display edit panel
function displayEditPanel(slide) {
    if (!editableElements) return;
    
    editableElements.innerHTML = slide.elements
        .filter(element => element.editable)
        .map(element => `
            <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">
                    ${element.placeholder_name || element.element_id} (${element.type})
                </label>
                <textarea id="edit-${element.element_id}" rows="3"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none text-sm"
                          placeholder="Enter content for this element...">${element.content}</textarea>
            </div>
        `).join('');
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
            headers: { 'Content-Type': 'application/json' },
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
            showSlide(currentSlideIndex);
            showSuccess('Changes saved successfully!');
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

// Start over
function startOver() {
    // Reset state
    selectedTemplate = null;
    templates = [];
    placeholders = [];
    currentPresentation = null;
    currentSlideIndex = 0;
    isEditMode = false;
    
    // Reset UI
    if (promptInput) promptInput.value = '';
    if (selectedTemplateInfo) selectedTemplateInfo.classList.add('hidden');
    
    // Show template section
    outputSection.classList.add('hidden');
    promptSection.classList.add('hidden');
    templateSection.classList.remove('hidden');
    templateSection.classList.add('slide-in-up');
    
    updateProgressSteps(0);
    
    // Reload templates
    loadTemplates();
}

// Utility functions
function showError(message) {
    if (errorMessage) errorMessage.textContent = message;
    if (errorModal) errorModal.classList.remove('hidden');
}

function closeErrorModal() {
    if (errorModal) errorModal.classList.add('hidden');
}

function showSuccess(message) {
    // Create success notification
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg shadow-lg z-50 flex items-center space-x-2';
    notification.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Load slide into canvas (will be implemented in slide-editor-tailwind.js)
function loadSlideIntoCanvas(slide) {
    if (window.loadSlideIntoCanvas) {
        window.loadSlideIntoCanvas(slide);
    }
}

// Google Slides Integration
function openInGoogleSlides() {
    if (!currentPresentation) {
        showError('No presentation loaded');
        return;
    }
    
    // If it's a demo presentation, show info
    if (currentPresentation.presentation_id.startsWith('demo-')) {
        showError('This is a demo presentation. Generate a real presentation to edit in Google Slides.');
        return;
    }
    
    // Open Google Slides editor
    if (currentPresentation.presentation_url) {
        window.open(currentPresentation.presentation_url, '_blank');
    } else {
        showError('Google Slides URL not available');
    }
}

// Fullscreen toggle
function toggleFullscreen() {
    const fullscreenOverlay = document.getElementById('fullscreen-overlay') || createFullscreenOverlay();
    const currentSlideClone = document.getElementById('current-slide').cloneNode(true);
    
    if (fullscreenOverlay.style.display === 'flex') {
        // Exit fullscreen
        fullscreenOverlay.style.display = 'none';
        document.exitFullscreen?.() || document.webkitExitFullscreen?.() || document.mozCancelFullScreen?.();
    } else {
        // Enter fullscreen
        currentSlideClone.className = 'fullscreen-slide';
        fullscreenOverlay.innerHTML = `
            <div class="fullscreen-slide">
                ${currentSlideClone.innerHTML}
            </div>
            <button onclick="toggleFullscreen()" class="absolute top-4 right-4 text-white bg-black/50 hover:bg-black/70 px-4 py-2 rounded-lg transition-colors">
                <i class="fas fa-times mr-2"></i>Exit Fullscreen
            </button>
        `;
        fullscreenOverlay.style.display = 'flex';
        
        // Request fullscreen
        if (fullscreenOverlay.requestFullscreen) {
            fullscreenOverlay.requestFullscreen();
        } else if (fullscreenOverlay.webkitRequestFullscreen) {
            fullscreenOverlay.webkitRequestFullscreen();
        } else if (fullscreenOverlay.mozRequestFullScreen) {
            fullscreenOverlay.mozRequestFullScreen();
        }
    }
}

// Create fullscreen overlay
function createFullscreenOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'fullscreen-overlay';
    overlay.className = 'fullscreen-overlay';
    document.body.appendChild(overlay);
    
    // Handle ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && overlay.style.display === 'flex') {
            toggleFullscreen();
        }
    });
    
    return overlay;
}

// Apply slide theme
function applyTheme(theme) {
    if (!currentPresentation || !currentPresentation.slides[currentSlideIndex]) return;
    
    const slide = currentPresentation.slides[currentSlideIndex];
    slide.theme = theme;
    
    // Re-render slide with new theme
    displaySlideContent(slide);
    displayPresentationThumbnails(); // Update thumbnail
    
    // Mark as changed
    showSuccess(`Applied ${theme} theme to slide`);
}

// Change slide background
function changeSlideBackground(color) {
    if (!currentPresentation || !currentPresentation.slides[currentSlideIndex]) return;
    
    const slide = currentPresentation.slides[currentSlideIndex];
    slide.background_color = color;
    
    // Re-render slide
    displaySlideContent(slide);
    
    // Mark as changed
    showSuccess('Background color changed');
}

// Presentation playback controls
function startSlideshow() {
    showSlide(0);
    toggleFullscreen();
    
    // Auto-advance slides (optional)
    let slideshowInterval = setInterval(() => {
        if (currentSlideIndex < currentPresentation.slides.length - 1) {
            showSlide(currentSlideIndex + 1);
        } else {
            clearInterval(slideshowInterval);
            toggleFullscreen();
        }
    }, 10000); // 10 seconds per slide
    
    // Store interval so it can be cleared
    window.currentSlideshowInterval = slideshowInterval;
}

// Export presentation
function exportPresentation() {
    if (!currentPresentation) {
        showError('No presentation to export');
        return;
    }
    
    // Create export modal or direct download
    const exportOptions = [
        { format: 'pdf', label: 'PDF Document', icon: 'fas fa-file-pdf' },
        { format: 'pptx', label: 'PowerPoint', icon: 'fas fa-file-powerpoint' },
        { format: 'png', label: 'PNG Images', icon: 'fas fa-image' }
    ];
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
            <div class="p-6 border-b border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900">Export Presentation</h3>
            </div>
            <div class="p-6">
                <div class="space-y-3">
                    ${exportOptions.map(option => `
                        <button onclick="downloadPresentation('${option.format}')" 
                                class="w-full flex items-center space-x-3 p-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                            <i class="${option.icon} text-primary-600"></i>
                            <span class="font-medium">${option.label}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
            <div class="p-6 border-t border-gray-200 flex justify-end">
                <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Download presentation in specific format
async function downloadPresentation(format) {
    try {
        const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/export?format=${format}`, {
            method: 'GET'
        });
        
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentPresentation.title || 'presentation'}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showSuccess(`Presentation exported as ${format.toUpperCase()}`);
        
    } catch (error) {
        console.error('Export error:', error);
        showError('Failed to export presentation. For demo presentations, use "Open in Google Slides" to download.');
    }
    
    // Close modal
    document.querySelector('.fixed.inset-0.bg-black').remove();
}

// Tab switching
function showEditTab(tabName) {
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-primary-600', 'text-primary-600');
        btn.classList.add('border-transparent', 'text-gray-500');
    });
    
    document.querySelectorAll('.edit-tab').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // Activate selected tab
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.remove('hidden');
    }
    
    // Update button style
    if (event && event.target) {
        const activeButton = event.target;
        activeButton.classList.remove('border-transparent', 'text-gray-500');
        activeButton.classList.add('border-primary-600', 'text-primary-600');
    }
}

// Slide management functions
function duplicateSlide() {
    if (!currentPresentation || currentSlideIndex < 0) {
        showError('No slide selected to duplicate');
        return;
    }
    
    const currentSlide = currentPresentation.slides[currentSlideIndex];
    const newSlide = {
        ...currentSlide,
        slide_id: `slide_${Date.now()}`,
        slide_index: currentPresentation.slides.length + 1,
        title: `${currentSlide.title} (Copy)`,
        elements: currentSlide.elements.map(el => ({
            ...el,
            element_id: `element_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`
        }))
    };
    
    currentPresentation.slides.splice(currentSlideIndex + 1, 0, newSlide);
    
    // Update slide indices
    currentPresentation.slides.forEach((slide, index) => {
        slide.slide_index = index + 1;
    });
    
    displayPresentationThumbnails();
    showSlide(currentSlideIndex + 1);
    showSuccess('Slide duplicated');
}

function deleteSlide() {
    if (!currentPresentation || currentPresentation.slides.length <= 1) {
        showError('Cannot delete the only slide');
        return;
    }
    
    if (currentSlideIndex < 0) {
        showError('No slide selected to delete');
        return;
    }
    
    // Confirm deletion
    if (!confirm('Are you sure you want to delete this slide?')) {
        return;
    }
    
    currentPresentation.slides.splice(currentSlideIndex, 1);
    
    // Update slide indices
    currentPresentation.slides.forEach((slide, index) => {
        slide.slide_index = index + 1;
    });
    
    // Adjust current slide index
    if (currentSlideIndex >= currentPresentation.slides.length) {
        currentSlideIndex = currentPresentation.slides.length - 1;
    }
    
    displayPresentationThumbnails();
    showSlide(currentSlideIndex);
    showSuccess('Slide deleted');
}

function addNewSlide() {
    if (!currentPresentation) {
        showError('No presentation loaded');
        return;
    }
    
    const newSlide = {
        slide_id: `slide_${Date.now()}`,
        slide_index: currentPresentation.slides.length + 1,
        title: `Slide ${currentPresentation.slides.length + 1}`,
        theme: 'corporate',
        elements: [{
            element_id: `element_${Date.now()}`,
            type: 'text',
            content: 'Click to edit title',
            placeholder_name: 'Title',
            position: { x: 50, y: 50 },
            size: { width: 600, height: 80 },
            font_size: 32,
            font_family: 'Inter',
            color: '#ffffff',
            editable: true
        }, {
            element_id: `element_${Date.now() + 1}`,
            type: 'text',
            content: 'Click to edit content',
            placeholder_name: 'Content',
            position: { x: 50, y: 150 },
            size: { width: 600, height: 300 },
            font_size: 18,
            font_family: 'Inter',
            color: '#ffffff',
            editable: true
        }]
    };
    
    currentPresentation.slides.push(newSlide);
    displayPresentationThumbnails();
    showSlide(currentPresentation.slides.length - 1);
    showSuccess('New slide added');
}

// Enhanced theme system with more options
const slideThemes = {
    corporate: {
        name: 'Corporate',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        textColor: '#ffffff',
        accentColor: '#ffd700'
    },
    creative: {
        name: 'Creative',
        background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        textColor: '#ffffff',
        accentColor: '#00f2fe'
    },
    minimal: {
        name: 'Minimal',
        background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        textColor: '#ffffff',
        accentColor: '#667eea'
    },
    dark: {
        name: 'Dark',
        background: 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
        textColor: '#ffffff',
        accentColor: '#e74c3c'
    },
    professional: {
        name: 'Professional',
        background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
        textColor: '#ffffff',
        accentColor: '#ffd700'
    },
    modern: {
        name: 'Modern',
        background: 'linear-gradient(135deg, #667db6 0%, #0082c8 33%, #0082c8 66%, #667db6 100%)',
        textColor: '#ffffff',
        accentColor: '#ff6b6b'
    }
};

// Auto-save functionality
let autoSaveInterval;
function startAutoSave() {
    if (autoSaveInterval) clearInterval(autoSaveInterval);
    
    autoSaveInterval = setInterval(() => {
        if (isEditMode && currentPresentation && !currentPresentation.presentation_id.startsWith('demo-')) {
            savePresentation(true); // Silent save
        }
    }, 30000); // Auto-save every 30 seconds
}

function stopAutoSave() {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
        autoSaveInterval = null;
    }
}

// Enhanced save function with silent option
async function savePresentation(silent = false) {
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
                    element.content = editInput.value;
                }
            }
        });
        
        if (Object.keys(updates).length === 0 && !silent) {
            showError('No changes to save.');
            return;
        }
        
        // Save to backend if not demo
        if (!currentPresentation.presentation_id.startsWith('demo-')) {
            const response = await fetch(`${API_BASE_URL}/presentations/${currentPresentation.presentation_id}/slides/${slide.slide_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    slide_id: slide.slide_id,
                    elements: updates,
                    background_color: slide.background_color,
                    theme: slide.theme
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Failed to save changes');
            }
        }
        
        showSlide(currentSlideIndex);
        if (!silent) {
            showSuccess('Changes saved successfully!');
        }
        
    } catch (error) {
        console.error('Error saving presentation:', error);
        if (!silent) {
            showError(`Failed to save changes: ${error.message}`);
        }
    }
}

// Global functions for window access
window.openInGoogleSlides = openInGoogleSlides;
window.toggleFullscreen = toggleFullscreen;
window.applyTheme = applyTheme;
window.changeSlideBackground = changeSlideBackground;
window.startSlideshow = startSlideshow;
window.exportPresentation = exportPresentation;
window.downloadPresentation = downloadPresentation;
window.duplicateSlide = duplicateSlide;
window.deleteSlide = deleteSlide;
window.addNewSlide = addNewSlide;