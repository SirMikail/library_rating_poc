from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from rapidfuzz import fuzz, process

import pandas as pd
import datetime


app = Flask(__name__)
app.secret_key = 'secret'  # Use a secure, random secret key for your application


databases = {
    'users_db': 'sqlite:///users.db',
    'user_ratings_db': 'sqlite:///user_ratings.db'
}

# Configure Flask app to use multiple databases
app.config['SQLALCHEMY_DATABASE_URI'] = databases['users_db']  # Default DB URI
app.config['SQLALCHEMY_BINDS'] = {
    'user_ratings_db': databases['user_ratings_db']
}

# Create a single SQLAlchemy instance for managing all databases
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# Define a User model
class User(db.Model):
    __bind_key__ = None  # Defaults to 'users_db'
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class UserRating(db.Model):
    __bind_key__ = 'user_ratings_db'  # Bind to 'user_ratings_db' database
    __tablename__ = 'user_ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150), nullable=False)
    book_id = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    rating_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow())


# Create the database and tables
with app.app_context():
    db.create_all()
    df = pd.read_excel("book_list.xlsx")


# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')


# Route for the signup form
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create a new user and save to the database
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')


# Route for the login form
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        
        # Find the user in the database
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            # If the user is found and the password matches, log them in
            session['user_id'] = user.id
            flash('You are now logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


# Route for logging out
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/search_book', methods=['GET', 'POST'])
def search_book():
    search_results = []
    if request.method == 'POST':
        title = request.form.get('q')
        similarity_threshold = 50

        # Find book titles in the DataFrame that are similar to the provided title
        # Using `process.extract` from `rapidfuzz` to find similar titles
        choices = [str(x) for x in df["Title"].tolist()]
        similar_titles = process.extract(title, choices, scorer=fuzz.WRatio, limit=10)

        # Filter results based on the similarity threshold
        similar_books = [book for book in similar_titles if book[1] >= similarity_threshold]
        print(similar_books)

        # Get the indices of similar titles
        similar_indices = [df[df['Title'] == book[0]].index[0] for book in similar_books]

        # Get the rows of similar books
        similar_books_df = df.iloc[similar_indices]

        # Convert the result to a dictionary and return as JSON
        similar_books_info = similar_books_df.to_dict(orient='records')

        # filter by accession no.
        unique_books = []
        final_books = []
        for x in similar_books_info:
            if x["Accession No."] not in unique_books:
                unique_books.append(x["Accession No."])
                final_books.append(x)
        search_results = final_books
    return render_template('search.html', search_results=search_results)


@app.route('/rate_book', methods=['POST'])
def rate_book():
    book_id = request.form.get('book_id')
    if not book_id:
        raise Exception("Enter a valid book id")
    rating = request.form.get('rating')
    if not rating and int(rating) not in [1, 2, 3, 4, 5]:
        raise Exception("Enter a valid rating from 1 - 5")
    user_id = session.get('user_id')
    if not user_id:
        raise Exception("Need to be logged in to perform this action")
    
    new_rating = UserRating(user_id=user_id, book_id=book_id, rating=int(rating), rating_date=datetime.datetime.utcnow())
    db.session.add(new_rating)
    db.session.commit()
    return jsonify({"message": f"Succesfully added rating for book {book_id} and user {user_id}"})


@app.route('/get_my_ratings', methods=['POST'])
def get_my_ratings():
    ratings_data = []
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            raise Exception("Need to be logged in to perform this action")
        
        user_ratings = UserRating.query.filter_by(user_id=user_id).all()
        
        # Prepare a list to hold the data
        
        for rating in user_ratings:
            row = df[df['Accession No.'] == rating.book_id]
            data = {
                "book_id": rating.book_id,
                "title": row['Title'].values.tolist()[0],
                "author": row['Author'].values.tolist()[0],
                "year": row['Year'].values.tolist()[0],
                "rating": rating.rating,
                "rating_date": rating.rating_date.isoformat()
            }
            ratings_data.append(data)
    return render_template('ratings.html', ratings=ratings_data)


if __name__ == '__main__':
    app.run(debug=True)
