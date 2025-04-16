from flask import Blueprint, render_template, jsonify, request
import pandas as pd
import os
import random
import logging
from app import db

bp = Blueprint('extras', __name__)
logger = logging.getLogger(__name__)

@bp.route('/dashboard')
def dashboard():
    try:
        results = db.get_all_results()
        if not results:
            return render_template('dashboard.html', summary={
                'total_searches': 0,
                'unique_keywords': 0,
                'average_rank': 'N/A',
                'best_rank': 'N/A',
                'worst_rank': 'N/A',
                'recent_searches': []
            })

        df = pd.DataFrame(results)
        total_searches = len(df)
        unique_keywords = len(df['keyword'].unique())
        
        numeric_ranks = df[df['rank'].apply(lambda x: isinstance(x, str) and x.strip().isdigit())]['rank'].astype(int)
        average_rank = round(numeric_ranks.mean(), 2) if not numeric_ranks.empty else 'N/A'
        best_rank = numeric_ranks.min() if not numeric_ranks.empty else 'N/A'
        worst_rank = numeric_ranks.max() if not numeric_ranks.empty else 'N/A'
        
        recent_searches = df.tail(5)[['timestamp', 'keyword', 'rank']].to_dict('records')
        
        summary = {
            'total_searches': total_searches,
            'unique_keywords': unique_keywords,
            'average_rank': average_rank,
            'best_rank': best_rank,
            'worst_rank': worst_rank,
            'recent_searches': recent_searches
        }
        
        return render_template('dashboard.html', summary=summary)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render_template('dashboard.html', error=f"Error loading dashboard: {str(e)}")

@bp.route('/trends')
def trends():
    try:
        keywords = db.get_all_keywords()
        return render_template('trends.html', keywords=keywords)
    except Exception as e:
        logger.error(f"Trends error: {str(e)}")
        return render_template('trends.html', error=f"Error loading trends: {str(e)}")

@bp.route('/chart_data')
def chart_data():
    try:
        keyword = request.args.get('keyword')
        logger.info(f"Fetching chart data for keyword: {keyword}")
        if keyword == 'All':
            keywords = db.get_all_keywords()
            datasets = []
            for kw in keywords:
                history = db.get_keyword_history(kw)
                if history:
                    logger.info(f"Raw history for {kw}: {history}")
                    timestamps = [item['timestamp'][:10] for item in history]
                    ranks = [int(float(str(item['rank']).strip())) if str(item['rank']).replace('.', '').isdigit() else None for item in history]
                    logger.info(f"Processed history for {kw}: timestamps={timestamps}, ranks={ranks}")
                    if any(r is not None for r in ranks):
                        datasets.append({
                            'label': kw,
                            'data': ranks,
                            'borderColor': f'rgb({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)})',
                            'fill': False
                        })
            return jsonify({
                'labels': timestamps if datasets else [],
                'datasets': datasets
            })
        else:
            history = db.get_keyword_history(keyword)
            if not history:
                logger.warning(f"No history found for {keyword}")
                return jsonify({'labels': [], 'datasets': []})
            
            logger.info(f"Raw history for {keyword}: {history}")
            timestamps = [item['timestamp'][:10] for item in history]
            ranks = [int(float(str(item['rank']).strip())) if str(item['rank']).replace('.', '').isdigit() else None for item in history]
            logger.info(f"Processed history for {keyword}: timestamps={timestamps}, ranks={ranks}")
            
            datasets = [{
                'label': keyword,
                'data': ranks,
                'borderColor': 'blue',
                'fill': False
            }]
            
            return jsonify({
                'labels': timestamps,
                'datasets': datasets
            })
    except Exception as e:
        logger.error(f"Chart data error for {keyword}: {str(e)}")
        return jsonify({'error': f"Error fetching chart data: {str(e)}"})