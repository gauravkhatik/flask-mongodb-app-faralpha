from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

# Initialize the Flask application
app = Flask(__name__)

# Connect to MongoDB
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb://localhost:27017/"
)

client = MongoClient(MONGODB_URI)

# Connect to the database and collection
db = client.flask_db
collection = db.data


# Root endpoint
@app.route('/')
def index():
    return f"Welcome to the Flask app! The current time is: {datetime.now()}"


# Data endpoint: supports GET and POST
@app.route('/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        # Get JSON data from the request
        data = request.get_json()

        if data is None:
            return jsonify({"error": "Valid JSON data is required"}), 400

        # Insert data into MongoDB
        collection.insert_one(data)

        return jsonify({"status": "Data inserted"}), 201

    elif request.method == 'GET':
        # Retrieve all documents, excluding MongoDB's _id field
        data = list(collection.find({}, {"_id": 0}))

        return jsonify(data), 200


# Run the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)