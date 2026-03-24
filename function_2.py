from flask import Flask, request, jsonify, send_file, current_app
import os, io, json, uuid, boto3, base64
from datetime import datetime
from playwright.sync_api import sync_playwright
import logging

app = Flask(__name__)

# S3_BUCKET = os.environ.get('S3_BUCKET', 'your-bucket-name')
# s3_client = boto3.client('s3')

logging.basicConfig(level=logging.INFO)

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
    filename="generated.pdf"
    try:
        content_type = (request.content_type or '').lower()
        return_type = 'application/pdf'
        # filename = request.args.get('filename', 'generated.pdf')
        #print("filename is :",filename)

        if 'application/json' in content_type:
            data = request.get_json()
            logging.info("data is received")
            html_content = data.get('html_content', '')
            logging.info("html content is received")
            filename = data.get('filename', filename)
            logging.info(f"filename is :{filename}")
            return_type = data.get('return_type', return_type)
            logging.info(f"return type is {return_type}")
        else:
            html_content = request.get_data(as_text=True)

        if not html_content:
            return jsonify({'error': 'html_content is required'}), 400
        
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            logging.info(f"filename {filename}")
        # Generate PDF
        browser = get_browser()
        logging.info("browser started")
        page = browser.new_page()
        logging.info("page loaded")
        try:
            # page.set_viewport_size({"width": 1280, "height": 720})
            page.set_content(html_content, wait_until='networkidle', timeout=30000)
            # Force a complete layout reflow before measuring
            logging.info("preparing the page state")
            page.evaluate("""() => {
                // Force reflow
                document.body.getBoundingClientRect();
                // Force all images/media to report their size
                return document.readyState;
            }""")
            # Wait for any delayed rendering (lazy loads, transitions, etc.)
            page.wait_for_function("() => document.readyState === 'complete'")
            logging.info("page is loaded full")
            page.wait_for_timeout(500)
            page.emulate_media(media="screen")
            # page.emulate_media(media="screen")

            # Measure true content dimensions (no viewport influence)
            # dimensions = page.evaluate("""() => {
            #                             // Shrink body to content, not viewport
            #                             document.body.style.display = 'inline-block';
            #                             return {
            #                                 width:  Math.ceil(document.body.scrollWidth),
            #                                 height: Math.ceil(document.body.scrollHeight)
            #                            };
            #                            }"""
            #                            )
            logging.info("evaluating the page size")
            dimensions = page.evaluate("""() => {
                                       document.body.style.display = 'inline-block';
                                        
                                        // Get the bottom-most point of ALL elements on the page
                                        const all = document.querySelectorAll('*');
                                        let maxBottom = 0;
                                        let maxRight = 0;
                                        
                                        all.forEach(el => {
                                            const rect = el.getBoundingClientRect();
                                            if (rect.bottom > maxBottom) maxBottom = rect.bottom;
                                            if (rect.right  > maxRight)  maxRight  = rect.right;
                                        });

                                        return {
                                            width:  Math.ceil(Math.max(document.body.scrollWidth,  maxRight)),
                                            height: Math.ceil(Math.max(document.body.scrollHeight, maxBottom))
                                        };
                                    }""")

            MARGIN_IN = 0.5
            MARGIN_PX = int(MARGIN_IN * 96)
            BUFFER_PX = 50

            content_width  = max(dimensions['width'],  1)
            content_height = max(dimensions['height'], 1)

            viewport_width = max(content_width + MARGIN_PX * 2, 800)
            viewport_height = max(content_height + MARGIN_PX * 2 + BUFFER_PX, 600)
            page.set_viewport_size({"width": viewport_width, "height": viewport_height})
            logging.info(f"viewport set to {viewport_width}x{viewport_height}")

            logging.info(f"content width is {content_width} and height is {content_height}")  
            pdf_bytes = page.pdf(
                # prefer_css_page_size=True,
                # page_ranges='1',
                # format='Letter',
                # scale=1,
                # prefer_css_page_size=True,
                width=f"{content_width}px",
                height=f"{content_height + BUFFER_PX}px",
                print_background=True,
                scale=1,
                prefer_css_page_size=False,
                margin={'top': '0in', 'bottom': '0in', 'left': '0in', 'right': '0in'}
                )
            logging.info("pdf generated")
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
