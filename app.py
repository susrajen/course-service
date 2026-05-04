import os
import boto3
from flask import Flask, jsonify
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from flask import request
from botocore.exceptions import ClientError

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",   # for testing only
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
 
 
xray_recorder.configure(service="course-service")
XRayMiddleware(app, xray_recorder)
 
REGION = os.environ.get("AWS_REGION", "us-east-1")
 
dynamodb      = boto3.resource("dynamodb", region_name=REGION)
courses_table = dynamodb.Table("Courses")
 
 
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "course-service"}), 200
 
 
@app.route("/courses/<course_code>", methods=["GET"])
def get_course(course_code):
    resp = courses_table.get_item(Key={"code": course_code})
    item = resp.get("Item")
    if not item:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(item), 200
 
@app.route("/courses", methods=["GET"])
def list_courses_base():
    resp = courses_table.scan(Limit=50)
    return jsonify(resp.get("Items", [])), 200
 
@app.route("/sush-course/courses", methods=["GET"])
def list_courses():
    resp = courses_table.scan(Limit=50)
    return jsonify(resp.get("Items", [])), 200


@app.route("/sush-course/courses", methods=["POST"])
def add_course():
    try:
        data = request.get_json()

        # Basic validation
        if not data or "code" not in data or "name" not in data:
            return jsonify({"error": "Missing required fields: code, name"}), 400

        course_code = data["code"]

        # Prevent overwrite if course already exists
        courses_table.put_item(
            Item=data,
            ConditionExpression="attribute_not_exists(code)"
        )

        return jsonify({"message": "Course added successfully"}), 201

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return jsonify({"error": "Course already exists"}), 409
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3001, debug=False)
