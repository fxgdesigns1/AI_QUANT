#!/usr/bin/env python3
"""
Reports API - Serve Monthly & Weekly Analysis Reports
Converts markdown reports to HTML for dashboard display
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
from flask import jsonify, Response, request

logger = logging.getLogger(__name__)

# Report files to serve
REPORT_FILES = {
    'comprehensive_summary': {
        'file': 'COMPREHENSIVE_ANALYSIS_SUMMARY.md',
        'title': '📊 Comprehensive Analysis Summary',
        'description': 'Complete overview of monthly and weekly analysis'
    },
    'october_analysis': {
        'file': 'OCTOBER_2025_MONTHLY_ANALYSIS.md',
        'title': '📈 October 2025 Monthly Analysis',
        'description': 'Full breakdown of October performance by strategy and pair'
    },
    'november_roadmap': {
        'file': 'NOVEMBER_2025_MONTHLY_ROADMAP.md',
        'title': '🗺️ November 2025 Monthly Roadmap',
        'description': 'Strategic plan for November with weekly milestones'
    },
    'weekly_breakdown': {
        'file': 'WEEKLY_PERFORMANCE_BREAKDOWN.md',
        'title': '📅 Weekly Performance Breakdown',
        'description': 'Current week analysis and performance metrics'
    },
    'weekly_roadmap': {
        'file': 'WEEKLY_ROADMAP.md',
        'title': '🗺️ Weekly Roadmap',
        'description': "This week's action plan and daily objectives"
    }
}

def get_reports_directory() -> Path:
    """Get the directory where reports are stored"""
    # Reports are in the project root (same level as google-cloud-trading-system)
    current_file = Path(__file__)
    # Go up: utils -> src -> google-cloud-trading-system -> quant_system_clean
    project_root = current_file.parent.parent.parent.parent
    return project_root

def list_reports() -> List[Dict]:
    """List all available reports"""
    reports_dir = get_reports_directory()
    available_reports = []
    
    for report_id, report_info in REPORT_FILES.items():
        report_path = reports_dir / report_info['file']
        exists = report_path.exists()
        
        report_data = {
            'id': report_id,
            'title': report_info['title'],
            'description': report_info['description'],
            'available': exists,
            'filename': report_info['file']
        }
        
        if exists:
            # Get file metadata
            stat = report_path.stat()
            report_data['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            report_data['size'] = stat.st_size
        
        available_reports.append(report_data)
    
    return available_reports

def get_report_content(report_id: str, format: str = 'html') -> Optional[Dict]:
    """
    Get report content
    
    Args:
        report_id: ID of the report (from REPORT_FILES keys)
        format: 'html' or 'markdown'
    
    Returns:
        Dict with 'content' and 'metadata' or None if not found
    """
    if report_id not in REPORT_FILES:
        return None
    
    report_info = REPORT_FILES[report_id]
    reports_dir = get_reports_directory()
    report_path = reports_dir / report_info['file']
    
    if not report_path.exists():
        return None
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        metadata = {
            'id': report_id,
            'title': report_info['title'],
            'description': report_info['description'],
            'filename': report_info['file'],
            'modified': datetime.fromtimestamp(report_path.stat().st_mtime).isoformat()
        }
        
        if format == 'html':
            # Convert markdown to HTML
            if MARKDOWN_AVAILABLE:
                try:
                    html_content = markdown.markdown(
                        markdown_content,
                        extensions=['fenced_code', 'tables']
                    )
                except Exception as e:
                    logger.warning(f"Markdown conversion failed: {e}, using basic formatting")
                    # Fallback: basic HTML formatting
                    html_content = markdown_content.replace('\n', '<br>')
            else:
                # Fallback if markdown not available
                html_content = markdown_content.replace('\n', '<br>').replace('**', '<strong>').replace('**', '</strong>')
            return {
                'content': html_content,
                'metadata': metadata,
                'format': 'html'
            }
        else:
            return {
                'content': markdown_content,
                'metadata': metadata,
                'format': 'markdown'
            }
    
    except Exception as e:
        logger.error(f"❌ Error reading report {report_id}: {e}")
        return None

def register_reports_routes(app):
    """Register report API routes with Flask app"""
    
    @app.route('/api/reports')
    def api_list_reports():
        """List all available reports"""
        try:
            reports = list_reports()
            return jsonify({
                'success': True,
                'reports': reports,
                'count': len(reports),
                'available_count': sum(1 for r in reports if r['available'])
            })
        except Exception as e:
            logger.error(f"❌ Error listing reports: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/reports/<report_id>')
    def api_get_report(report_id: str):
        """Get a specific report"""
        try:
            format = request.args.get('format', 'html')
            report_data = get_report_content(report_id, format=format)
            
            if report_data:
                return jsonify({
                    'success': True,
                    **report_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Report not found'
                }), 404
        
        except Exception as e:
            logger.error(f"❌ Error getting report {report_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/reports/<report_id>/download')
    def api_download_report(report_id: str):
        """Download report as markdown file"""
        try:
            report_data = get_report_content(report_id, format='markdown')
            
            if report_data:
                filename = report_data['metadata']['filename']
                return Response(
                    report_data['content'],
                    mimetype='text/markdown',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'Report not found'
                }), 404
        
        except Exception as e:
            logger.error(f"❌ Error downloading report {report_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    logger.info("✅ Reports API routes registered")

