from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import datetime
import threading
import csv
import random
import logging
from html import escape
import portalocker
import re
import requests
import json
import numpy as np
import retrying


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)


def clean_old_files(directory="search_results", days=7):
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = (time.time() - os.path.getmtime(file_path)) / (24 * 3600)
                if file_age > days:
                    os.remove(file_path)
                    logger.info(f"Deleted old file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning old files: {e}")

def sanitize_filename(keyword):
    """Sanitize keyword to create a valid filename."""
    return re.sub(r'[^\w\s-]', '_', keyword.strip()).replace(' ', '_')

def get_web_rank(keyword):
    driver = None
    try:
        options = Options()
        options.headless = True
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        query = keyword.replace(" ", "+")
        url = f"https://www.google.com/search?q={query}&num=20"
        driver.get(url)
        time.sleep(random.uniform(2, 5))

        html = driver.page_source
        os.makedirs("search_results", exist_ok=True)
        sanitized_keyword = sanitize_filename(keyword)
        html_file = f"search_results/{sanitized_keyword}.html"
        with open(html_file, "w", encoding="utf-8") as file:
            file.write(html)
        logger.info(f"Saved search results to {html_file}")

        soup = BeautifulSoup(html, 'html.parser')
        results = soup.find_all('div', class_='tF2Cxc')

        for index, result in enumerate(results, start=1):
            link = result.find('a', href=True)
            title = result.find('h3')
            if link and 'web.com' in link['href']:
                return {
                    "rank": index,
                    "title": title.text if title else "No Title Found",
                    "url": link['href']
                }
        return None

    except Exception as e:
        logger.error(f"Error scraping for keyword '{keyword}': {e}")
        return None

    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
        clean_old_files()

