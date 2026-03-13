from flask import Flask, request, jsonify, send_file, current_app
import os, io, json, uuid, boto3, base64
from datetime import datetime
from playwright.sync_api import sync_playwright

app = Flask(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET', 'your-bucket-name')
s3_client = boto3.client('s3')

_playwright = None
_browser = None

def get_browser():
    global _playwright, _browser
    if _browser is not None:
        try:
            _browser.contexts
            return _browser
        except:
            _browser = None
            _playwright = None

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(args=[
        '--no-sandbox', '--disable-setuid-sandbox',
        '--disable-dev-shm-usage', '--disable-gpu',
    ])
    return _browser

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/returning', methods=['POST'])
def returning():
    try:
        content_type = (request.content_type or '').lower()
        filename = request.args.get('filename', 'generated.pdf')

        if 'application/json' in content_type:
            data = request.get_json()
            html_content = data.get('html_content', '')
            filename = data.get('filename', filename)
            return_type = data.get('return_type',content_type)
        else:
            html_content = request.get_data(as_text=True)

        if not html_content:
            return jsonify({'error': 'html_content is required'}), 400
        
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            print("filename {filename}")
        # Generate PDF
        browser = get_browser()
        page = browser.new_page()
        try:
            page.set_content(html_content, wait_until='networkidle', timeout=30000)
            page.emulate_media(media="screen")
            # page.set_viewport_size({"width": 1280, "height": 900})

            # Inject print CSS to prevent page breaks
            # page.add_style_tag(content="""
            #                    * {
            #                    -webkit-print-color-adjust: exact !important;
            #                     print-color-adjust: exact !important;
            #                     box-sizing: border-box;
            #                    }
            #                    body {
            #                     margin: 0 !important;
            #                     padding: 0 !important;
            #                     width: 1280px !important;
            #                    }
            #                     /* Prevent unwanted page breaks */
            #                     tr, td, th, li, p, div {
            #                     page-break-inside: avoid;
            #                    }
            #                    """)
            # Get actual content height
            # height = page.evaluate("document.documentElement.scrollHeight")
            # width  = page.evaluate("document.documentElement.scrollWidth")
            pdf_bytes = page.pdf(
                prefer_css_page_size=True,
                page_ranges='1',
                format='Letter',
                scale=1,
                # width=f"{width}px",
                # height=f"{height}px",
                print_background=True
                )
        finally:
            page.close()
            # browser.close()
            if return_type == "application/pdf":
                return send_file(
                    io.BytesIO(pdf_bytes),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=filename
                    )
            else:
                return jsonify({'status': 'healthy',
                                'content':html_content,
                                'pdf': base64.b64encode(pdf_bytes).decode('utf-8'),
                                'filename':filename,
                                'pdf_len':len(pdf_bytes),
                                'return_type':return_type,
                                }), 200
         
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# @app.route('/convert', methods=['POST'])
# def convert():
#     try:
#         content_type = (request.content_type or '').lower()
#         filename = request.args.get('filename', 'generated.pdf')

#         if 'application/json' in content_type:
#             data = request.get_json()
#             html_content = data.get('html_content', '')
#             filename = data.get('filename', filename)
#         else:
#             html_content = request.get_data(as_text=True)

#         if not html_content:
#             return jsonify({'error': 'html_content is required'}), 400

#         if not filename.lower().endswith('.pdf'):
#             filename += '.pdf'
#         print(filename)
#         # Generate PDF
#         browser = get_browser()
#         page = browser.new_page()
#         try:
#             page.set_content(html_content, wait_until='networkidle', timeout=30000)
#             pdf_bytes = page.pdf(format='A4', print_background=True)
#         finally:
#             page.close()
#             browser.close()

#         # Upload to S3
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         unique_id = str(uuid.uuid4())[:8]
#         s3_key = f"generated-pdfs/{timestamp}_{unique_id}_{filename}"

#         s3_client.upload_fileobj(
#             io.BytesIO(pdf_bytes), S3_BUCKET, s3_key,
#             ExtraArgs={'ContentType': 'application/pdf'}
#         )

#         download_url = s3_client.generate_presigned_url(
#             'get_object',
#             Params={'Bucket': S3_BUCKET, 'Key': s3_key},
#             ExpiresIn=3600
#         )

#         return jsonify({
#             'message': 'PDF generated successfully',
#             'download_url': download_url,
#             'filename': filename,
#             'size_bytes': len(pdf_bytes)
#         }), 200

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=False)