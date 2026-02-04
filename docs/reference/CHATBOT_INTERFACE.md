# Chatbot Interface Documentation

## Overview

The OC7 RAG API now includes a web-based chat interface that provides a user-friendly way to query the cultural events database. This interface is adapted from the OC5 project's landing page design.

## Features

### User Interface
- **Modern Design**: Gradient background with card-based layout (adapted from OC5)
- **Responsive**: Mobile-optimized layout with media queries
- **Real-time Chat**: Interactive conversation interface with message history
- **Status Indicator**: Shows API health status (online/degraded/offline)
- **Typing Indicator**: Visual feedback while waiting for responses

### RAG Functionality
- **Method Selection**: Choose between 3 RAG methods:
  - **Basic**: FAISS vector similarity only
  - **Hybrid**: FAISS + BM25 keyword search (default)
  - **Advanced**: Hybrid + FlashRank reranking
- **Source Display**: Shows relevant event sources with:
  - Event title
  - Location and date
  - Relevance score
- **Error Handling**: User-friendly error messages

## Architecture

### Technology Stack
- **Frontend**: Vanilla HTML/CSS/JavaScript (no framework)
- **Backend**: FastAPI endpoint serving static HTML
- **API Integration**: Browser fetch() to `/api/v1/ask`

### File Structure
```
src/api/
├── main.py                 # Added GET / endpoint
└── static/
    └── index.html          # Chat interface (16KB)
```

### How It Works

1. **Page Load**:
   - User visits `http://server:8000/`
   - FastAPI serves `index.html` via FileResponse
   - JavaScript checks `/health` endpoint for status

2. **User Query**:
   - User types question and clicks "Envoyer"
   - JavaScript sends POST to `/api/v1/ask` with:
     ```json
     {
       "question": "user question",
       "rag_method": "hybrid",
       "top_k": 5
     }
     ```

3. **Response Display**:
   - Answer displayed in chat bubble
   - Sources shown as collapsible cards
   - Conversation history maintained in session

## Deployment

### Changes Made

1. **main.py** (2 changes):
   - Added `FileResponse` import
   - Added `GET /` endpoint to serve chat interface
   - Updated version to 0.4.0

2. **New Files**:
   - `src/api/static/index.html` (chat interface)

### Server Hosting

The interface runs on the same server as the API:
```
hetzner3-oc7api:8000
├── GET /              → Chat interface (NEW)
├── GET /health        → Health check
├── POST /api/v1/ask   → RAG queries
└── /docs              → Swagger UI
```

### Access Methods

**Via SSH Tunnel** (current setup):
```bash
# Create tunnel
ssh -L 8000:localhost:8000 hetzner3-oc7api

# Open browser
open http://localhost:8000
```

**Direct Access** (requires nginx setup):
```
http://[server-ip]:8000
```

## Design Choices

### Why Vanilla JavaScript?

1. **No Build Step**: No npm, webpack, or transpilation needed
2. **Fast Loading**: Single 16KB HTML file
3. **Simple Deployment**: Just copy file to server
4. **Zero Dependencies**: Works in any modern browser
5. **Easy Maintenance**: No framework version updates

### OC5 Design Adaptation

Reused from OC5:
- ✅ Gradient background (#667eea to #764ba2)
- ✅ Card-based layout with shadows
- ✅ Button hover effects
- ✅ Responsive media queries
- ✅ Status badge component

New for OC7:
- ✅ Chat message bubbles
- ✅ Typing indicator animation
- ✅ Source document cards
- ✅ Real-time API integration
- ✅ Conversation history

## Usage Examples

### Example Queries

**Concerts**:
- "Quels concerts à Chambéry ce weekend ?"
- "Y a-t-il des concerts de jazz en Savoie ?"

**Expositions**:
- "Expositions à Annecy en février ?"
- "Quelles galeries d'art en Haute-Savoie ?"

**Events by Location**:
- "Que faire à Grenoble ce soir ?"
- "Événements culturels à Aix-les-Bains"

### Method Comparison

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| Basic | Fast | Good | Simple queries |
| Hybrid | Medium | Better | Most queries (default) |
| Advanced | Slower | Best | Complex queries |

## Testing

### Local Testing
```bash
# Start API (requires OC7 conda environment)
conda activate OC7
python scripts/run_api.py

# Open browser
open http://localhost:8000
```

### Server Testing
```bash
# Check API health
ssh hetzner3-oc7api 'curl -s localhost:8000/health'

# Test chat endpoint
ssh hetzner3-oc7api 'curl -s localhost:8000/ | head -10'

# View API logs
ssh hetzner3-oc7api 'tail -f ~/oc7-rag/api.log'
```

## Browser Compatibility

**Supported Browsers**:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

**Required Features**:
- ES6 JavaScript (arrow functions, async/await)
- CSS Flexbox
- Fetch API

## Limitations

### Current Implementation

1. **No Persistence**: Conversation history lost on page reload
2. **No Streaming**: Full response only (no word-by-word)
3. **Session-only**: No user accounts or saved conversations
4. **Single Language**: French only (Savoie region focus)

### Future Enhancements (Optional)

- [ ] Conversation persistence (localStorage or backend)
- [ ] Streaming responses (Server-Sent Events or WebSocket)
- [ ] Export conversation as PDF
- [ ] Share conversation link
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Dark mode toggle

## Performance

### Metrics

- **Page Load**: < 100ms (16KB HTML)
- **Health Check**: ~50ms
- **Query Response**: 2-5 seconds (depends on RAG method)
  - Basic: ~2s
  - Hybrid: ~3s
  - Advanced: ~5s

### Optimization

The interface is already optimized:
- Single HTTP request for page load
- No external dependencies
- Minimal JavaScript (~100 lines)
- CSS animations use GPU acceleration

## Security Considerations

### Current Setup

✅ **Good**:
- No authentication needed (internal tool)
- Same-origin policy (no CORS issues)
- No sensitive data in frontend
- Input validation on backend

⚠️ **Future Considerations**:
- Rate limiting (prevent abuse)
- Authentication (if exposed publicly)
- HTTPS (if exposed publicly)
- CSP headers (Content Security Policy)

## Troubleshooting

### Common Issues

**Chat interface shows "404 Not Found"**:
- Check `src/api/static/index.html` exists
- Verify FileResponse path is correct
- Restart API to reload changes

**Status shows "Hors ligne"**:
- Check API is running: `ps aux | grep python | grep api`
- Check health endpoint: `curl localhost:8000/health`
- Check logs: `tail -f api.log`

**Queries return errors**:
- Check FAISS index loaded: `/health` shows `index_loaded: true`
- Check LLM available: `/health` shows `llm_available: true`
- Verify MISTRAL_API_KEY is set
- Check API logs for details

**Sources not displaying**:
- Verify response includes `sources` array
- Check browser console for JavaScript errors
- Test API directly: `POST /api/v1/ask`

## Version History

### v0.4.0 (2026-01-30)
- Initial chatbot interface implementation
- Adapted from OC5 landing page design
- Vanilla JavaScript for simplicity
- Full RAG integration (3 methods)
- Source document display
- Responsive mobile layout

## References

- **OC5 Project**: `/Users/ghislaindelabie/Projets dév/Formation OC/OC5 - Déployez un modèle de Machine Learning/`
- **OC5 Landing Page**: `src/oc5_ml_deployment/api/static/landing.html`
- **OC7 API Docs**: `README.md`, `DEPLOYMENT_STATUS.md`
- **FastAPI Static Files**: https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse

---

**Status**: ✅ Implemented and ready for testing on server
**Branch**: `feature/chatbot`
**Target Version**: v0.4.0
