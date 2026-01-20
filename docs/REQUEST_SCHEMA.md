# Resume Processor API - Request Schema Reference

**Version:** 3.0.0 - Dynamic Experience Configuration
**Last Updated:** January 2025

This document serves as the definitive reference for the `/process` endpoint request schema.

---

## Endpoint

```
POST /process
```

**Headers:**
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

---

## Request Body Schema

```json
{
  "job_text": "<string>",
  "user_json": { ... },
  "config_json": { ... }
}
```

---

## Field Definitions

### 1. `job_text` (required)

The raw job description text to analyze.

- **Type:** `string`
- **Minimum length:** 50 characters
- **Language:** English or French (auto-detected)

```json
"job_text": "Senior Data Scientist\n\nWe are looking for..."
```

---

### 2. `user_json` (required)

User profile data containing personal info, projects, skills, and experience configuration.

#### 2.1 `personal` (required)

```json
"personal": {
  "name": "John Doe",
  "gender": "male",
  "degree": "Master's in Data Science",
  "title": "Data Scientist"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Full name |
| `gender` | string | Yes | "male" or "female" (for language localization) |
| `degree` | string | No | Highest degree |
| `title` | string | Yes | Professional title |

#### 2.2 `contact` (required)

```json
"contact": {
  "email": "john@example.com",
  "phone": "+33 6 12 34 56 78",
  "location": "Paris, France",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "website": ""
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Email address |
| `phone` | string | Yes | Phone number |
| `location` | string | No | City, Country |
| `linkedin` | string | No | LinkedIn URL |
| `github` | string | No | GitHub URL |
| `website` | string | No | Personal website |

#### 2.3 `projects_database` (required)

Dictionary of all available projects. Keys are project names, values are project details.

```json
"projects_database": {
  "Project Name A": {
    "company": "Company Name",
    "start_date": "2024-01",
    "end_date": "2024-12",
    "location": {
      "en": "Paris, France",
      "fr": "Paris, France"
    },
    "contexte": "Brief context description",
    "technologies": ["Python", "PyTorch", "Docker"],
    "realisations": [
      "Achievement bullet point 1",
      "Achievement bullet point 2",
      "Achievement bullet point 3",
      "Achievement bullet point 4"
    ],
    "metiers": ["AI Engineer", "Data Scientist", "ML Engineer"],
    "priority": 0.8
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company` | string | Yes | Company name |
| `start_date` | string | Yes | Start date (YYYY-MM) |
| `end_date` | string | Yes | End date (YYYY-MM) |
| `location` | object | Yes | `{"en": "...", "fr": "..."}` |
| `contexte` | string | Yes | Brief project context |
| `technologies` | array | Yes | List of technologies used |
| `realisations` | array | Yes | Achievement bullet points |
| `metiers` | array | Yes | Available role titles for this project |
| `priority` | number | No | Priority weight (0.0-1.0) |

**Important:** The `metiers` field is required for role selection. It defines which role titles can be assigned to this project.

#### 2.4 `experiences_config` (required)

Configuration for each experience slot in the resume. Defines which projects can be used and what processing strategy to apply.

```json
"experiences_config": [
  {
    "candidate_projects": [0, 1],
    "role_strategy": "enhanced",
    "content_strategy": "enhanced"
  },
  {
    "candidate_projects": [2],
    "role_strategy": "enhanced",
    "content_strategy": "direct"
  },
  {
    "candidate_projects": [3, 4],
    "role_strategy": "direct",
    "content_strategy": "direct"
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `candidate_projects` | array[int] | Yes | 0-based indexes into projects_database (order of keys) |
| `role_strategy` | string | Yes | `"direct"` or `"enhanced"` |
| `content_strategy` | string | Yes | `"direct"` or `"enhanced"` |

**Strategy Definitions:**

| Strategy | Role Behavior | Content Behavior |
|----------|---------------|------------------|
| `direct` | Use role exactly as defined in project's `metiers` | Use `realisations` bullets directly (no AI) |
| `enhanced` | AI generates optimized role title for ATS | AI generates enhanced bullets tailored to job |

**Index Resolution:**
- Projects are indexed by their order in `projects_database`
- Example: If `projects_database` has keys `["Project A", "Project B", "Project C"]`, then:
  - Index `0` = "Project A"
  - Index `1` = "Project B"
  - Index `2` = "Project C"

**Constraints:**
- Each project can only be used in ONE experience (no reuse)
- The coordinator selects the best project from the candidate pool
- Number of experiences is dynamic (not fixed to 3)

#### 2.5 `skills_database` (required)

User's available skills and essential skills.

```json
"skills_database": {
  "skills": {
    "Python": {"category": "language", "order": 1},
    "PyTorch": {"category": "ml_framework", "order": 2},
    "Docker": {"category": "cloud", "order": 8},
    "SQL": {"category": "language", "order": 1}
  },
  "essential_skills": ["Python", "PyTorch", "Docker", "SQL"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skills` | object | Yes | Map of skill name to metadata |
| `essential_skills` | array | Yes | Skills to always include |

**Skill Categories:**
- `language` - Programming languages
- `ml_framework` - ML/AI frameworks
- `ai_tool` - AI-specific tools
- `web_framework` - Web frameworks
- `data_tool` - Data processing tools
- `database` - Database technologies
- `big_data` - Big data tools
- `cloud` - Cloud platforms
- `devops` - DevOps tools
- `bi_tool` - Business intelligence

#### 2.6 `education` (required)

Education history.

```json
"education": [
  {
    "degree": {
      "en": "Master's in Data Science",
      "fr": "Master en Science des Données"
    },
    "institution": "University Name",
    "location": {
      "en": "Paris, France",
      "fr": "Paris, France"
    },
    "start": "2020-09",
    "end": "2022-06",
    "description": ""
  }
]
```

#### 2.7 `languages` (required)

Language proficiencies.

```json
"languages": [
  {
    "language": {"en": "French", "fr": "Français"},
    "proficiency": {"en": "Native", "fr": "Langue maternelle"}
  },
  {
    "language": {"en": "English", "fr": "Anglais"},
    "proficiency": {"en": "Fluent", "fr": "Courant"}
  }
]
```

#### 2.8 `certifications` (optional)

Professional certifications.

```json
"certifications": [
  {
    "name": "AWS Solutions Architect",
    "issuer": "Amazon",
    "date": "2023-06"
  }
]
```

---

### 3. `config_json` (required)

Processing configuration for models and parameters.

```json
"config_json": {
  "openai": {
    "default_model": "gpt-4o-mini"
  },
  "structuring": {
    "model": "gpt-4o-mini",
    "temperature": 0
  },
  "enhancing": {
    "coordinator": {
      "model": "gpt-4o-mini",
      "temperature": 0.7
    },
    "bullet_coordinator": {
      "model": "gpt-4o-mini",
      "temperature": 0.6
    },
    "bullet_adaptation": {
      "bullets_per_experience": 4,
      "max_bullet_length": 150
    },
    "skills_generation": {
      "target_technical_skills": 20,
      "num_soft_skills": 5
    },
    "profile_generation": {
      "model": "gpt-4o-mini"
    },
    "cover_letter": {
      "model": "gpt-4o-mini"
    }
  }
}
```

---

## Complete Request Example

```json
{
  "job_text": "Data Scientist / AI Engineer\n\nNous recherchons un Data Scientist...",
  "user_json": {
    "personal": {
      "name": "Mohamed BACHAR",
      "gender": "male",
      "degree": "Ingénieur en IA et Data Science",
      "title": "Data Scientist & AI Engineer"
    },
    "contact": {
      "email": "m.bachar.fr@gmail.com",
      "phone": "+33 7 45 50 19 06",
      "location": "Paris, France",
      "linkedin": "https://www.linkedin.com/in/mohamed-bachar/"
    },
    "projects_database": {
      "AI Engine Project": {
        "company": "TNP Consultants",
        "start_date": "2025-02",
        "end_date": "2025-08",
        "location": {"en": "Paris, France", "fr": "Paris, France"},
        "contexte": "Deep Learning on Graphs",
        "technologies": ["Python", "PyTorch", "GCN", "Docker"],
        "realisations": [
          "Designed GCN models for recommendation",
          "Implemented anomaly detection algorithms",
          "Developed RAG pipeline for compliance",
          "Integrated models into microservices"
        ],
        "metiers": ["AI Engineer", "Data Scientist", "ML Engineer"],
        "priority": 0.85
      },
      "Data Governance Project": {
        "company": "TNP Consultants",
        "start_date": "2025-02",
        "end_date": "2025-08",
        "location": {"en": "Paris, France", "fr": "Paris, France"},
        "contexte": "Data catalog implementation",
        "technologies": ["Docker", "Airflow", "Python", "SQL"],
        "realisations": [
          "Mapped data flows across systems",
          "Deployed data governance platform",
          "Built metadata ingestion connectors",
          "Trained business teams on tools"
        ],
        "metiers": ["Data Architect", "Data Engineer", "Data Consultant"],
        "priority": 0.7
      },
      "RAG Platform Project": {
        "company": "AI Movement",
        "start_date": "2024-03",
        "end_date": "2024-09",
        "location": {"en": "Rabat, Morocco", "fr": "Rabat, Maroc"},
        "contexte": "Entrepreneurial AI project",
        "technologies": ["Python", "Flask", "LangChain", "RAG"],
        "realisations": [
          "Architected hybrid RAG system",
          "Built reactive user interfaces",
          "Orchestrated LLM models",
          "Implemented validation protocols"
        ],
        "metiers": ["AI Engineer", "ML Engineer", "Software Engineer"],
        "priority": 0.4
      }
    },
    "skills_database": {
      "skills": {
        "Python": {"category": "language", "order": 1},
        "PyTorch": {"category": "ml_framework", "order": 2},
        "LangChain": {"category": "ai_tool", "order": 3},
        "Docker": {"category": "cloud", "order": 8},
        "SQL": {"category": "language", "order": 1}
      },
      "essential_skills": ["Python", "PyTorch", "Docker", "SQL"]
    },
    "experiences_config": [
      {
        "candidate_projects": [0],
        "role_strategy": "enhanced",
        "content_strategy": "enhanced"
      },
      {
        "candidate_projects": [1],
        "role_strategy": "enhanced",
        "content_strategy": "direct"
      },
      {
        "candidate_projects": [2],
        "role_strategy": "direct",
        "content_strategy": "direct"
      }
    ],
    "education": [
      {
        "degree": {"en": "Engineering Degree in AI & Data Science", "fr": "Diplôme d'Ingénieur en IA"},
        "institution": "Arts et Métiers",
        "location": {"en": "Meknès, Morocco", "fr": "Meknès, Maroc"},
        "start": "2022-09",
        "end": "2025-09",
        "description": ""
      }
    ],
    "languages": [
      {"language": {"en": "French", "fr": "Français"}, "proficiency": {"en": "Bilingual", "fr": "Bilingue"}},
      {"language": {"en": "English", "fr": "Anglais"}, "proficiency": {"en": "Bilingual", "fr": "Bilingue"}}
    ],
    "certifications": []
  },
  "config_json": {
    "openai": {"default_model": "gpt-4o-mini"},
    "structuring": {"model": "gpt-4o-mini", "temperature": 0},
    "enhancing": {
      "coordinator": {"model": "gpt-4o-mini", "temperature": 0.7},
      "bullet_coordinator": {"model": "gpt-4o-mini", "temperature": 0.6},
      "bullet_adaptation": {"bullets_per_experience": 4, "max_bullet_length": 150},
      "skills_generation": {"target_technical_skills": 20, "num_soft_skills": 5},
      "profile_generation": {"model": "gpt-4o-mini"},
      "cover_letter": {"model": "gpt-4o-mini"}
    }
  }
}
```

---

## Response Schema

```json
{
  "success": true,
  "structured_job": {
    "job_title": "Data Scientist",
    "company_name": "Tech Corp",
    "technical_skills": ["Python", "PyTorch"],
    "soft_skills": ["Communication"],
    "metadata": {"language": "en"}
  },
  "resume": {
    "personal": {"name": "...", "title": "..."},
    "contact": {"email": "...", "phone": "..."},
    "profile": "Professional summary text...",
    "experience": [
      {
        "role": "AI Engineer",
        "company": "Company Name",
        "location": "Paris, France",
        "start_date": "2024-01",
        "end_date": "2024-12",
        "bullets": ["Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4"],
        "context": "Project context",
        "is_direct": false
      }
    ],
    "skills": {
      "technical": ["Python", "PyTorch", "Docker"],
      "soft": ["Leadership", "Communication"]
    },
    "education": [...],
    "certifications": [...],
    "languages": [...]
  },
  "cover_letter": "Cover letter text...",
  "metadata": {
    "processing_time_seconds": 12.5,
    "language": "en",
    "experiences": {
      "total": 3,
      "enhanced": 1,
      "direct": 2,
      "projects_used": ["AI Engine Project", "Data Governance Project", "RAG Platform Project"]
    },
    "average_ats_score": 85.3
  }
}
```

---

## Error Responses

| Status | Error | Description |
|--------|-------|-------------|
| 400 | `job_text must be at least 50 characters` | Job text too short |
| 400 | `user_json is required` | Missing user data |
| 400 | `config_json is required` | Missing config |
| 401 | `Missing Authorization header` | No auth header |
| 401 | `Invalid API key` | Wrong API key |
| 500 | `OPENAI_API_KEY not configured` | Server config issue |
| 500 | `experiences_config is required in user_json` | Missing experiences config |
| 500 | `candidate_projects must be integers` | Invalid project indexes |
| 500 | `Project index X out of range` | Index exceeds project count |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | Jan 2025 | Dynamic experience configuration with indexes |
| 2.0.0 | Dec 2024 | JSON-only API (no PDF generation) |
| 1.0.0 | Nov 2024 | Initial release |
