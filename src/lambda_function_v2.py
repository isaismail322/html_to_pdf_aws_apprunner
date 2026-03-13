import os
import io
import json
import uuid
import base64
import boto3
from datetime import datetime
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

s3_client = boto3.client('s3')
BUCKET_NAME = "lambda-html-to-pdf-file-storage"
# Initialize browser once outside handler for reuse across invocations
playwright_instance = None
browser = None
def get_browser():
    global playwright_instance, browser
    if browser is None:
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch(
            headless=True,
            args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-audio-output',
            '--disable-extensions',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-first-run',
            '--disable-background-networking'
            ])
    print("browser launched successfully")
    return browser


def generate_pdf(html_content: str, pdf_options: dict = None) -> bytes:
    """Convert HTML to PDF bytes using headless Chromium."""
    browser = get_browser()
    page = browser.new_page()

    try:
        page.set_content(html_content, wait_until='networkidle', timeout=30000)

        options = {
            'format': 'A4',
            'print_background': True,
            # 'margin': {
            #     'top': '10mm',
            #     'bottom': '10mm',
            #     'left': '10mm',
            #     'right': '10mm'
            # }
        }

        if pdf_options:
            options.update(pdf_options)

        # Returns bytes in memory — no temp file
        pdf_bytes = page.pdf(**options)
        return pdf_bytes

    finally:
        page.close()


def upload_to_s3(pdf_bytes: bytes, filename: str) -> dict:
    """Upload PDF bytes buffer directly to S3."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    s3_key = f"{S3_FOLDER}/{timestamp}_{unique_id}_{filename}"

    # Stream buffer directly to S3
    buffer = io.BytesIO(pdf_bytes)
    s3_client.upload_fileobj(
        buffer,
        BUCKET_NAME,
        s3_key,
        ExtraArgs={
            'ContentType': 'application/pdf',
            'ContentDisposition': f'attachment; filename="{filename}"',
            'CacheControl': 'max-age=86400',
        }
    )

    # Presigned URL for download
    download_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=PDF_EXPIRES_IN
    )

    return {
        's3_key': s3_key,
        'download_url': download_url,
        'bucket': BUCKET_NAME,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for App Runner."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/convert', methods=['POST'])
def convert():
    """
    Convert HTML to PDF and store in S3.

    Accepts:
      - Content-Type: text/html        → raw HTML as body
      - Content-Type: application/json → { "html_content": "...", "filename": "...", "pdf_options": {} }
    
    Query params:
      - filename=output.pdf
      - orientation=landscape (optional shortcut)
      - format=A4 (optional shortcut)
    """
    try:
        content_type = (request.content_type or '').lower()
        filename = request.args.get('filename', 'generated.pdf')
        pdf_options = None

        # ── Parse request body ────────────────────────────────────
        if 'application/json' in content_type:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'error': 'Invalid JSON body'}), 400
            html_content = data.get('html_content', '')
            filename = data.get('filename', filename)
            pdf_options = data.get('pdf_options', None)

        elif 'text/html' in content_type or 'text/plain' in content_type:
            # Raw HTML body — just like pdfendpoint.com
            html_content = request.get_data(as_text=True)

        else:
            # Default: treat body as raw HTML
            html_content = request.get_data(as_text=True)

        if not html_content:
            return jsonify({'error': 'html_content is required'}), 400

        if not filename.endswith('.pdf'):
            filename += '.pdf'

        # ── Handle optional query param shortcuts ─────────────────
        orientation = request.args.get('orientation', '').lower()
        page_format = request.args.get('format', 'A4')

        if orientation == 'landscape' or page_format:
            pdf_options = pdf_options or {}
            pdf_options['format'] = page_format
            if orientation == 'landscape':
                pdf_options['landscape'] = True

        print(f"Converting HTML ({len(html_content)} chars) → {filename}")

        # ── Generate PDF → memory buffer ──────────────────────────
        pdf_bytes = generate_pdf(html_content, pdf_options)
        print(f"PDF generated: {len(pdf_bytes)} bytes")

        if not pdf_bytes:
            return jsonify({'error': 'PDF generation failed'}), 500

        # ── Upload buffer to S3 ───────────────────────────────────
        result = upload_to_s3(pdf_bytes, filename)
        print(f"Uploaded to S3: {result['s3_key']}")

        return jsonify({
            'message': 'PDF generated successfully',
            'download_url': result['download_url'],
            'filename': filename,
            's3_key': result['s3_key'],
            'size_bytes': len(pdf_bytes),
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500