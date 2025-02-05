import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
import pandas as pd
import numpy as np
import random
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import defaultdict

load_dotenv()
app = Flask(__name__)
CORS(app)

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        text = extract_text_from_pdf(file)
        response_data = process_bank_statement(text)
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def parse_text_with_openai(text):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    prompt = f"""
    Extract the following fields from the bank statement text below:
    - Date
    - Description
    - Amount
    - Transaction Type (Deposit/Withdrawal)

    Return the results in a valid JSON array format with the following structure.
    Remove any markdowns:
    [
        {{
            "Date": "DD MMM YYYY",
            "Description": "Transaction description",
            "Amount": 123.45,
            "Transaction Type": "Deposit/Withdrawal"
        }},
        ...
    ]

    Text: {text}
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {
            "role": "user",
            "content": prompt
            }
        ]
    )

    return completion.choices[0].message.content

def normalize_description(desc):
    # Remove transaction type indicators (DEB, CPT, TFR, DD)
    cleaned_desc = re.sub(r'\b(DEB|CPT|TFR|DD)\b', '', desc, flags=re.IGNORECASE)
    
    # Remove numbers and special characters
    cleaned_desc = re.sub(r'[^A-Za-z ]', '', cleaned_desc)
    
    # Extract transaction description
    tokens = cleaned_desc.strip().split()
    return tokens[0].lower() if tokens else ""

def detect_recurring_expenses(transactions):
    expense_count = defaultdict(int)
    
    # Only consider withdrawals (expenses)
    for t in transactions:
        if t["Transaction Type"] == "Withdrawal":
            normalized_desc = normalize_description(t["Description"])
            if normalized_desc:
                expense_count[normalized_desc] += 1
    
    # Filter to get recurring expenses (> 1)
    return {desc: count for desc, count in expense_count.items() if count > 1}

def process_bank_statement(text):

    # Training data
    categories = {
        "Salary": [
            "Salary Payment", "Direct Bank Deposit", "Paycheck Deposit", "Monthly Salary Credit",
            "Bonus Deposit", "Employer Salary Transfer", "JANALAKSHMI FINA", "Bi-weekly"
        ],
        "Rent": [
            "Apartment Rent", "Office Rent", "Warehouse Rent", "Housing Lease",
            "Rent Payment for Property", "Monthly Rental Fee", "TP ACH Bajaj Finanac",
            "ACH" 
        ],
        "Utilities": [
            "Electricity", "Water", "Gas", "Internet",
            "Cable Subscription", "Phone", "LNK COOPERATIVE SW",
            "LV LIFE 03592291015W DD", "LNK PO MITCHAM LAN", "VODAFONE LTD",
            "LNK WEST NORWOOD", "TATASKY DTH", "Tata Power", "VIDEOCON DTH",
            "AIRTEL PREPA", "IDEA PREPAID", "Reliance Ene", "PHONEPE RECHARGE"
        ],
        "Loan Payment": [
            "Car Loan", "Student Loan Installment", "Mortgage Repayment", "Personal Loan EMI",
            "Loan Repayment", "Credit Card", "FINNOVATION TECH"
        ],
        "Food & Dining": [
            "McDonalds Restaurant", "Starbucks Coffee", "Local Cafe Expense", "Restaurant Bill",
            "Takeout Order", "Food Delivery Service", "WINELEAF", "MIS BAR MLECZNY CD",
            "KINGS TUN", "BEDFORD TAVERN", "DELIGHT", "Upper Crust Foods", "SHREENATHJI CAKE",
            "PRAKASH LUNCH", "Food", "Dining", "Wine", "Alcohol"
        ],
        "Shopping": [
            "Nike Store Purchase", "Amazon Purchase", "Supermarket Grocery Shopping", "Clothing Store",
            "Electronics Store Expense", "Retail Outlet Purchase", "BARCLAYCARD", "WESTERN VILLA",
            "SPORTSDIRECT 252", "TESCO STORES", "NIKE FACTORY STORE", "Amazon UK Marketpl", "THE BOMBAY SEEDS SUPPL",
            "Under Armour", "H&M", "Petco", "Kroger", "Target"
        ],
        "Entertainment": [
            "Netflix Subscription", "Spotify Premium Payment", "Movie Ticket Booking", "Concert Ticket",
            "Game Store", "Online Streaming Service", "LOYD ROYDON CENTR", "OPERA HOUSE", "Hulu",
            "Cable", "HBO Max", "Cinemark", "AMC Theatres", "Galaxy Theatres", "Broadway"
        ],
        "Transportation": [
            "Uber Ride", "Train Ticket Booking", "Gas Station Fuel", "Bus Pass",
            "Flight Ticket", "Toll Road", "FLIPKART PAYMENTS", "Lyft", "Metro",
            "Train", "Amtrak", "American Airlines", "Spirit Airlines", "Alaska Airlines"
        ],
        "Cash Deposit": [
            "Cash Deposit at ATM", "Bank Teller Deposit", "Mobile Banking Cash Deposit", "Check Deposit",
            "Wire Transfer Received", "Direct Cash Addition", "LOYD STREATHAM HIG CSH", "Fund Trf", "APB-INW",
            "CREDIT INTEREST", "QUATERLY SAVINGS INTEREST", "Rajesh basavraj goda", "EKO INDIA FINANCIAL SERVICES PR"
        ],
        "Other": [
            "Miscellaneous Transfer", "Charity Donation", "Freelance Work Payment", "Investment Dividend Credit",
            "Gift Card Redemption", "Bank Fee Deduction", "P ADAMCZUK KASA 7420", "D ROBERTSON DEB", "KATE EYR G D LTD KEGD FPI",
            "SUPER CHOICE", "KARUN MEDICAL", "CASH WITHDRAWAL", "HOTEL SAROJ", "Cash Wdl", "MANSI MEDICAL", "POS-VISA",
            "MOBIKWK", "KURLA NAGARIK SAHAKARI BAN", "Pest Control", "MANSI MEDICARE"
        ]
    }

    # Generate a balanced dataset
    num_samples_per_category = 100
    data = {
        "Description": [
            random.choice(categories[cat]) + f" {random.randint(1, 999)}"
            for cat in categories for _ in range(num_samples_per_category)
        ],
        "Category": [cat for cat in categories for _ in range(num_samples_per_category)]
    }
    df = pd.DataFrame(data)

    # Vectorize text data using TF-IDF
    vectorizer = TfidfVectorizer(ngram_range=(1,3), stop_words="english", max_features=1000)
    X = vectorizer.fit_transform(df["Description"])
    y = df["Category"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    # Train Random Forest model
    random_forest_model = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=42, class_weight="balanced")
    random_forest_model.fit(X_train, y_train)

    # Evaluate the model
    # y_pred = rf_model.predict(X_test)
    # print("Model Evaluation:\n", classification_report(y_test, y_pred))

    # Retrieve response from LLM
    parsed_data = parse_text_with_openai(text)

    # Remove markdown code blocks if present
    parsed_data = re.sub(r"```json|```", "", parsed_data.strip())

    # Parse the JSON 
    if isinstance(parsed_data, str):
        transactions = json.loads(parsed_data)
    else:
        transactions = parsed_data

    # Extract descriptions
    new_descriptions = [t["Description"] for t in transactions]

    # Vectorize new descriptions
    X_new = vectorizer.transform(new_descriptions)

    # Predict categories
    predicted_categories = random_forest_model.predict(X_new)

    # Add predictions to the transactions
    for i, t in enumerate(transactions):
        t["Predicted Category"] = predicted_categories[i]

    # Normalize dates for financial insights computations
    df = pd.DataFrame(transactions)

    df['Date'] = pd.to_datetime(df['Date'], format = '%d %b %Y')
    df['Year-Month'] = df['Date'].dt.to_period('M')

    deposits = df[df['Transaction Type'] == 'Deposit']
    withdrawals = df[df['Transaction Type'] == 'Withdrawal']

    monthly_deposits = deposits.groupby('Year-Month')['Amount'].sum().to_dict()
    monthly_withdrawals = withdrawals.groupby('Year-Month')['Amount'].sum().to_dict()
    monthly_net_cash_flow = {}

    # Calculate insights
    for month in set(list(monthly_deposits.keys()) + list(monthly_withdrawals.keys())):
        deposits_val = monthly_deposits.get(month, 0)
        withdrawals_vals = monthly_withdrawals.get(month, 0)
        monthly_net_cash_flow[str(month)] = deposits_val - withdrawals_vals
    
    # Compute recurring expenses
    recurring_expenses = detect_recurring_expenses(transactions)

    return {
        "transactions": transactions,
        "monthly_deposits": {str(k): v for k, v in monthly_deposits.items()},
        "monthly_withdrawals": {str(k): v for k, v in monthly_withdrawals.items()},
        "monthly_net_cash_flow": monthly_net_cash_flow,
        "recurring_expenses": recurring_expenses
    }

if __name__ == "__main__":
    app.run(debug=True)