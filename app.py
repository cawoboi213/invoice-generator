import os
from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import datetime
import pdfkit

app = Flask(__name__)
WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'  # Change to local path if needed
LOG_FILE = "invoice_log.txt"

def log_invoice(user, filename):
    with open(LOG_FILE, "a") as logf:
        logf.write(f"{datetime.datetime.now()}: {user} generated {filename}\n")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_invoice():
    file = request.files["file"]
    rate = float(request.form["rate"])
    user_name = request.form["user_name"]
    user_email = request.form["user_email"]
    user_phone = request.form["user_phone"]
    user_address = request.form["user_address"]

    df = pd.read_csv(file)
    mask = (
        df['Date'].notna() & df['Project Name'].notna() & df['Task/General/Issue'].notna()
    ) & (
        (df['Date'].astype(str).str.strip() != '') &
        (df['Project Name'].astype(str).str.strip() != '') &
        (df['Task/General/Issue'].astype(str).str.strip() != '')
    )
    df = df[mask]
    df['Amount_USD'] = df['Hours(For Calculation)'] * rate
    total_amount = df['Amount_USD'].sum()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    invoice_number = f"INV{timestamp}"
    invoice_date = datetime.date.today().strftime('%Y-%m-%d')
    rows_html = ""
    for _, row in df.iterrows():
        rows_html += f"""
        <tr>
          <td class="date-col">{row['Date']}</td>
          <td>{row['Project Name']}</td>
          <td>{row['Task/General/Issue']}</td>
          <td align="center">{row['Hours(For Calculation)']:.2f}</td>
          <td align="right">${rate:.2f}</td>
          <td align="right">${row['Amount_USD']:,.2f}</td>
          <td>{row['Notes']}</td>
        </tr>
        """
    html_content = f"""<!DOCTYPE html>
    <html lang="en"><head>
    <meta charset="UTF-8">
    <title>Invoice {invoice_number}</title>
    <style>
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; margin: 40px; }}
      h1 {{ color: #2a7bbd; margin-bottom: 10px; }}
      .header {{ margin-bottom: 20px; width: 100%; }}
      .header td {{ border: none; padding: 5px; vertical-align: top; }}
      .header .from {{ text-align: left; }}
      .header .to {{ text-align: right; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border: 1px solid #ccc; padding: 10px; }}
      thead th {{ background-color: #2a7bbd; color: #fff; text-align: left; }}
      tbody tr:nth-child(even) {{ background-color: #f9f9f9; }}
      tfoot td {{ border: none; padding: 8px; }}
      .total-label {{ text-align: right; font-weight: bold; }}
      .total-value {{ text-align: right; font-size: 1.1em; font-weight: bold; }}
      .subtle {{ color: #777; font-size: 0.9em; }}
      th.note-col, td.note-col {{ width: 25%; }}
      th.date-col, td.date-col {{ white-space: nowrap; }}
    </style>
    </head>
    <body>
      <h1>INVOICE</h1>
      <table class="header">
        <tr>
          <td class="from">
            <strong>From:</strong><br>
            {user_name}<br>
            {user_address}<br>
            <span class="subtle">Email: {user_email}</span><br>
            <span class="subtle">Phone: {user_phone}</span>
          </td>
          <td class="to">
            <strong>To:</strong><br>
            Virtual Gal Friday, LLC<br>
            13423 Blanco Rd, Unit #3197 San Antonio, TX 78216<br>
            <span class="subtle">Email: invoices@virtualgalfriday.com</span>
          </td>
        </tr>
        <tr>
          <td><strong>Invoice #:</strong> {invoice_number}</td>
          <td class="to"><strong>Date:</strong> {invoice_date}</td>
        </tr>
      </table>
      <table>
        <thead>
          <tr>
            <th class="date-col">Date</th>
            <th>Client/Project Name</th>
            <th>Task Description</th>
            <th>Hours</th>
            <th>Rate (USD)</th>
            <th>Amount (USD)</th>
            <th class="note-col">Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="6" class="total-label">Total:</td>
            <td class="total-value">${total_amount:,.2f}</td>
          </tr>
        </tfoot>
      </table>
    </body>
    </html>
    """
    html_file = f"{invoice_number}.html"
    pdf_file = f"{invoice_number}.pdf"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    pdfkit.from_file(html_file, pdf_file, configuration=config)
    log_invoice(user_name, file.filename)
    return send_file(pdf_file, as_attachment=True)

@app.route("/log", methods=["GET"])
def get_log():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE) as f:
        lines = f.readlines()
    return jsonify(lines)

@app.route("/clear_log", methods=["POST"])
def clear_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
