# Clinical Protocols RAG API Documentation

## Overview
This API provides AI-powered question answering about clinical protocols using **RAG (Retrieval-Augmented Generation)** with Mistral AI.

## Features
✅ **AI-Powered Answers** - Uses Mistral AI to answer medical questions
✅ **Database-Grounded** - All answers based on actual protocol content
✅ **Multi-Language Support** - Russian, Kazakh, English
✅ **Source Citations** - Every answer includes source references
✅ **Content Filtering** - Filter by protocol or content type
✅ **RESTful API** - Standard REST endpoints with Swagger docs

---

## API Endpoints

### 1. Ask a Question (RAG)
**POST** `/api/v1/protocols/ask/`

Ask AI a question about clinical protocols.

**Request Body:**
```json
{
  "question": "Какие диагностические критерии HELLP-синдрома?",
  "protocol_id": 1,
  "content_types": ["diagnosis", "classification"],
  "language": "ru",
  "include_sources": true
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | ✅ Yes | User's question (3-500 chars) |
| `protocol_id` | integer | ❌ No | Filter by specific protocol ID |
| `content_types` | array | ❌ No | Filter by content types |
| `language` | string | ❌ No | Response language (ru/kk/en), default: ru |
| `include_sources` | boolean | ❌ No | Include source sections, default: true |

**Response:**
```json
{
  "question": "Какие диагностические критерии HELLP-синдрома?",
  "answer": "Диагностические критерии HELLP-синдрома включают: снижение гемоглобина и эритроцитов, наличие шистоцитов; повышение АЛТ, АСТ минимум в 2 раза; ЛДГ >600 МЕ/л; тромбоциты <100 000/мм³...",
  "success": true,
  "error": null,
  "metadata": {
    "model": "open-mistral-nemo",
    "usage": {"prompt_tokens": 450, "completion_tokens": 120},
    "num_sources": 5,
    "language": "ru"
  },
  "sources": [
    {
      "protocol_id": 1,
      "protocol_name": "HELLP-СИНДРОМ",
      "content_type": "diagnosis",
      "content_type_display": "Диагностика",
      "title": "Лабораторные критерии",
      "content": "Снижение гемоглобина и эритроцитов...",
      "page_from": 4,
      "page_to": 5,
      "confidence": 1.0
    }
  ]
}
```

---

### 2. Search Content
**GET** `/api/v1/protocols/search/?q=HELLP&content_type=diagnosis&limit=5`

Search protocol content by text query (no AI).

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ Yes | Search query |
| `content_type` | string | ❌ No | Filter by content type |
| `limit` | integer | ❌ No | Max results (default: 10) |

**Response:**
```json
[
  {
    "protocol_id": 1,
    "protocol_name": "HELLP-СИНДРОМ",
    "content_type": "diagnosis",
    "content_type_display": "Диагностика",
    "title": "Лабораторные критерии",
    "content": "Снижение гемоглобина...",
    "page_from": 4,
    "page_to": 5,
    "confidence": 1.0
  }
]
```

---

### 3. List Protocols
**GET** `/api/v1/protocols/`

Get all clinical protocols.

**Response:**
```json
[
  {
    "id": 1,
    "name": "HELLP-СИНДРОМ",
    "year": 2022,
    "medicine": "Акушерство и гинекология",
    "mkb": "О14.2",
    "mkb_codes": ["O00-O99", "О14.2"],
    "url": "https://...",
    "size": 1234567,
    "extension": "pdf",
    "created_at": "2026-01-14T00:00:00Z",
    "contents": [...]
  }
]
```

---

### 4. Get Protocol Details
**GET** `/api/v1/protocols/{id}/`

Get specific protocol with all content sections.

---

### 5. List Content Sections
**GET** `/api/v1/protocol-content/?protocol=1&content_type=diagnosis`

Get all content sections with filtering.

**Query Parameters:**
- `protocol` - Filter by protocol ID
- `content_type` - Filter by content type
- `source` - Filter by source (pdf/ai/etc)
- `ordering` - Sort by field

---

## Content Types

| Type | Code | Russian Name |
|------|------|--------------|
| Definition | `definition` | Определение |
| Diagnosis | `diagnosis` | Диагностика |
| Classification | `classification` | Классификация |
| Differential | `differential` | Дифференциальный диагноз |
| Treatment | `treatment` | Лечение |
| Drugs | `drugs` | Лекарственные средства |
| Algorithm | `algorithm` | Алгоритм ведения |
| Complications | `complications` | Осложнения |
| Indications | `indications` | Показания |
| Contraindications | `contraindications` | Противопоказания |
| References | `references` | Источники и литература |
| Metadata | `meta` | Организационная информация |
| Other | `other` | Другое |

---

## Usage Examples

### Example 1: Simple Question
```bash
curl -X POST "http://localhost:8000/api/v1/protocols/ask/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Что такое HELLP-синдром?",
    "language": "ru"
  }'
