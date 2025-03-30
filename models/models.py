from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(UTC))


class Subjects(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quizzes = db.relationship('Quizzes', backref='subject', lazy=True)


class Quizzes(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey(
        'subjects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    no_of_questions = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    validity = db.Column(db.DateTime, nullable=False)
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    questions = db.relationship('Questions', backref='quiz', lazy=True)


class Questions(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey(
        'quizzes.id'), nullable=False)
    question_title = db.Column(db.String(200), nullable=False)
    question_statement = db.Column(db.String(500), nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)


class Scores(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey(
        'quizzes.id'), nullable=False)
    score_percentage = db.Column(db.Integer, nullable=False)

    # We take a quiz, all question are sorted by id and then we take the correct answers and attempted answers stored as 32412 (for 3, 2, 4, 1, 2) as a string
    # code is found in spammed ################ and ################ between those in submit_quiz route, update later if needed
    attempted_answers = db.Column(db.String, nullable=False)
    correct_answers = db.Column(db.String, nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    end_time = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', backref=db.backref('scores', lazy=True))
    quiz = db.relationship('Quizzes', backref=db.backref('scores', lazy=True))
