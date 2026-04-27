from datetime import datetime
import csv
import os

from flask import Flask, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError


app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "cricket_score_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "ball_by_ball")
DEFAULT_MATCH_OVERS = 20
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_FILE_PATH = os.path.join(DATA_DIR, "ball_by_ball.csv")
CSV_HEADERS = [
    "batsman_name",
    "bowler_name",
    "runs_scored",
    "total_score",
    "completed_overs",
    "ball_in_over",
    "balls_bowled",
    "match_overs",
    "current_run_rate",
    "predicted_score",
    "created_at",
]


def get_collection():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]


def ensure_csv_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()


def save_entry_to_csv(entry: dict):
    ensure_csv_storage()
    csv_entry = {
        key: entry.get(key, "")
        for key in CSV_HEADERS
    }
    csv_entry["created_at"] = (
        entry["created_at"].isoformat()
        if isinstance(entry.get("created_at"), datetime)
        else entry.get("created_at", "")
    )
    with open(CSV_FILE_PATH, "a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writerow(csv_entry)


def load_csv_entries():
    ensure_csv_storage()
    with open(CSV_FILE_PATH, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def build_score_graph_data(entries):
    labels = []
    scores = []

    for index, entry in enumerate(entries, start=1):
        over_value = f"{entry.get('completed_overs', '0')}.{entry.get('ball_in_over', '0')}"
        labels.append(f"Ball {index} ({over_value})")
        try:
            scores.append(int(float(entry.get("total_score", 0))))
        except (TypeError, ValueError):
            scores.append(0)

    return {"labels": labels, "scores": scores}


def balls_bowled_from_input(completed_overs: int, ball_in_over: int) -> int:
    return (completed_overs * 6) + ball_in_over


def calculate_run_rate(total_score: int, balls_bowled: int) -> float:
    if balls_bowled <= 0:
        return 0.0
    return round((total_score * 6) / balls_bowled, 2)


def predict_score(total_score: int, run_rate: float, target_overs: int, balls_bowled: int) -> int:
    total_balls = target_overs * 6
    remaining_balls = max(total_balls - balls_bowled, 0)
    predicted_total = total_score + ((run_rate / 6) * remaining_balls)
    return round(predicted_total)


def recent_entries(limit: int = 15):
    try:
        return list(get_collection().find().sort("created_at", -1).limit(limit))
    except PyMongoError:
        return []


@app.route("/", methods=["GET", "POST"])
def index():
    errors = []
    result = None
    db_warning = None
    form_data = {
        "batsman_name": "",
        "bowler_name": "",
        "runs_scored": "",
        "total_score": "",
        "completed_overs": "",
        "ball_in_over": "",
        "match_overs": str(DEFAULT_MATCH_OVERS),
    }

    if request.method == "POST":
        form_data.update(
            {
                "batsman_name": request.form.get("batsman_name", "").strip(),
                "bowler_name": request.form.get("bowler_name", "").strip(),
                "runs_scored": request.form.get("runs_scored", "").strip(),
                "total_score": request.form.get("total_score", "").strip(),
                "completed_overs": request.form.get("completed_overs", "").strip(),
                "ball_in_over": request.form.get("ball_in_over", "").strip(),
                "match_overs": request.form.get("match_overs", "").strip(),
            }
        )

        try:
            runs_scored = int(form_data["runs_scored"])
            total_score = int(form_data["total_score"])
            completed_overs = int(form_data["completed_overs"])
            ball_in_over = int(form_data["ball_in_over"])
            match_overs = int(form_data["match_overs"])
        except ValueError:
            errors.append("Please enter numbers for score, overs, and ball count.")
        else:
            if not form_data["batsman_name"]:
                errors.append("Batsman name is required.")
            if not form_data["bowler_name"]:
                errors.append("Bowler name is required.")
            if runs_scored < 0:
                errors.append("Runs scored cannot be negative.")
            if total_score < 0:
                errors.append("Total score cannot be negative.")
            if completed_overs < 0:
                errors.append("Completed overs cannot be negative.")
            if ball_in_over < 0 or ball_in_over > 5:
                errors.append("Ball in over must be between 0 and 5.")
            if match_overs <= 0:
                errors.append("Match overs must be greater than 0.")

            if not errors:
                balls_bowled = balls_bowled_from_input(completed_overs, ball_in_over)
                run_rate = calculate_run_rate(total_score, balls_bowled)
                predicted_total = predict_score(total_score, run_rate, match_overs, balls_bowled)

                entry = {
                    "batsman_name": form_data["batsman_name"],
                    "bowler_name": form_data["bowler_name"],
                    "runs_scored": runs_scored,
                    "total_score": total_score,
                    "completed_overs": completed_overs,
                    "ball_in_over": ball_in_over,
                    "balls_bowled": balls_bowled,
                    "match_overs": match_overs,
                    "current_run_rate": run_rate,
                    "predicted_score": predicted_total,
                    "created_at": datetime.utcnow(),
                }

                save_entry_to_csv(entry)

                try:
                    get_collection().insert_one(entry)
                except PyMongoError:
                    db_warning = "Prediction worked, but MongoDB is not connected so the data could not be saved."

                result = {
                    "balls_bowled": balls_bowled,
                    "run_rate": run_rate,
                    "predicted_score": predicted_total,
                }

    csv_entries = load_csv_entries()
    graph_data = build_score_graph_data(csv_entries)

    return render_template(
        "index.html",
        errors=errors,
        result=result,
        db_warning=db_warning,
        form_data=form_data,
        entries=recent_entries(),
        graph_data=graph_data,
    )


@app.route("/history")
def history():
    db_warning = None
    try:
        entries = list(get_collection().find().sort("created_at", -1))
    except PyMongoError:
        entries = []
        db_warning = "MongoDB is not connected. Start MongoDB to load saved history."
    return render_template("history.html", entries=entries, db_warning=db_warning)


@app.route("/csv-history")
def csv_history():
    entries = list(reversed(load_csv_entries()))
    graph_data = build_score_graph_data(list(reversed(entries)))
    return render_template(
        "csv_history.html",
        entries=entries,
        csv_file_path=CSV_FILE_PATH,
        graph_data=graph_data,
    )


@app.route("/seed-sample")
def seed_sample():
    sample_entry = {
        "batsman_name": "Virat Kohli",
        "bowler_name": "Jasprit Bumrah",
        "runs_scored": 2,
        "total_score": 78,
        "completed_overs": 10,
        "ball_in_over": 3,
        "balls_bowled": 63,
        "match_overs": DEFAULT_MATCH_OVERS,
        "current_run_rate": calculate_run_rate(78, 63),
        "predicted_score": predict_score(78, calculate_run_rate(78, 63), DEFAULT_MATCH_OVERS, 63),
        "created_at": datetime.utcnow(),
    }
    save_entry_to_csv(sample_entry)
    try:
        get_collection().insert_one(sample_entry)
    except PyMongoError:
        return redirect(url_for("index"))
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
