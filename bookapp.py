import os
import requests

from flask import Flask, session, render_template, request, flash, redirect, url_for, g, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for('welcome'))
    else:
        return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        usernamedata = db.execute("SELECT username FROM users WHERE username=:username", {"username":username}).fetchone()
        if usernamedata == None:
            if password == confirm:
                db.execute("INSERT INTO users (username, password) VALUES(:username, :password)",
                    {"username":username, "password":password})
                db.commit()
                flash("You are registered and can now login", "success")
                return redirect(url_for('login'))
            else:
                flash("Password does not match", "danger")
                return redirect(url_for('register'))
        else:
            flash("user already exists, please login or contact admin", "danger")
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        userdata = db.execute("SELECT * FROM users WHERE username=:username AND password=:password", {"username":username, "password": password}).fetchone()
        if userdata == None:
            flash ("Invalid Credentials, try again")
            return redirect(url_for('login'))
        else:
            session["user"] = username
            session["logged_in"] = True
            return redirect(url_for('welcome'))
    return render_template('login.html')

@app.route("/logout")
def logout():
    session["logged_in"] = False
    session["user"] is None
    return redirect(url_for("index"))

@app.route("/welcome", methods=["GET", "POST"])
def welcome():
    if session.get("logged_in"):
        if request.method == "POST":
            bookdata = request.form.get("book-search").lower()
            book_info = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE :isbn OR LOWER(title) LIKE :title OR LOWER(author) LIKE :author ORDER BY isbn",
            {"isbn": bookdata, "title": bookdata, "author": bookdata}).fetchall()
            return render_template('book_list.html', books = book_info)
        return render_template('welcome.html', username = session["user"])
    else:
        return render_template('logged_out.html')


@app.route("/isbn/<string:isbn>")
def reviews(isbn):
    if session.get("logged_in"):
        book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        reviews = db.execute("SELECT * FROM reviews WHERE isbn=:isbn", {"isbn": isbn}).fetchall()
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"KiCa5LTmht019IT2tHudCg", "isbns": isbn})
        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        data = res.json()
        review_count = data['books'][0]['reviews_count']
        average_rating = data['books'][0]['average_rating']
        return render_template('book_profile.html', book = book, reviews = reviews, review_count = review_count, average_rating = average_rating)


@app.route("/leave_review/<string:isbn>", methods=["GET", "POST"])
def leave_review(isbn):
    if session.get("logged_in"):
        if request.method == "POST":
            username = session["user"]
            review = request.form.get("review")
            db.execute("INSERT INTO reviews (isbn, review, username) VALUES(:isbn, :review, :username)",
                {"isbn": isbn, "review": review, "username": username})
            db.commit()
            return redirect(url_for('reviews', isbn=isbn))
        user_review = db.execute("SELECT * FROM reviews WHERE isbn=:isbn AND username=:username", {"isbn": isbn, "username": session["user"]}).fetchone()
        if user_review is None:
            book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
            return render_template('leave_review.html', book = book, username = session["user"])
        else:
            return render_template('sorry.html')

@app.route("/api/<isbn>", methods=["GET"])
def return_json(isbn):
    if session.get("logged_in"):
        api_book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        if api_book is None:
            return render_template('error.html')
        title = api_book.title
        author = api_book.author
        year = api_book.year
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"KiCa5LTmht019IT2tHudCg", "isbns": isbn})
        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        data = res.json()
        review_count = data['books'][0]['reviews_count']
        average_rating = data['books'][0]['average_rating']
        return jsonify({
                "title": title,
                "author": author,
                "year": year,
                "isbn": isbn,
                "review_count": review_count,
                "average_score": average_rating
                })
