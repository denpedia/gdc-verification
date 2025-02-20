from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse

app = Flask(__name__)

def format_date(date_str):
    try:
        dt = date_parse(date_str)
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return date_str

def extract_dentist_details(html):
    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    header = soup.select_one('#registrant-details .card-header h2')
    if header:
        bold_tag = header.find('b')
        if bold_tag:
            second_name = bold_tag.get_text(strip=True)
            full_text = header.get_text(" ", strip=True)
            first_name = full_text.replace(second_name, "").strip()
            details["First Name"] = first_name
            details["Second Name"] = second_name
        else:
            details["First Name"] = header.get_text(strip=True)
            details["Second Name"] = "N/A"
    else:
        details["First Name"] = "N/A"
        details["Second Name"] = "N/A"

    card_body = soup.select_one('#registrant-details .card-body')
    if card_body:
        for row in card_body.find_all('div', class_='row'):
            label_div = row.find('div', class_='col-md-4')
            if not label_div:
                continue
            label = label_div.get_text(strip=True).rstrip(':')
            value_div = label_div.find_next_sibling('div')
            if value_div:
                value = " ".join(value_div.stripped_strings)
                if label == "Current period of registration from":
                    if "until:" in value:
                        parts = value.split("until:")
                        details["Register until"] = parts[1].strip()
                    else:
                        details[label] = value
                else:
                    details[label] = value

    for key in ["Registration Number", "Status", "Registrant Type", "First Registered on", "Qualifications"]:
        if key not in details:
            details[key] = "N/A"
    if "Register until" not in details:
        details["Register until"] = "N/A"

    if details.get("First Registered on") != "N/A":
        details["First Registered on"] = format_date(details["First Registered on"])
    if details.get("Register until") != "N/A":
        details["Register until"] = format_date(details["Register until"])

    return details

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    gdc_number = request.form.get('gdc_number', '').strip()
    if not gdc_number:
        return jsonify({'error': 'Please provide a GDC number'}), 400
    url = f"https://olr.gdc-uk.org/SearchRegister/SearchResult?RegistrationNumber={gdc_number}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        details = extract_dentist_details(response.text)
        return jsonify(details)
    except requests.RequestException as e:
        return jsonify({'error': f'Error retrieving data: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
