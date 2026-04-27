# Cricket Score Predictor Website

This project is a simple Flask website for:

- entering ball-wise cricket data
- calculating current run rate
- predicting the final score
- saving each entry in MongoDB
- saving each entry in a local CSV file

## Inputs

The website accepts:

- batsman name
- bowler name
- runs scored on the ball
- total team score
- completed overs
- ball in the current over
- total match overs

## Run the project

1. Install Python packages:

```bash
pip install -r requirements.txt
```

2. Start MongoDB on your machine.

3. Set environment variables if needed:

```bash
set MONGO_URI=mongodb://localhost:27017/
set MONGO_DB_NAME=cricket_score_db
set MONGO_COLLECTION_NAME=ball_by_ball
```

4. Run the website:

```bash
python app.py
```

5. Open:

```text
http://127.0.0.1:5000
```

## CSV file storage

Every submitted record is also saved locally in:

```text
data/ball_by_ball.csv
```

You can see CSV records in two ways:

- open the file directly in Excel or any spreadsheet app
- open `http://127.0.0.1:5000/csv-history` in the browser

## MongoDB collection

Saved records include:

- batsman name
- bowler name
- runs scored
- total score
- overs and ball number
- current run rate
- predicted score
- created time

## Notes

- `ball_in_over` uses `0` to `5`
- default match length is `20` overs
- prediction is based on the current run rate continuing for the remaining balls
