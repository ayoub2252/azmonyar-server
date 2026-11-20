import os, json, secrets, string, time
from flask import Flask, request, jsonify
from flask_cors import CORS

DATA_DIR = os.environ.get("DATA_DIR", ".")
if not os.path.isdir(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

EXAMS_FILE = os.path.join(DATA_DIR, "exams.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def generate_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if any(c in "IO01" for c in code):
            continue
        return code

app = Flask(__name__)
CORS(app)

TEACHER_KEY = os.environ.get("TEACHER_KEY", "default-teacher-key")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"ok": True, "app": "azmonyar-server", "time": int(time.time())})

@app.route("/api/exams", methods=["POST"])
def create_exam():
    data = request.get_json(force=True)
    exams = load_json(EXAMS_FILE, {})
    code = generate_code()
    while code in exams:
        code = generate_code()
    exams[code] = {
        "data": data,
        "created_at": int(time.time())
    }
    save_json(EXAMS_FILE, exams)
    return jsonify({"ok": True, "code": code})

@app.route("/api/exams/<code>", methods=["GET"])
def get_exam(code):
    exams = load_json(EXAMS_FILE, {})
    exam = exams.get(code)
    if not exam:
        return jsonify({"ok": False, "error": "exam not found"}), 404
    return jsonify({"ok": True, "exam": exam["data"], "code": code})

@app.route("/api/results/<code>", methods=["POST"])
def submit_result(code):
    exams = load_json(EXAMS_FILE, {})
    if code not in exams:
        return jsonify({"ok": False, "error": "exam not found"}), 404
    data = request.get_json(force=True)
    student_id = data.get("studentId") or data.get("student_id")
    results = load_json(RESULTS_FILE, {})
    if code not in results:
        results[code] = []
    for r in results[code]:
        if r.get("studentId") == student_id:
            return jsonify({"ok": False, "error": "duplicate submission"}), 409
    data["received_at"] = int(time.time())
    results[code].append(data)
    save_json(RESULTS_FILE, results)
    return jsonify({"ok": True, "received": True})

@app.route("/api/results/<code>", methods=["GET"])
def get_results(code):
    key = request.args.get("key", "")
    if key != TEACHER_KEY:
        return jsonify({"ok": False, "error": "invalid key"}), 403
    results = load_json(RESULTS_FILE, {}).get(code, [])
    return jsonify({"ok": True, "results": results})

@app.route("/api/results/<code>", methods=["DELETE"])
def delete_results(code):
    key = request.args.get("key", "")
    if key != TEACHER_KEY:
        return jsonify({"ok": False, "error": "invalid key"}), 403
    results = load_json(RESULTS_FILE, {})
    results.pop(code, None)
    save_json(RESULTS_FILE, results)
    return jsonify({"ok": True, "deleted": True})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
