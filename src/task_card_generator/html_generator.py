"""HTML to image generation for task cards."""

import base64
import html
import logging
import os
import shutil
import tempfile
from io import BytesIO
from urllib.parse import quote
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configurable padding for ticket container (adjust per printer/machine)
TICKET_PADDING_TOP = int(os.getenv("TICKET_PADDING_TOP", "0"))
TICKET_PADDING_RIGHT = int(os.getenv("TICKET_PADDING_RIGHT", "8"))

try:
    import imgkit
    IMGKIT_AVAILABLE = True
except ImportError:
    IMGKIT_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    import time
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def create_task_html(task):
    """Create HTML content for task card with ticket-style design."""
    # Use the due_date from task if it's a Task object, otherwise use current date
    if hasattr(task, 'due_date'):
        # Parse ISO format date string and show as MM/DD for compact tickets
        from datetime import datetime as dt
        due_date_obj = dt.fromisoformat(task.due_date.replace('Z', '+00:00'))
        due_date_text = due_date_obj.strftime('%m/%d')
    else:
        # Fallback for dict format
        due_date_text = datetime.now().strftime("%m/%d")

    # Optional operator signature (for attribution/audit)
    if hasattr(task, 'operator_signature'):
        operator_signature = (task.operator_signature or "").strip()
    else:
        operator_signature = (task.get("operator_signature") or "").strip()
    operator_signature_safe = html.escape(operator_signature) if operator_signature else ""
    # Optional attachment (image shown at bottom)
    if hasattr(task, 'attachment_bytes'):
        attachment_bytes = task.attachment_bytes
    else:
        attachment_bytes = task.get("attachment_bytes")

    attachment_data_uri = None
    if attachment_bytes:
        try:
            image_type = "png"
            try:
                from PIL import Image
                with Image.open(BytesIO(attachment_bytes)) as img:
                    if img.format:
                        image_type = img.format.lower()
            except Exception:
                image_type = "png"
            encoded = base64.b64encode(attachment_bytes).decode("ascii")
            attachment_data_uri = f"data:image/{image_type};base64,{encoded}"
        except Exception:
            attachment_data_uri = None
    
    # Priority indicator - handle both Task object and dict
    if hasattr(task, 'priority'):
        # Task object with numeric priority
        priority_map = {1: ("⚡ ⚡ ⚡", "HIGH PRIORITY"),
                       2: ("⚡ ⚡", "MEDIUM PRIORITY"),
                       3: ("⚡", "LOW PRIORITY")}
        priority_dots, priority_text = priority_map.get(task.priority, ("⚡ ⚡", "MEDIUM PRIORITY"))
    else:
        # Dict format with string priority
        if task["priority"].upper() == "HIGH":
            priority_dots = "⚡ ⚡ ⚡"
            priority_text = "HIGH PRIORITY"
        elif task["priority"].upper() == "MEDIUM":
            priority_dots = "⚡ ⚡"
            priority_text = "MEDIUM PRIORITY"
        else:
            priority_dots = "⚡"
            priority_text = "LOW PRIORITY"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Microsoft JhengHei UI', 'Segoe UI', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', Arial, sans-serif;
                background-color: white;
                width: 576px;
                padding: 0;
                margin: 0;
            }}
            
            .ticket-container {{
                background: white;
                padding: {TICKET_PADDING_TOP}px {TICKET_PADDING_RIGHT}px 0 0;
                position: relative;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 3px;
            }}
            
            .ticket-label {{
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 4px;
                color: #000;
                margin-bottom: 16px;
            }}
            
            
            .priority-dots {{
                font-size: 48px;
                font-weight: bold;
                margin-top: 4px;
                color: #000;
                font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', 'Segoe UI', Arial, sans-serif;
            }}

            .operator-signature {{
                position: absolute;
                top: 6px;
                right: {TICKET_PADDING_RIGHT + 6}px;
                font-size: 16px;
                font-weight: 600;
                color: #111;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                white-space: nowrap;
            }}
            
            .perforation {{
                background: repeating-linear-gradient(
                    to right,
                    #000 0,
                    #000 6px,
                    transparent 6px,
                    transparent 12px
                );
                height: 3px;
                margin: 3px 0;
            }}
            
            .task-title {{
                text-align: center;
                padding: 8px 0;
            }}
            
            .task-title h1 {{
                font-size: 48px;
                font-weight: bold;
                line-height: 1.2;
                color: #000;
                word-wrap: break-word;
                max-width: 100%;
                overflow-wrap: break-word;
                hyphens: auto;
                margin: 0;
                padding: 0 10px;
            }}
            
            .dashed-line {{
                border-top: 3px dashed #666;
                margin: 4px 0;
            }}
            
            .due-date {{
                text-align: center;
            }}
            
            
            .due-date-text {{
                font-size: 32px;
                font-weight: bold;
                color: #000;
                margin-top: 2px;
            }}

            .attachment {{
                margin-top: 8px;
                text-align: center;
                padding: 0 6px;
            }}
            .attachment img {{
                width: 100%;
                max-width: 100%;
                max-height: 720px;
                border-radius: 6px;
                border: 2px dashed #666;
                object-fit: contain;
                display: block;
                margin: 0 auto;
            }}
            
            .bottom-perforation {{
                margin-top: 4px;
            }}
            
        </style>
    </head>
    <body>
        <div class="ticket-container">
            {"<div class=\"operator-signature\">BY " + operator_signature_safe + "</div>" if operator_signature_safe else ""}
            <!-- Lightning Bolts Only -->
            <div class="header">
                <div class="priority-dots">{priority_dots}</div>
            </div>
            
            <!-- Task Title -->
            <div class="task-title">
                <h1>{task.name if hasattr(task, 'name') else task["title"]}</h1>
            </div>
            
            <!-- Dashed Separator -->
            <div class="dashed-line"></div>
            
            <!-- Due Date Section -->
            <div class="due-date">
                <div class="due-date-text">{due_date_text}</div>
            </div>
            
            <!-- Attachment -->
            {f'<div class="attachment"><img src=\"{attachment_data_uri}\" alt=\"Attachment\" /></div>' if attachment_data_uri else ''}
            
            <!-- Bottom Perforation -->
            <div class="perforation bottom-perforation"></div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def html_to_image_imgkit(html_content, retain_file=True):
    """Convert HTML to image using imgkit (requires wkhtmltopdf)."""
    if not IMGKIT_AVAILABLE:
        logger.info("imgkit unavailable; skipping wkhtmltoimage conversion")
        return None, None
    logger.info("Rendering task card via imgkit/wkhtmltoimage")
    
    try:
        # Configure options for thermal printer size
        options = {
            'width': 576,  # 72mm thermal printer width
            'disable-smart-width': '',
            'encoding': 'UTF-8',
            'disable-local-file-access': '',
            'crop-w': 576,  # Crop to exact width
        }

        # Try to configure wkhtmltopdf path for Windows
        config = None
        import os
        possible_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltoimage.exe',
            r'C:\wkhtmltopdf\bin\wkhtmltoimage.exe'
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config = imgkit.config(wkhtmltoimage=path)
                break

        # Convert HTML to image, returning either a file or bytes
        if retain_file:
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_img.close()
            imgkit.from_string(html_content, temp_img.name, options=options, config=config)
            with open(temp_img.name, "rb") as f:
                img_bytes = f.read()
            logger.info("Task card rendered via imgkit: %s", temp_img.name)
            return temp_img.name, img_bytes

        img_bytes = imgkit.from_string(html_content, False, options=options, config=config)
        return None, img_bytes

    except Exception as e:
        logger.exception("imgkit conversion failed")
        return None, None


