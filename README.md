# 🚀 LLM Evaluation Platform

A comprehensive **Multi-Provider LLM Evaluation & Regression Testing Platform** for evaluating, comparing, and benchmarking Large Language Models (LLMs) and prompts across multiple providers.

🌐 **Live Demo:** https://llmevaluationplatform-m.streamlit.app/

---

## 📌 Overview

LLM Evaluation Platform helps developers, AI engineers, and prompt engineers measure the quality of LLM responses using automated evaluation pipelines.

Instead of manually checking responses, the platform automatically:

- Generates responses from selected LLMs
- Evaluates them using an LLM Judge
- Compares prompts or models
- Calculates quality metrics
- Detects regressions
- Generates downloadable reports
- Displays experiment history
- Supports CI/CD quality gates

---

# ✨ Features

## 🤖 Multi-Provider Support

Choose your preferred LLM provider.

Supported providers include:

- Groq
- Google Gemini
- OpenAI (Extensible)
- Anthropic (Extensible)
- Ollama (Future)
- Any OpenAI-compatible endpoint

Users can simply enter their own API key without modifying the code.

---

## 🧠 Flexible Evaluation

Evaluate:

- Prompt A vs Prompt B
- Model A vs Model B
- Same model with different prompts
- Different providers
- Baseline vs Candidate prompts

Example:

Baseline

```
Groq
llama-3.1-8b-instant
```

Candidate

```
Gemini 2.5 Flash
```

---

## 📊 Automatic Metrics

The platform measures:

- Pass Rate
- Correctness
- Faithfulness
- Relevancy
- Semantic Similarity
- Hallucination Rate
- Safety
- Latency
- Token Usage
- Estimated Cost (when available)

---

## 📈 Regression Detection

Automatically detects whether a new prompt or model:

✅ Improved

❌ Regressed

⚠️ Introduced hallucinations

⚠️ Became slower

⚠️ Reduced correctness

Perfect for continuous prompt engineering.

---

## 📁 Experiment Tracking

Each evaluation run is saved as a unique experiment.

Example:

```
reports/
└── experiments/
    ├── exp-20260630100302/
    ├── exp-20260630112110/
    └── exp-20260630142044/
```

Each experiment stores:

- experiment_summary.json
- test_results.csv
- prompt_comparison.csv
- model_comparison.csv
- quality_gates.csv
- failed_tests.csv
- fixed_tests.csv
- regressed_tests.csv

---

## 📦 Downloadable Reports

Download complete evaluation reports as ZIP files containing:

- JSON summaries
- CSV metrics
- Failed tests
- Quality gates
- Comparison reports

---

## 📚 Experiment History

View all previous evaluations inside the dashboard.

Includes:

- Experiment ID
- Generator Model
- Judge Model
- Pipeline Status
- Timestamp
- Metrics
- Report Location

---

# 📊 Dashboard

The Streamlit dashboard provides:

- Provider Selection
- API Key Input
- Prompt Upload
- Dataset Upload
- Evaluation Configuration
- Live Progress
- Charts
- Quality Gates
- Experiment History
- Report Downloads

---

# 🧪 Evaluation Pipeline

```
                User
                  │
                  ▼
        Select Generator Model
                  │
                  ▼
          Generate Responses
                  │
                  ▼
            LLM Judge
                  │
                  ▼
      Compute Evaluation Metrics
                  │
                  ▼
      Compare Baseline vs Candidate
                  │
                  ▼
      Detect Regressions
                  │
                  ▼
 Generate Reports + Dashboard Results
```

---

# 📋 Evaluation Metrics

| Metric | Description |
|---------|-------------|
| Correctness | Accuracy of the response |
| Faithfulness | Whether the answer follows the provided context |
| Relevancy | Whether the response answers the question |
| Hallucination | Measures fabricated information |
| Safety | Checks unsafe outputs |
| Latency | Response time |
| Pass Rate | Percentage of successful test cases |

---

# 📂 Project Structure

```
LLM-Evaluation-Platform/

├── dashboard/
├── prompts/
├── datasets/
├── reports/
│   └── experiments/
├── scripts/
├── tests/
├── app/
├── configs/
├── docs/
├── .github/
│   └── workflows/
├── requirements.txt
├── Dockerfile
├── README.md
└── .env.example
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/USERNAME/LLM-Evaluation-Platform.git
```

Move into the project

```bash
cd LLM-Evaluation-Platform
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create environment variables

```
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
```

Run the dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

---

# 🚀 GitHub CI/CD

The project includes GitHub Actions for automated evaluation.

Pipeline:

```
Push Code
      │
      ▼
Run Tests
      │
      ▼
Run LLM Evaluation
      │
      ▼
Generate Reports
      │
      ▼
Quality Gates
      │
      ▼
PASS ✅ / FAIL ❌
```

---

# 📊 Sample Workflow

1. Select Generator Model
2. Select Judge Model
3. Upload Dataset
4. Upload Baseline Prompt
5. Upload Candidate Prompt
6. Click **Run Evaluation**
7. Wait for evaluation
8. View dashboard
9. Download reports

---

# 💡 Example Use Cases

- Prompt Engineering
- AI Regression Testing
- LLM Benchmarking
- Enterprise AI QA
- RAG Evaluation
- CI/CD for LLM Applications
- Model Comparison
- Prompt Optimization

---

# 🛠️ Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- SQLite
- GitHub Actions
- Docker
- Groq API
- Gemini API
- OpenAI Compatible APIs

---

# 📸 Live Demo

🌐 **Application**

https://llmevaluationplatform-m.streamlit.app/

---

# 🔮 Future Enhancements

- Authentication
- Team Workspaces
- Leaderboards
- Hugging Face Integration
- Ollama Support
- Azure OpenAI
- AWS Bedrock
- Cost Dashboard
- Report Versioning
- Prompt Library
- RAG Evaluation Suite
- Batch Evaluations
- Benchmark Datasets
- Human Feedback Integration

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to GitHub
5. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Karthik Yadav**

Information Science & Engineering

AI | Machine Learning | Full Stack Development | LLM Engineering

---

⭐ If you found this project useful, consider giving it a Star on GitHub!
