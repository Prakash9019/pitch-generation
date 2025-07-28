"""
Demo data for testing the AI Pitchdeck Generator frontend
This file provides sample data when Google Drive templates are not available
"""

DEMO_TEMPLATES = [
    {
        "id": "demo-template-1",
        "name": "Startup Pitch Deck",
        "thumbnailLink": None
    },
    {
        "id": "demo-template-2", 
        "name": "Business Plan Presentation",
        "thumbnailLink": None
    },
    {
        "id": "demo-template-3",
        "name": "Product Launch Deck",
        "thumbnailLink": None
    }
]

DEMO_PLACEHOLDERS = {
    "demo-template-1": [
        {
            "name": "company_name",
            "instruction": "Provide the name of your company or startup",
            "slide_index": 1,
            "element_type": "text",
            "min_words": 1,
            "max_words": 3
        },
        {
            "name": "problem_statement",
            "instruction": "Describe the problem your company solves {{50,100}}",
            "slide_index": 2,
            "element_type": "text",
            "min_words": 50,
            "max_words": 100
        },
        {
            "name": "solution_overview",
            "instruction": "Explain your solution in detail {{75,150}}",
            "slide_index": 3,
            "element_type": "text",
            "min_words": 75,
            "max_words": 150
        },
        {
            "name": "target_market",
            "instruction": "Define your target market and customer segments {{40,80}}",
            "slide_index": 4,
            "element_type": "text",
            "min_words": 40,
            "max_words": 80
        },
        {
            "name": "business_model",
            "instruction": "Describe how your business makes money {{60,120}}",
            "slide_index": 5,
            "element_type": "text",
            "min_words": 60,
            "max_words": 120
        }
    ],
    "demo-template-2": [
        {
            "name": "executive_summary",
            "instruction": "Provide a high-level overview of your business {{100,200}}",
            "slide_index": 1,
            "element_type": "text",
            "min_words": 100,
            "max_words": 200
        },
        {
            "name": "market_analysis",
            "instruction": "Analyze your market size and opportunities {{80,160}}",
            "slide_index": 2,
            "element_type": "text",
            "min_words": 80,
            "max_words": 160
        },
        {
            "name": "competitive_advantage",
            "instruction": "Explain what makes you different from competitors {{60,120}}",
            "slide_index": 3,
            "element_type": "text",
            "min_words": 60,
            "max_words": 120
        }
    ],
    "demo-template-3": [
        {
            "name": "product_name",
            "instruction": "Name of the product being launched",
            "slide_index": 1,
            "element_type": "text",
            "min_words": 1,
            "max_words": 5
        },
        {
            "name": "product_features",
            "instruction": "List key features and benefits {{80,150}}",
            "slide_index": 2,
            "element_type": "text",
            "min_words": 80,
            "max_words": 150
        },
        {
            "name": "launch_strategy",
            "instruction": "Describe your go-to-market strategy {{100,200}}",
            "slide_index": 3,
            "element_type": "text",
            "min_words": 100,
            "max_words": 200
        }
    ]
}

def get_demo_templates():
    """Return demo templates for testing"""
    return DEMO_TEMPLATES

def get_demo_placeholders(template_id):
    """Return demo placeholders for a given template ID"""
    return DEMO_PLACEHOLDERS.get(template_id, [])