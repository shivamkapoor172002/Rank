# SEO Rank Tracker

A Flask-based tool to track Google search rankings, store data in CSVs, and analyze trends using Microsoft's Phi-3 model via Ollama. Features a clean UI for single and batch searches, ranking history, LLM-powered insights, and trend visualizations.

## Features

- Scrape Google to fetch rank, title, and URL for any keyword.
- Perform batch keyword searches with progress tracking.
- Store and export historical rankings as CSV files.
- Analyze rank trends, title shifts, and URL changes using Phi-3 via Ollama.
- Dashboard with key statistics such as total searches and average rank.
- Interactive trend charts powered by Chart.js.
- Robust error handling for scraping and LLM operations.

## Visuals

![Dashboard](https://github.com/user-attachments/assets/81e17d61-93cb-47c3-9265-a28cdfc5963e)
![Search Page](https://github.com/user-attachments/assets/6fd67406-e885-43d6-87dd-5ff3646a1ecc)
![Analysis](https://github.com/user-attachments/assets/2874816b-22f8-459c-afe0-9370e5fee0f8)
![Trends](https://github.com/user-attachments/assets/686c2127-d613-4b55-be7e-d3d558567e8e)

## Project Structure

![image](https://github.com/user-attachments/assets/cb30d587-b314-412b-a667-f712e9bd4e03)


## Pipeline

- *Scraping*: Uses Selenium to scrape Google (with randomized delay), BeautifulSoup to parse HTML.
- *Storage*: Saves results as CSVs in ranking_data/ using pandas and portalocker for thread safety.
- *LLM Analysis*:
  - Chunks CSV data (10 records at a time).
  - Prompts Phi-3 via Ollama for ranking trend insights.
  - Retries failed calls (3 attempts with 2-second delay).
- *UI*: Built with Flask (Jinja2), Select2 for dropdowns, and Chart.js for visualizations.

## Technologies

- *Backend*: Python, Flask, Selenium, BeautifulSoup, pandas, requests, retrying
- *Frontend*: HTML/CSS/JS, Chart.js, Select2, jQuery
- *AI*: Ollama + Phi-3 Mini (3.8B model)
- *Other*: ChromeDriver, Git

## Setup

# Clone Repo
git clone https://github.com/Amiradha/AgenticAI_WebRanking
cd webreinvent-seo-tracker

# Virtual Environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Dependencies
pip install flask selenium beautifulsoup4 pandas requests retrying portalocker webdriver-manager

# Setup Ollama
ollama pull phi3
ollama serve
ollama run phi3

# Run App
python run.py
