import os
from flask import Flask, request, redirect, url_for
from flask import render_template

ALLOWED_EXTENSIONS = set(["csv"])

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static"


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/upload_file", methods=["GET", "POST"])
def upload_file():
    pass


@app.route("/diplay_table_data", methods=["GET", "POST"])
def diplay_table_data():
    pass


@app.route("/display_table_meta", methods=["GET", "POST"])
def display_table_meta():
    pass


@app.route("/change_data_header", methods=["GET", "POST"])
def change_data_header(id, type):
    pass


if __name__ == "__main__":
    app.run(debug=True)
