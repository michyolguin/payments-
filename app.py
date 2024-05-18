from flask import Flask, request, render_template, redirect, url_for, send_file
import os
import pdfkit
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    user_info = request.form['user_info']
    items = request.form.getlist('items')
    files = request.files.getlist('receipts')

    request_id = save_submission(user_info, items, files)
    create_pdf(request_id, user_info, items)
    merged_pdf_path = merge_pdfs(request_id, files)
    send_email(merged_pdf_path)

    return redirect(url_for('status', request_id=request_id))

@app.route('/status/<int:request_id>')
def status(request_id):
    # Implement status check
    return f'Status of request {request_id}'

def save_submission(user_info, items, files):
    # Implement saving logic
    request_id = 1  # Get a unique request ID
    return request_id

def create_pdf(request_id, user_info, items):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'request_{request_id}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f'Request ID: {request_id}')
    c.drawString(100, 730, f'User Info: {user_info}')
    y = 710
    for item in items:
        c.drawString(100, y, item)
        y -= 20
    c.save()

def merge_pdfs(request_id, files):
    merger = PdfMerger()
    base_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'request_{request_id}.pdf')
    merger.append(base_pdf_path)

    for file in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        merger.append(filepath)

    merged_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'merged_request_{request_id}.pdf')
    merger.write(merged_pdf_path)
    merger.close()
    return merged_pdf_path

def send_email(pdf_path):
    sender_email = "your_email@example.com"
    receiver_email = "receiver@example.com"
    subject = "New Reimbursement Request"
    body = "Please find the attached reimbursement request."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
        msg.attach(part)

    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login(sender_email, "your_password")
        server.send_message(msg)

if __name__ == '__main__':
    app.run(debug=True)