class RankingDatabase:
    def __init__(self):
        self.data_dir = "ranking_data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_csv_path(self, keyword):
        """Get CSV path for a keyword."""
        sanitized_keyword = sanitize_filename(keyword)
        return os.path.join(self.data_dir, f"{sanitized_keyword}.csv")
    
    def save_result(self, keyword, result):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        csv_path = self._get_csv_path(keyword)
        
        if not os.path.exists(csv_path):
            with open(csv_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp', 'keyword', 'rank', 'title', 'url'])
        
        try:
            with portalocker.Lock(csv_path, mode='a', timeout=5, newline='') as file:
                writer = csv.writer(file)
                if result:
                    writer.writerow([timestamp, keyword, str(result['rank']), result['title'], result['url']])
                else:
                    writer.writerow([timestamp, keyword, 'Not found', 'N/A', 'N/A'])
                logger.info(f"Saved result for keyword '{keyword}' to {csv_path}")
        except Exception as e:
            logger.error(f"Error saving result for '{keyword}': {e}")
    
    def get_all_results(self):
        results = []
        for csv_file in os.listdir(self.data_dir):
            if csv_file.endswith('.csv'):
                csv_path = os.path.join(self.data_dir, csv_file)
                try:
                    df = pd.read_csv(
                        csv_path,
                        on_bad_lines='skip',
                        quoting=1,
                        encoding='utf-8',
                        delimiter=','
                    )
                    df = df.fillna('N/A')
                    results.extend(df.to_dict('records'))
                except Exception as e:
                    logger.error(f"Error reading {csv_file}: {e}")
        return results
    
    def get_keyword_history(self, keyword):
        csv_path = self._get_csv_path(keyword)
        if not os.path.exists(csv_path):
            return []
        try:
            df = pd.read_csv(
                csv_path,
                on_bad_lines='skip',
                quoting=1,
                encoding='utf-8',
                delimiter=','
            )
            df = df.fillna('N/A')
            logger.info(f"Raw data from {csv_path}: {df.to_dict('records')}")
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error reading history for '{keyword}': {e}")
            return []
    
    def get_all_keywords(self):
        """Return list of unique keywords from CSVs."""
        keywords = set()
        for csv_file in os.listdir(self.data_dir):
            if csv_file.endswith('.csv'):
                keyword = csv_file[:-4].replace('_', ' ')
                keywords.add(keyword)
        return sorted(list(keywords))

db = RankingDatabase()

DEFAULT_KEYWORDS = [
    "Laravel development company",
    "Laravel Development Services Company",
    "Laravel development services",
    "Laravel development company in India",
    "Laravel development company in Delhi",
    "NuxtJs Development Services Company India",
    "Nuxt.js Development",
    "Software Product Development Services",
    "Product development company in india",
    "Software product development company"
]

tasks = {}

def run_batch_search(keywords, task_id):
    try:
        results = {}
        for keyword in keywords:
            result = get_web_rank(keyword)
            results[keyword] = result
            db.save_result(keyword, result)
            tasks[task_id]['progress'] += 1
            logger.info(f"Completed search for '{keyword}' in task {task_id}")
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['results'] = results
    except Exception as e:
        logger.error(f"Error in batch search task {task_id}: {e}")
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = str(e)

# LLM Analysis Functions
@retrying.retry(
    stop_max_attempt_number=3,
    wait_fixed=2000,
    retry_on_exception=lambda e: isinstance(e, (requests.exceptions.RequestException,))
)
def ask_phi(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json().get("response", "⚠ No response from model.")
    except Exception as e:
        logger.error(f"Error contacting PHI model: {e}")
        raise e

def analyze_keyword_data(keyword):
    csv_path = db._get_csv_path(keyword)
    if not os.path.exists(csv_path):
        logger.warning(f"No CSV found for keyword: {keyword}")
        return {"error": f"No data found for keyword: {keyword}"}
    
    try:
        df = pd.read_csv(
            csv_path,
            on_bad_lines='skip',
            quoting=1,
            encoding='utf-8',
            delimiter=','
        )
        df = df.fillna('N/A')
        logger.info(f"Loaded CSV for {keyword}: {len(df)} rows")
    except Exception as e:
        logger.error(f"Error reading CSV for {keyword}: {e}")
        return {"error": f"Error reading CSV for {keyword}: {str(e)}"}
    
    def chunk_dataframe(dataframe, chunk_size=10):
        for start in range(0, len(dataframe), chunk_size):
            yield dataframe.iloc[start:start + chunk_size].to_dict(orient='records')
    
    analysis_results = []
    for i, chunk in enumerate(chunk_dataframe(df)):
        ranks = [row["rank"] for row in chunk]
        dates = [row["timestamp"] for row in chunk]
        
        prompt = f"""
You are a search ranking analyst. Analyze the following keyword trend data.

Each record contains: timestamp, keyword, rank, title, and URL.

Data:
{json.dumps(chunk, indent=2)}

Based on this data:
1. Identify if the rank is improving, declining, or stable.
2. Mention the highest and lowest ranks and the corresponding dates.
3. Point out if title or URL changed.
4. Keep it short, clear, and fact-based. Avoid guessing beyond the data.
"""
        
        try:
            result = ask_phi(prompt)
            analysis_results.append({
                "chunk": i + 1,
                "analysis": result
            })
            logger.info(f"Analyzed chunk {i+1} for {keyword}")
        except Exception as e:
            analysis_results.append({
                "chunk": i + 1,
                "analysis": f"❌ Error analyzing chunk: {str(e)}"
            })
            logger.error(f"Error analyzing chunk {i+1} for {keyword}: {e}")
    
    return {
        "keyword": keyword,
        "analyses": analysis_results,
        "total_rows": len(df)
    }

@app.route('/')
def index():
    try:
        return render_template('index.html', default_keywords=DEFAULT_KEYWORDS)
    except Exception as e:
        logger.error(f"Error rendering index: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        keyword = request.form.get('keyword')
        if not keyword:
            return jsonify({'error': 'No keyword provided'}), 400
        keyword = escape(keyword.strip())
        if not keyword:
            return jsonify({'error': 'Invalid keyword'}), 400
        
        result = get_web_rank(keyword)
        db.save_result(keyword, result)
        
        return jsonify({
            'keyword': keyword,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/batch', methods=['POST'])
def batch_search():
    try:
        keywords = request.json.get('keywords', [])
        keywords = [escape(k.strip()) for k in keywords if k.strip()]
        if not keywords:
            return jsonify({'error': 'No valid keywords provided'}), 400
        
        task_id = f"task_{time.time()}"
        tasks[task_id] = {
            'keywords': keywords,
            'total': len(keywords),
            'progress': 0,
            'status': 'running',
            'results': {}
        }
        
        thread = threading.Thread(target=run_batch_search, args=(keywords, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'task_id': task_id})
    except Exception as e:
        logger.error(f"Error in batch endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/task/<task_id>')
def get_task_status(task_id):
    try:
        if task_id not in tasks:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(tasks[task_id])
    except Exception as e:
        logger.error(f"Error in task status endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/history')
def get_history():
    try:
        keyword = request.args.get('keyword')
        if keyword:
            keyword = escape(keyword.strip())
            history = db.get_keyword_history(keyword)
        else:
            history = db.get_all_results()
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error in history endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/export')
def export_data():
    try:
        results = db.get_all_results()
        if not results:
            return jsonify({'error': 'No data to export'}), 404
        
        export_path = os.path.join("ranking_data", "web_rankings_export.csv")
        df = pd.DataFrame(results)
        df.to_csv(export_path, index=False)
        
        return send_file(export_path, as_attachment=True, download_name='web_rankings.csv')
    except Exception as e:
        logger.error(f"Error in export endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/llm_analysis', methods=['GET'])
def llm_analysis():
    try:
        keyword = request.args.get('keyword')
        if not keyword:
            return jsonify({'error': 'No keyword provided'}), 400
        keyword = escape(keyword.strip())
        logger.info(f"Starting LLM analysis for keyword: {keyword}")
        result = analyze_keyword_data(keyword)
        logger.info(f"Completed LLM analysis for {keyword}: {len(result.get('analyses', []))} chunks")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in LLM analysis endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    os.makedirs("search_results", exist_ok=True)
    os.makedirs("ranking_data", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    app.run(debug=True, port=5000)