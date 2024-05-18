from flask import Flask, request, render_template, redirect, url_for, session, flash
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import secrets

app = Flask(__name__)

# Generate a secure secret key
app.secret_key = secrets.token_hex(16)

app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/start')
def start():
    return render_template('start.html')

@app.route('/general_info', methods=['POST'])
def general_info():
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    budget_number = request.form['budget_number']
    title = request.form['title']

    # Validate budget number contains a letter
    if not any(char.isalpha() for char in budget_number):
        flash('Budget number must contain at least one letter.')
        return redirect(url_for('start'))

    session['general_info'] = {
        'last_name': last_name,
        'first_name': first_name,
        'budget_number': budget_number,
        'title': title
    }

    return redirect(url_for('add_item'))

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        budget_line = request.form['budget_line']
        item_name = request.form['item_name']
        amount_chf = request.form['amount_chf']
        amount_other = request.form['amount_other']
        currency = request.form['currency']
        receipt = request.files['receipt']

        # Validate amounts
        if not amount_chf and (not amount_other or not currency):
            flash('You must provide either an amount in CHF or an amount in another currency with its abbreviation.')
            return redirect(url_for('add_item'))

        items = session.get('items', [])
        items.append({
            'budget_line': budget_line,
            'item_name': item_name,
            'amount_chf': amount_chf,
            'amount_other': amount_other,
            'currency': currency,
            'receipt': receipt.filename
        })
        session['items'] = items

        # Save receipt
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], receipt.filename)
        receipt.save(receipt_path)

        return redirect(url_for('add_item'))

    return render_template('add_item.html')

@app.route('/submit', methods=['POST'])
def submit():
    general_info = session.get('general_info')
    items = session.get('items', [])

    if not general_info or not items:
        flash('No general information or items found.')
        return redirect(url_for('start'))

    request_id = save_submission(general_info, items)
    create_pdf(request_id, general_info, items)
    merged_pdf_path = merge_pdfs(request_id, items)
    send_email(merged_pdf_path)

    session.clear()  # Clear the session to ensure new start

    return redirect(url_for('status', request_id=request_id))

@app.route('/status', methods=['GET', 'POST'])
def status():
    if request.method == 'POST':
        request_id = request.form['request_id']
        # Implement the status check logic here if necessary
        return f'Status of request {request_id}: Pending'
    return render_template('status.html')

def save_submission(general_info, items):
    # Save the submission to a local file or database if needed
    request_id = 1  # Generate or retrieve a unique request ID
    return request_id

def create_pdf(request_id, general_info, items):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'request_{request_id}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f'Request ID: {request_id}')
    c.drawString(100, 730, f'Last Name: {general_info["last_name"]}')
    c.drawString(100, 710, f'First Name: {general_info["first_name"]}')
    c.drawString(100, 690, f'Budget Number: {general_info["budget_number"]}')
    c.drawString(100, 670, f'Title: {general_info["title"]}')
    y = 650
    for item in items:
        c.drawString(100, y, f'Budget Line: {item["budget_line"]}')
        c.drawString(200, y, f'Item: {item["item_name"]}')
        c.drawString(300, y, f'CHF: {item["amount_chf"]}')
        c.drawString(400, y, f'Other Amount: {item["amount_other"]} {item["currency"]}')
        y -= 20
    c.save()

def merge_pdfs(request_id, items):
    merger = PdfMerger()
    base_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'request_{request_id}.pdf')
    merger.append(base_pdf_path)

    for item in items:
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], item['receipt'])
        merger.append(receipt_path)

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