def html_to_image_selenium(html_content, retain_file=True):
    """Convert HTML to image using Selenium (requires Chrome/ChromeDriver)."""
    if not SELENIUM_AVAILABLE:
        logger.info("Selenium unavailable; skipping webdriver conversion")
        return None, None
    logger.info("Rendering task card via Selenium screenshot")
    
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=576,800')  # Tall enough to capture content
        # Use Chromium when google-chrome is not available (e.g. Debian slim)
        chromium_bin = shutil.which("chromium") or shutil.which("chromium-browser")
        if chromium_bin:
            chrome_options.binary_location = chromium_bin

        # Create webdriver
        driver = webdriver.Chrome(options=chrome_options)
        
        if retain_file:
            # Create temporary HTML file
            temp_html = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8')
            temp_html.write(html_content)
            temp_html.close()
            driver.get(f'file://{temp_html.name}')
        else:
            driver.get(f"data:text/html;charset=utf-8,{quote(html_content)}")
        
        # Wait for page to load
        time.sleep(1)
        
        # Get the ticket container element
        ticket_element = driver.find_element(By.CLASS_NAME, "ticket-container")
        
        if retain_file:
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_img.close()
            ticket_element.screenshot(temp_img.name)
            with open(temp_img.name, "rb") as f:
                img_bytes = f.read()
            driver.quit()
            logger.info("Task card rendered via Selenium: %s", temp_img.name)
            return temp_img.name, img_bytes

        img_bytes = ticket_element.screenshot_as_png
        driver.quit()
        return None, img_bytes
        
    except Exception as e:
        logger.exception("Selenium conversion failed")
        return None, None


def create_task_image(task_data, retain_file=True):
    """Create task card image from HTML, optionally avoiding filesystem writes."""
    html_content = create_task_html(task_data)

    logger.info("Starting task card image render; retain_file=%s", retain_file)
    image_path, image_bytes = html_to_image_imgkit(html_content, retain_file=retain_file)

    if image_bytes is None:
        logger.info("Falling back to Selenium for task card render")
        image_path, image_bytes = html_to_image_selenium(html_content, retain_file=retain_file)
    else:
        logger.info("imgkit render succeeded; skipping Selenium fallback")

    if image_bytes is None:
        logger.warning("Task card render failed in both imgkit and Selenium")

    return image_path, image_bytes


def create_task_html_image(task_data):
    """Create task card image and return the file path (retained on disk)."""
    image_path, _ = create_task_image(task_data, retain_file=True)
    return image_path