```

### Example 2: Specific Protocol & Content Type
```bash
curl -X POST "http://localhost:8000/api/v1/protocols/ask/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Какие осложнения могут возникнуть?",
    "protocol_id": 1,
    "content_types": ["complications"],
    "include_sources": true
  }'
```

### Example 3: Python Client
```python
import requests

url = "http://localhost:8000/api/v1/protocols/ask/"
headers = {
    "Authorization": "Token YOUR_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "question": "Какие диагностические критерии HELLP-синдрома?",
    "protocol_id": 1,
    "language": "ru"
}

response = requests.post(url, headers=headers, json=data)
result = response.json()

print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])}")
```

### Example 4: JavaScript/React
```javascript
const askQuestion = async (question) => {
  const response = await fetch('/api/v1/protocols/ask/', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: question,
      language: 'ru',
      include_sources: true,
    }),
  });

  const data = await response.json();
  return data;
};

// Usage
const result = await askQuestion('Что такое HELLP-синдром?');
console.log(result.answer);
```

---

## How It Works (RAG Pipeline)

1. **Retrieval** - Search database for relevant content sections
   - Uses text matching on titles and content
   - Filters by protocol ID and content types
   - Returns top 10 most relevant sections

2. **Context Building** - Format retrieved sections for AI
   - Includes protocol name, content type, title, content
   - Adds page numbers for citations

3. **Generation** - Ask Mistral AI to answer
   - Sends question + context to Mistral API
   - Uses low temperature (0.1) for factual answers
   - Instructs AI to cite sources

4. **Response** - Return answer with sources
   - AI-generated answer
   - Source sections used
   - Metadata (model, token usage, etc.)

---

## Testing

Run the test script:
```bash
cd /home/corettaxkutcher/zhancare_group/zhancare_back_experiment
venv/bin/python test_protocol_rag.py
```

This will test:
- ✅ Simple questions
- ✅ Diagnostic criteria questions
- ✅ Treatment questions
- ✅ Complications questions
- ✅ Direct search (without AI)

---

## Authentication

All endpoints require authentication. Use one of:
- **Token Authentication**: `Authorization: Token YOUR_TOKEN`
- **Session Authentication**: Django session cookie

Get your token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token/" \
  -d "username=YOUR_USERNAME&password=YOUR_PASSWORD"
```

---

## Error Handling

### 400 Bad Request
```json
{
  "error": "Invalid input",
  "details": {
    "question": ["This field is required."]
  }
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Service error: API timeout",
  "question": "Your question",
  "answer": null
}
```

---

## Configuration

Set environment variables:
```bash
export MISTRAL_API_KEY="your_mistral_api_key"
```

Or in Django settings:
```python
MISTRAL_API_KEY = "your_mistral_api_key"
```

---

## Performance

- **Retrieval**: ~50ms (database query)
- **AI Generation**: 2-5s (depends on Mistral API)
- **Total Response Time**: 2-6s

Future optimizations:
- [ ] Add vector embeddings for better retrieval
- [ ] Cache common questions
- [ ] Parallel processing for multiple protocols

---

## Future Enhancements

- [ ] Vector embeddings (pgvector) for semantic search
- [ ] Multi-protocol questions ("Compare protocols X and Y")
- [ ] Streaming responses (SSE)
- [ ] Question history and favorites
- [ ] Feedback system (thumbs up/down)
- [ ] Export answers to PDF
- [ ] Voice input/output

---

## Support

For issues or questions:
- Email: support@zhancare.ai
- Docs: https://docs.zhancare.ai
- Swagger UI: http://localhost:8000/swagger/
