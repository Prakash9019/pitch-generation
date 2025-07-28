// Configuration file for the AI Pitchdeck Generator Frontend

const CONFIG = {
    // API Configuration
    api: {
        baseUrl: window.location.origin,
        timeout: 30000, // 30 seconds
        retryAttempts: 3
    },
    
    // UI Configuration
    ui: {
        animationDuration: 300,
        maxPromptLength: 5000,
        minPromptLength: 50,
        templatesPerPage: 12
    },
    
    // Feature Flags
    features: {
        enableColorCustomization: true,
        enableTemplatePreview: true,
        enableProgressSaving: false,
        enableAdvancedPrompts: false
    },
    
    // Text Configuration
    text: {
        appTitle: "AI Pitchdeck Generator",
        appSubtitle: "Transform your ideas into professional presentations",
        promptPlaceholder: "Describe your business, product, or idea. Include details about your target market, value proposition, business model, and any other relevant information...",
        loadingMessages: [
            "Analyzing your business description...",
            "Generating creative content...",
            "Optimizing for your template...",
            "Finalizing your presentation..."
        ]
    },
    
    // Validation Rules
    validation: {
        prompt: {
            minLength: 50,
            maxLength: 5000,
            requiredKeywords: [] // Optional: require certain keywords
        }
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}