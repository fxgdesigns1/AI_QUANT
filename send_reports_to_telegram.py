#!/usr/bin/env python3
"""
Send Monthly & Weekly Analysis Reports to Telegram
Splits long reports into multiple messages to respect Telegram limits
"""

import os
import sys
import requests
from pathlib import Path
from typing import List, Optional

# Telegram Configuration
TELEGRAM_CHAT_ID = "6100678501"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096  # Telegram limit

def get_telegram_token() -> Optional[str]:
    """Get Telegram token from environment or config files"""
    token = os.getenv('TELEGRAM_TOKEN')
    if not token or token in ['your_telegram_bot_token_here', '']:
        # Try alternative sources
        try:
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv('TELEGRAM_TOKEN')
        except:
            pass
    
    # Try reading from config files
    if not token or token in ['your_telegram_bot_token_here', '']:
        try:
            # Try app.yaml files
            config_files = [
                'google-cloud-trading-system/config/app.yaml',
                'google-cloud-trading-system/config/app_corrected.yaml',
            ]
            
            import yaml
            for config_file in config_files:
                config_path = Path(__file__).parent / config_file
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        if config and 'env_variables' in config:
                            token = config['env_variables'].get('TELEGRAM_TOKEN')
                            if token and token not in ['your_telegram_bot_token_here', '']:
                                break
        except Exception as e:
            print(f"⚠️  Could not read config files: {e}")
    
    # Try from credentials file
    if not token or token in ['your_telegram_bot_token_here', '']:
        try:
            creds_file = Path(__file__).parent / 'COMPLETE_CREDENTIALS_READABLE.txt'
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    content = f.read()
                    # Look for bot token pattern
                    import re
                    match = re.search(r'Bot Token:\s*([A-Za-z0-9:_-]+)', content)
                    if match:
                        token = match.group(1)
        except:
            pass
    
    # Last resort fallback tokens (in order of likelihood)
    if not token or token in ['your_telegram_bot_token_here', '']:
        fallback_tokens = [
            '7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs',  # From app.yaml
            '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU',  # From credentials
        ]
        # Try first fallback
        token = fallback_tokens[0]
    
    return token

def send_telegram_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send message to Telegram"""
    token = get_telegram_token()
    if not token:
        print("❌ Telegram token not found")
        return False
    
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        
        # Try with Markdown first, fall back to plain text if parsing fails
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, data=data, timeout=15)
        if response.status_code == 200:
            return True
        else:
            # If Markdown parsing fails, try without parse_mode
            if response.status_code == 400 and 'parse' in response.text.lower():
                print(f"   ⚠️  Markdown parsing error, trying plain text...")
                data.pop('parse_mode')
                response = requests.post(url, data=data, timeout=15)
                if response.status_code == 200:
                    return True
            
            print(f"❌ Telegram error: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False

def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> List[str]:
    """Split long message into chunks"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by lines first to preserve formatting
    lines = text.split('\n')
    
    for line in lines:
        # If adding this line would exceed limit, save current chunk and start new
        test_chunk = current_chunk + '\n' + line if current_chunk else line
        
        if len(test_chunk) > max_length - 50:  # Leave some buffer
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                # Single line is too long, split it
                words = line.split(' ')
                for word in words:
                    if len(current_chunk + ' ' + word) > max_length - 50:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
                    else:
                        current_chunk += ' ' + word if current_chunk else word
        else:
            current_chunk = test_chunk
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def format_report_for_telegram(content: str, title: str) -> List[str]:
    """Format report with header and split if needed"""
    header = f"📊 *{title}*\n\n"
    full_text = header + content
    
    chunks = split_message(full_text)
    
    # Add page numbers if split
    if len(chunks) > 1:
        formatted_chunks = []
        for i, chunk in enumerate(chunks, 1):
            page_header = f"📊 *{title}*\n📄 Page {i}/{len(chunks)}\n\n"
            formatted_chunks.append(page_header + chunk)
        return formatted_chunks
    
    return chunks

def send_report_file(file_path: Path, report_name: str) -> bool:
    """Send a report file to Telegram"""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False
    
    print(f"📤 Sending {report_name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Format and split
        chunks = format_report_for_telegram(content, report_name)
        
        # Send each chunk with delay
        success = True
        for i, chunk in enumerate(chunks):
            if not send_telegram_message(chunk):
                success = False
                break
            
            # Small delay between messages to avoid rate limiting
            if i < len(chunks) - 1:
                import time
                time.sleep(1)
        
        if success:
            print(f"   ✅ Sent ({len(chunks)} message(s))")
        else:
            print(f"   ❌ Failed to send")
        
        return success
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Send all reports to Telegram"""
    print("🚀 SENDING ANALYSIS REPORTS TO TELEGRAM")
    print("=" * 60)
    print()
    
    # Get project root
    project_root = Path(__file__).parent
    
    # List of reports to send
    reports = [
        ("COMPREHENSIVE_ANALYSIS_SUMMARY.md", "📊 COMPREHENSIVE ANALYSIS SUMMARY"),
        ("OCTOBER_2025_MONTHLY_ANALYSIS.md", "📈 OCTOBER 2025 MONTHLY ANALYSIS"),
        ("NOVEMBER_2025_MONTHLY_ROADMAP.md", "🗺️ NOVEMBER 2025 MONTHLY ROADMAP"),
        ("WEEKLY_PERFORMANCE_BREAKDOWN.md", "📅 WEEKLY PERFORMANCE BREAKDOWN"),
        ("WEEKLY_ROADMAP.md", "🗺️ WEEKLY ROADMAP"),
    ]
    
    # Check token
    token = get_telegram_token()
    if not token:
        print("❌ Telegram token not configured")
        print("   Set TELEGRAM_TOKEN environment variable")
        return
    
    print(f"📱 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"✅ Token: {'*' * 20}{token[-10:] if len(token) > 10 else token}")
    print()
    
    # Send header message
    header = """🎯 *MONTHLY & WEEKLY ANALYSIS REPORTS*

📊 Complete analysis reports generated and ready!

Reports being sent:
1. 📊 Comprehensive Analysis Summary
2. 📈 October 2025 Monthly Analysis  
3. 🗺️ November 2025 Monthly Roadmap
4. 📅 Weekly Performance Breakdown
5. 🗺️ Weekly Roadmap

_Starting transmission..._"""
    
    send_telegram_message(header)
    print("✅ Header sent")
    print()
    
    # Send each report
    results = []
    for filename, report_name in reports:
        file_path = project_root / filename
        success = send_report_file(file_path, report_name)
        results.append((report_name, success))
        
        # Delay between reports
        if reports.index((filename, report_name)) < len(reports) - 1:
            import time
            time.sleep(2)
    
    print()
    print("=" * 60)
    print("📊 TRANSMISSION SUMMARY")
    print("=" * 60)
    print()
    
    for report_name, success in results:
        status = "✅ Sent" if success else "❌ Failed"
        print(f"{status}: {report_name}")
    
    # Send completion message
    success_count = sum(1 for _, s in results if s)
    total_count = len(results)
    
    completion_msg = f"""✅ *TRANSMISSION COMPLETE*

📊 *Reports Sent:* {success_count}/{total_count}

{"✅ All reports sent successfully!" if success_count == total_count else "⚠️ Some reports failed to send"}

📁 All reports are also saved locally in your project directory.

_Check your Telegram for the full reports!_"""
    
    send_telegram_message(completion_msg)
    print()
    print("✅ Completion message sent")
    print()

if __name__ == "__main__":
    main()

