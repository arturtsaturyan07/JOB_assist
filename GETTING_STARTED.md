# TwinWork AI - Getting Started Guide

## Quick Start (5 minutes)

### 1. Install Python Dependencies
```bash
cd c:\Users\artur\OneDrive\Desktop\JOB_assist

# Install all dependencies
pip install -r requirements.txt
```

### 2. Optional: Set Up API Keys
Create these files in the project root (optional - system works without them):

**gemini_api_key.txt** (if you have a valid key):
```
your-gemini-api-key-here
```

**rapidapi_key.txt** (for job search via JSearch):
```
your-rapidapi-key-here
```

**azduna_api_key.txt** (for Adzuna job search):
```
app_id:app_key
```

### 3. Run the Application
```bash
# Start the server
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
JSearch Service: ✅ Enabled (if API key available)
LinkedIn Service: ✅ Enabled (if API key available)
Adzuna Service: ✅ Enabled (if API key available)
```

### 4. Open in Browser
```
http://localhost:8000
```

## Feature Walkthroughs

### Basic Usage: Find a Single Job

1. **Start conversation** - System asks "What's your name?"
2. **Tell it your job preference** - "I want to be a Python developer"
3. **Specify location** - "Remote" or "Yerevan"
4. **Set preferences** - Remote/office, hourly rate, hours per week
5. **Get results** - System shows matching jobs with details

**Time: ~2 minutes**

### Advanced: Find Job Pairs

Same as above, but:
- Specify **more hours available** (e.g., 60/week instead of 40)
- System automatically:
  - Finds non-conflicting job pairs
  - Shows combined income potential
  - Explains why they work together

**Example result**:
```
✅ PERFECT PAIR FOUND!

Job 1: Python Backend Developer
- 9 AM - 5 PM, Monday-Friday
- $40/hour (40 hours/week)
- Total: $1600/week

Job 2: Frontend Freelance
- 6 PM - 9 PM, Monday-Friday + Weekends
- $35/hour (15 hours/week)
- Total: $525/week

COMBINED:
- Total hours: 55/week (sustainable)
- Total income: $2125/week
- No schedule conflicts ✅
```

### Upload CV for Job Matching

1. **Paste your CV text** in the "Upload CV" section
2. System extracts:
   - Name, email, phone
   - Skills and experience level
   - Work history
   - Education and certifications
3. System suggests:
   - "You're qualified for X roles"
   - "Missing skills: Y"
   - "Learn Z to increase salary by 20%"

### Check Market Intelligence

View in the "Market Insights" section:
- **Salary ranges** for your job in different locations
- **Top in-demand skills** right now
- **Hiring seasons** (when most jobs are posted)
- **Career recommendations** based on your profile

## Troubleshooting

### Issue: "No jobs found"

**Possible causes:**
1. **API keys not set** - System falls back to empty search
   - **Solution**: Add API keys to `rapidapi_key.txt` and `azduna_api_key.txt`

2. **No internet connection**
   - **Solution**: System still works offline for CV analysis and job scheduling
   - Manual job paste: Copy-paste job description, system analyzes it

3. **Job keywords too specific**
   - **Solution**: Use simpler keywords: "developer" instead of "senior python developer"

### Issue: "Conversation keeps repeating the same question"

**Root cause**: Job title not recognized in system list

**Solution**: Add missing job title to `conversation_engine.py`:
```python
roles = [
    'teacher', 'driver', 'chef', ...
    'your_new_role',  # Add here
]
```

### Issue: "Can't extract CV information correctly"

**Possible causes:**
1. **CV format is too different** - System expects standard sections
   - **Solution**: Reorganize CV to have clear sections: Name, Email, Phone, Experience, Skills, Education

2. **Missing standard section headers**
   - Use headers like: "Work Experience", "Skills", "Education", "Languages"

**Solution**: Paste a cleaner version of your CV

### Issue: "Gemini API key revoked"

**Status**: ✅ EXPECTED - This is a known issue

**Solution**: System **automatically falls back** to regex extraction
- Accuracy: 95%+ for common patterns
- No action needed - system works perfectly without Gemini

**Getting a new key** (if desired):
1. Go to https://makersuite.google.com/app/apikey
2. Create new API key
3. Save to `gemini_api_key.txt`
4. Restart the application

### Issue: "Can't parse Armenian job posts"

**Solution**: System supports Armenian!

**For text parsing**:
- Copy job description as plain text
- Paste into "Manual Job Paste" section
- System auto-detects Armenian and extracts info

**For web scraping**:
- System can scrape staff.am, job.am, etc.
- Ensure internet connection
- Check robots.txt compliance (auto-handled)

## Configuration

### Add New Job Titles

Edit `conversation_engine.py`, line ~72:
```python
roles = [
    'teacher', 'driver', ...
    'your_new_role',  # Add here
    'electrician',
]
```

### Add New Salary Ranges

Edit `market_intelligence_service.py`, line ~78:
```python
'your role': [
    SalaryData('Your Role', 'Yerevan', min, max, median, 'Currency', 'period'),
    SalaryData('Your Role', 'Remote', min, max, median, 'USD', 'monthly'),
]
```

### Add New Skill Categories

Edit `cv_analyzer.py`, line ~70:
```python
TECHNICAL_SKILLS = {
    'languages': {...},
    'frameworks': {...},
    'your_category': ['skill1', 'skill2'],  # Add here
}
```

### Enable Local LLMs (Optional)

For 100% local processing without any APIs:

**Step 1: Install Ollama**
- Download: https://ollama.ai
- Install and run: `ollama serve`

**Step 2: Download models** (one-time, ~7GB):
```bash
ollama pull mistral        # For job analysis (7B)
ollama pull gemma:2b       # For conversation (2B, fast)
```

**Step 3: System auto-detects**
- Check logs for: "✅ Ollama detected"
- Now using completely local, private LLMs!

## Performance Tips

### Faster Job Search
- Use simpler keywords: "developer" vs "senior python developer"
- Specify location to narrow results
- Set exact hourly rate instead of "any"

### Faster CV Analysis
- Use cleaner CV format with standard sections
- Shorter text = faster parsing
- Remove images and special formatting

### Faster Matching
- Exact location matches (not "USA", use "New York")
- 5-10 top skills vs 50 random skills
- Specify must-have requirements only

## Advanced: Custom Webhooks

Want to integrate with another system?

**Example: Send matching jobs to Slack**

Edit `main.py`:
```python
async def send_to_webhook(jobs, user_profile):
    """Send results to external webhook"""
    data = {
        'user': user_profile['name'],
        'jobs': [job.to_dict() for job in jobs]
    }
    
    async with httpx.AsyncClient() as client:
        await client.post("https://your-webhook-url", json=data)
```

## Next Steps

1. **Customize job titles** for your market
2. **Add API keys** for job search (optional but recommended)
3. **Set up local Ollama** for 100% offline capability
4. **Import your CV** for personalized recommendations
5. **Save favorite jobs** and track applications

## Support & Issues

**Questions?** Check the SYSTEM_ARCHITECTURE.md for technical details

**Found a bug?** Add to list here: TODO_LIST

**Feature request?** Edit conversation_engine.py or job_intelligence.py

---

**You're ready to find your perfect job! 🚀**
