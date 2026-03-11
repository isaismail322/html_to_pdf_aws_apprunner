import os
os.environ['FONTCONFIG_PATH'] = '/etc/fonts'
os.environ['TMPDIR'] = '/tmp'
os.environ['HOME'] = '/tmp'
os.environ['PYTHONUNBUFFERED']='1'
import io
import json
import base64
import boto3
import uuid
from datetime import datetime
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


s3_client = boto3.client('s3')

def lambda_handler(event,context):
    try:
        # print("Event:", json.dumps(event))
        data = json.loads(event["body"])
        #print(data)
        html_content = data.get('html_content')
        output_filename = data.get('filename')
        #print(html_content)
        #print(output_filename)
        if not html_content:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'html_content missing'})
            }
        font_config = FontConfiguration()
        css = CSS(string='''
@page {
    size: A4;
    margin: 30px;
}

html, body {
    height: 100%;
    margin: 0;
}''')

        # Convert HTML to PDF
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css],pdf_variant="pdf/a-3b")
        print(f"PDF bytes generated: {len(pdf_bytes)}")

        if len(pdf_bytes) == 0:
            raise Exception("PDF generation failed")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"generated-pdfs/{timestamp}_{unique_id}_{output_filename}"

        # Your bucket name (replace with actual name)
        bucket_name = "lambda-html-to-pdf-file-storage"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf',
            ContentDisposition=f'attachment; filename="{output_filename}"',
            CacheControl='max-age=86400'  # Cache for 24 hours
        )
        
        # Generate public URL
        public_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        
        print(f"PDF uploaded to S3: {public_url}")
        # Save to /tmp (mapped to your local machine)
        # output_path = f"/tmp/{output_filename}"
        # with open(output_path, 'wb') as f:
        #     f.write(pdf_bytes)
        
        # print(f"PDF saved to {output_path}")


        return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*' #,
                    # 'Content-Disposition': f'attachment; filename={output_filename}'
                },
                # 'isBase64Encoded': True,
                # 'body': base64.b64encode(pdf_bytes).decode('utf-8')
                'body': json.dumps({'message': f'PDF generated successfully',
                                    'download_url': public_url,
                                    'filename': output_filename})
            }
    # pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    # Return base64 encoded PDF
    # return {
    #     'statusCode': 200,
    #     'headers': {
    #         'Content-Type': 'application/pdf',
    #         'Access-Control-Allow-Origin': '*',
    #         'Content-Disposition': 'attachment; filename=generated.pdf'
    #         },
    #         'isBase64Encoded': True,
    #         'body': pdf_base64
    #         }
    except Exception as e:
        import traceback
        traceback.print_exc()  # Full stack trace in CloudWatch
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }