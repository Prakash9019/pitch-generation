# AI Pitchdeck Generator Frontend

This is a modern, responsive frontend for the AI Pitchdeck Content Generator built with vanilla HTML, CSS, and JavaScript.

## Features

- **Template Selection**: Browse and select from available Google Slides templates
- **Prompt Input**: Describe your business or idea with a rich text input
- **Content Generation**: AI-powered content generation using Google's Gemini model
- **Real-time Preview**: See placeholders and generated content
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Clean, professional interface with smooth animations

## User Flow

1. **Template Selection**: Users can browse available templates and select one
2. **Prompt Input**: Users describe their business/idea in a text area
3. **Content Generation**: AI generates content for all placeholders in the template
4. **Output**: Users can view and edit the generated presentation

## File Structure

```
static/
├── index.html      # Main HTML file
├── styles.css      # CSS styles and responsive design
├── script.js       # JavaScript functionality
└── README.md       # This file
```

## API Integration

The frontend communicates with the FastAPI backend through these endpoints:

- `GET /templates` - Fetch available templates
- `GET /templates/{id}/placeholders` - Get template placeholders
- `POST /generate-content` - Generate content for the presentation

## Customization

### Styling
- Colors and themes can be modified in `styles.css`
- The design uses CSS Grid and Flexbox for responsive layouts
- Font: Inter (loaded from Google Fonts)

### Functionality
- API endpoints can be configured in `script.js` by changing `API_BASE_URL`
- Additional features can be added by extending the JavaScript functions

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript features used
- CSS Grid and Flexbox support required

## Development

To run the frontend:

1. Start the FastAPI backend server
2. Navigate to `http://localhost:8000` in your browser
3. The frontend will be served automatically

## Error Handling

The frontend includes comprehensive error handling for:
- Network connectivity issues
- API errors
- Invalid user input
- Missing templates or placeholders

All errors are displayed in user-friendly modal dialogs.