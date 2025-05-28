from flask import Flask, request, render_template, send_from_directory
import os
import pandas as pd
from datetime import datetime
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)

    # Remove timezone info
    for col in df.select_dtypes(include=['datetimetz']).columns:
        df[col] = df[col].dt.tz_localize(None)

    # Ensure datetime format
    df['Carrier first scan date'] = pd.to_datetime(df['Carrier first scan date'], errors='coerce')
    df['Promised delivery date'] = pd.to_datetime(df['Promised delivery date'], errors='coerce')

    # Find weekends
    def find_weekends(start_date, end_date):
        weekends = []
        if pd.notna(start_date) and pd.notna(end_date):
            date_range = pd.date_range(start=start_date.normalize(), end=end_date.normalize())
            for date in date_range:
                if date.weekday() in [5, 6]:
                    weekends.append((date, date.strftime('%A')))
                if len(weekends) == 2:
                    break
        while len(weekends) < 2:
            weekends.append((pd.NaT, None))
        return pd.Series([weekends[0][0], weekends[0][1], weekends[1][0], weekends[1][1]])

    df[['Weekend Date1', 'Weekend Day1', 'Weekend Date2', 'Weekend Day2']] = df.apply(
        lambda row: find_weekends(row['Carrier first scan date'], row['Promised delivery date']),
        axis=1
    )

    output_filename = f"processed_{file.filename.rsplit('.', 1)[0]}.xlsx"
    output_path = os.path.join(PROCESSED_FOLDER, output_filename)
    df.to_excel(output_path, index=False)

    return render_template('index.html', download_link=f"/download/{output_filename}")

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
