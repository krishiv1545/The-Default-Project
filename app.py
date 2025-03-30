from flask import Flask, render_template, request, redirect, url_for, session, flash
from models.models import db, User, Subjects, Quizzes, Questions, Scores
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os
import json
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['name']
        qualification = request.form['qualification']
        dob = datetime.strptime(request.form['dob'], '%Y-%m-%d')
        hashed_password = generate_password_hash(password)

        try:
            new_user = User(email=email, username=username,
                            password=hashed_password, full_name=full_name, qualification=qualification, dob=dob)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Username or email already exists.', 'error')
            # print(e)
    return render_template('signup.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    if session['role'] == 'superadmin' or session['role'] == 'admin':
        flash('Sign in as a user.', 'error')
        return redirect(url_for('admin_dashboard'))
    user = User.query.get(session['user_id'])

    search = None
    if request.method == 'POST':
        search = request.form['search']
        filterBy = request.form['filterBy']

    if search:
        if filterBy == "sub":
            search = search.lower()
            valid_datetime_quizzes = Quizzes.query.filter(
                Quizzes.validity > datetime.now()).all()
            ls = []  # [ (valid quiz object, subject name string) ]
            for valid_datetime_quiz in valid_datetime_quizzes:
                subject_name = valid_datetime_quiz.subject.name.lower()
                if search in subject_name:
                    ls.append(
                        (valid_datetime_quiz, valid_datetime_quiz.subject.name))
            valid_quizzes = ls
        elif filterBy == "quiz":
            search = search.lower()
            valid_datetime_quizzes = Quizzes.query.filter(
                Quizzes.validity > datetime.now()).all()
            ls = []  # [ (valid quiz object, subject name string) ]
            for valid_datetime_quiz in valid_datetime_quizzes:
                quiz_name = valid_datetime_quiz.name.lower()
                if search in quiz_name:
                    ls.append(
                        (valid_datetime_quiz, valid_datetime_quiz.subject.name))
            valid_quizzes = ls
    else:
        valid_quizzes = (
            db.session.query(Quizzes, Subjects.name)
            .join(Subjects, Quizzes.subject_id == Subjects.id)
            .filter(Quizzes.validity > datetime.now())
            .all()
        )
    # print(valid_quizzes)
    return render_template('dashboard.html', full_name=user.full_name, valid_quizzes=valid_quizzes, user_id=user.id)


@app.route('/scores', methods=['GET', 'POST'])
def scores():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    search = None
    if request.method == 'POST':
        search = request.form['search']
        filterBy = request.form['filterBy']

    user_scores = Scores.query.filter_by(user_id=session['user_id']).all()

    if search:
        filtered_scores = []
        search = search.lower()

        if filterBy == "sub":
            for score in user_scores:
                subject_name = score.quiz.subject.name.lower()
                if search in subject_name:
                    filtered_scores.append(score)

        elif filterBy == "quiz":
            for score in user_scores:
                quiz_name = score.quiz.name.lower()
                if search in quiz_name:
                    filtered_scores.append(score)

        elif filterBy == "score":
            for score in user_scores:
                if int(search) == int(score.score_percentage):
                    filtered_scores.append(score)

        user_scores = filtered_scores

    return render_template('scores.html', scores=user_scores)


@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():

    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('home'))
    user = User.query.get(session['user_id'])
    if user.role == 'user':
        flash('Sign in as an admin.', 'error')
        return redirect(url_for('home'))

    # new attempt for lower case and the full name search only error
    sub_search = None
    if request.method == 'POST':
        sub_search = request.form['sub_search']
    if sub_search:
        subjects = []
        all_subjects = Subjects.query.all()
        for subject in all_subjects:
            sub_search = sub_search.lower()
            subject_name = subject.name.lower()
            if sub_search in subject_name:
                subjects.append(subject)
    else:
        subjects = Subjects.query.all()
    # I am a genius, google should hire me

    quizzes = Quizzes.query.all()
    return render_template('admin_dashboard.html', subjects=subjects, quizzes=quizzes)


@app.route('/add_subject', methods=['POST'])
def add_subject():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        new_subject = Subjects(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()

        return redirect(url_for('admin_dashboard'))


@app.route('/add_quiz', methods=['GET', 'POST'])
def add_quiz():

    if request.method == 'POST':
        new_quiz = Quizzes(
            subject_id=request.form['subject_id'],
            name=request.form['name'],
            no_of_questions=request.form['no_of_questions'],
            duration=request.form['duration'],
            validity=datetime.strptime(
                request.form['validity'], '%Y-%m-%dT%H:%M')
        )
        db.session.add(new_quiz)
        db.session.commit()
        return redirect(url_for('quizzes'))


@app.route('/edit-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quizzes.query.get(quiz_id)

    if request.method == 'POST':
        quiz.subject_id = request.form['subject_id']
        quiz.name = request.form['name']
        quiz.no_of_questions = request.form['no_of_questions']
        quiz.duration = request.form['duration']
        quiz.validity = datetime.strptime(
            request.form['validity'], '%Y-%m-%dT%H:%M')
        db.session.commit()
        return redirect(url_for('admin_dashboard'))


@app.route('/edit-subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    sub = Subjects.query.get(subject_id)

    if request.method == 'POST':
        sub.name = request.form['name']
        sub.description = request.form['description']
        db.session.commit()
        return redirect(url_for('admin_dashboard'))


@app.route('/delete-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def delete_quiz(quiz_id):
    quiz = Quizzes.query.get(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/delete-subject/<int:subject_id>', methods=['GET', 'POST'])
def delete_subject(subject_id):
    subject = Subjects.query.get(subject_id)
    quizzes = Quizzes.query.filter_by(subject_id=subject_id).all()

    for quiz in quizzes:
        Questions.query.filter_by(quiz_id=quiz.id).delete()

    Quizzes.query.filter_by(subject_id=subject_id).delete()

    db.session.delete(subject)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))


@app.route('/add_question/<int:quiz_id>', methods=['POST'])
def add_question(quiz_id):
    if request.method == 'POST':
        new_question = Questions(
            quiz_id=quiz_id,
            question_title=request.form['question_title'],
            question_statement=request.form['question_statement'],
            option1=request.form['option1'],
            option2=request.form['option2'],
            option3=request.form['option3'],
            option4=request.form['option4'],
            correct_option=int(request.form['correct_option'])
        )
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for('quizzes', quiz_id=quiz_id))


@app.route('/edit-question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Questions.query.get(question_id)
    question.question_title = request.form['question_title']
    question.question_statement = request.form['question_statement']
    question.option1 = request.form['option1']
    question.option2 = request.form['option2']
    question.option3 = request.form['option3']
    question.option4 = request.form['option4']
    question.correct_option = int(request.form['correct_option'])
    db.session.commit()
    return redirect(url_for('quizzes'))


@app.route('/quiz/<int:quiz_id>/<int:user_id>', methods=['GET', 'POST'])
def start_quiz(quiz_id, user_id):
    quiz = Quizzes.query.get(quiz_id)
    quiz_questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    start_time = datetime.now()

    correct_answers_dict = {}
    for question in quiz_questions:
        correct_answers_dict[question.id] = question.correct_option
    # Initialize session dict if not present
    if 'attempted_answers_dict' not in session:
        session['attempted_answers_dict'] = {}

    # Convert stored keys to integers
    attempted_answers_dict = {
        int(k): v for k, v in session['attempted_answers_dict'].items()}

    if request.method == 'POST':
        # Determine what triggered the submit:
        action = request.form.get('action')
        if action == 'select_answer':
            # When an answer is selected:
            selected_option = request.form.get('selectedoption')
            active_question_id = request.form.get('activequestion')
            if active_question_id and selected_option:
                active_question_id = int(active_question_id)
                attempted_answers_dict[active_question_id] = int(
                    selected_option)
                current_question_id = active_question_id
            else:
                # Fallback if for some reason these values are missing
                current_question_id = quiz_questions[0].id

        elif action == 'change_question':
            # When a question is selected from the left panel:
            left_panel_question = request.form.get('selectedquestion')
            if left_panel_question:
                current_question_id = int(left_panel_question)
            else:
                current_question_id = quiz_questions[0].id
        else:
            # Fallback if no action is provided
            current_question_id = quiz_questions[0].id

        # Save the updated answers back into session (with string keys)
        session['attempted_answers_dict'] = {
            str(k): v for k, v in attempted_answers_dict.items()}

        # Find the question to display:
        selected_question = next(
            (q for q in quiz_questions if q.id == current_question_id),
            quiz_questions[0]
        )
    else:
        selected_question = quiz_questions[0]
    # print(session['attempted_answers_dict'])
    attempted_answers_dict_str = json.dumps(session['attempted_answers_dict'])
    correct_answers_dict_str = json.dumps(correct_answers_dict)
    # print("attempted answers dict str is", attempted_answers_dict_str)
    # print("correct answers dict str is", correct_answers_dict_str)
    return render_template(
        'quiz.html',
        quiz=quiz,
        quiz_questions=quiz_questions,
        selected_question=selected_question,
        attempted_answers_dict=attempted_answers_dict,
        attempted_answers_dict_str=attempted_answers_dict_str,
        user_id=user_id,
        correct_answers_dict=correct_answers_dict,
        correct_answers_dict_str=correct_answers_dict_str,
        start_time=start_time
    )


@app.route('/submit-quiz', methods=['GET', 'POST'])
def submit_quiz():
    print("in submit quiz")
    user_id = request.args.get('user_id', type=int)
    quiz_id = request.args.get('quiz_id', type=int)
    attempted_answers_dict_str = request.args.get(
        'attempted_answers_dict_str', type=str)
    correct_answers_dict_str = request.args.get(
        'correct_answers_dict_str', type=str)
    start_time_str = request.args.get('start_time')
    start_time = datetime.fromisoformat(start_time_str)

    attempted_answers_dict = json.loads(attempted_answers_dict_str)
    correct_answers_dict = json.loads(correct_answers_dict_str)

    your_score = 0
    for key in correct_answers_dict:
        if key in attempted_answers_dict:
            if attempted_answers_dict[key] == correct_answers_dict[key]:
                your_score += 1
    total_marks = len(correct_answers_dict)
    score_percentage = (your_score / total_marks) * 100

    end_time = datetime.now()
#################
    store_attempts = ""
    store_correct = ""
    attempted_answers_dict = {
        int(k): v for k, v in attempted_answers_dict.items()}
    attempted_answers_dict = dict(sorted(attempted_answers_dict.items()))
    for key in attempted_answers_dict:
        store_attempts += str(attempted_answers_dict[key])

    correct_answers_dict = {int(k): v for k, v in correct_answers_dict.items()}
    correct_answers_dict = dict(sorted(correct_answers_dict.items()))
    for key in correct_answers_dict:
        store_correct += str(correct_answers_dict[key])
################
    existing_score = Scores.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id
    ).first()

    if existing_score:
        # Update existing entry
        existing_score.score_percentage = score_percentage
        existing_score.attempted_answers = store_attempts
        existing_score.correct_answers = store_correct
        existing_score.start_time = start_time
        existing_score.end_time = end_time
    else:
        new_score = Scores(user_id=user_id, quiz_id=quiz_id, score_percentage=score_percentage,
                           attempted_answers=store_attempts, correct_answers=store_correct, start_time=start_time, end_time=end_time)
        db.session.add(new_score)

    db.session.commit()
    session.pop('attempted_answers_dict', None)

    return redirect(url_for('scores'))


@app.route('/delete-question/<int:question_id>', methods=['GET', 'POST'])
def delete_question(question_id):
    question = Questions.query.get(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('quizzes'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        user = User.query.filter((User.username == username_or_email) | (
            User.email == username_or_email)).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            # session['attempted_answers_dict'] = {}
            if user.role == 'superadmin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/quizzes', methods=['GET', 'POST'])
def quizzes():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    quiz_search = None
    if request.method == 'POST':
        quiz_search = request.form['quiz_search']
    if quiz_search:
        quizzes = []
        all_quizzes = Quizzes.query.all()
        for quiz in all_quizzes:
            quiz_search = quiz_search.lower()
            quiz_name = quiz.name.lower()
            if quiz_search in quiz_name:
                quizzes.append(quiz)
    else:
        quizzes = Quizzes.query.all()

    subjects = Subjects.query.all()
    return render_template('quizzes.html', subjects=subjects, quizzes=quizzes)


# I handcoded this route through-and-through, Im proud
@app.route('/summary')
def summary():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    if session['role'] == 'superadmin' or session['role'] == 'admin':
        flash('Sign in as a user.', 'error')
        return redirect(url_for('admin_summary'))

    subjects = Subjects.query.all()
    sub_name_list = []
    sub_id_list = []
    for subject in subjects:
        sub_name_list.append(subject.name)
        sub_id_list.append(subject.id)

    quizzes_attempted_per_sub_list = []
    for sub_id in sub_id_list:
        count = 0
        scores = Scores.query.filter_by(user_id=session['user_id']).all()
        if scores:
            for score in scores:
                if score.quiz.subject_id == sub_id:
                    count += 1
        else:
            count = 0
        quizzes_attempted_per_sub_list.append(count)

    correct_no = 0
    incorrect_no = 0
    scores = Scores.query.filter_by(user_id=session['user_id']).all()
    if scores:
        for score in scores:
            correct_no += ((score.score_percentage/100)
                           * len(score.correct_answers))
            incorrect_no += len(score.correct_answers) - correct_no

    # print(len(quizzes_attempted_per_sub_list))
    # print(len(sub_name_list))

    return render_template('summary.html', sub_name_list=sub_name_list, quizzes_attempted_per_sub_list=quizzes_attempted_per_sub_list, correct_no=correct_no, incorrect_no=incorrect_no)


@app.route('/admin-summary')
def admin_summary():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    if session['role'] == 'user':
        flash('Sign in as an admin.', 'error')
        return redirect(url_for('summary'))

    subjects = Subjects.query.all()
    sub_name_list = []
    sub_id_list = []
    for subject in subjects:
        sub_name_list.append(subject.name)
        sub_id_list.append(subject.id)

    highest_score_list = []
    for sub_id in sub_id_list:
        highest_score = db.session.query(
            Scores.score_percentage
        ).join(
            Quizzes, Scores.quiz_id == Quizzes.id
        ).filter(
            Quizzes.subject_id == sub_id
        ).order_by(
            Scores.score_percentage.desc()
        ).first()
        if highest_score:
            highest_score_list.append(highest_score[0])
        else:
            highest_score_list.append(0)

    good_students = 0
    average_students = 0
    bad_students = 0

    users = User.query.all()
    for user in users:
        performance = db.session.query(
            func.avg(Scores.score_percentage)
        ).filter_by(
            user_id=user.id
        ).scalar()

        if performance is not None:
            if performance >= 70:
                good_students += 1
            elif performance >= 40:
                average_students += 1
            else:
                bad_students += 1

    return render_template('admin_summary.html',
                           sub_name_list=sub_name_list,
                           highest_score_list=highest_score_list,
                           good_students=good_students,
                           average_students=average_students,
                           bad_students=bad_students
                           )


@app.route('/forget-selections/<int:quiz_id>')
def forget_selections(quiz_id):
    session.pop('attempted_answers_dict', None)
    user_id = session['user_id']
    return redirect(url_for('start_quiz', quiz_id=quiz_id, user_id=user_id))


@app.route('/add-admin', methods=['GET', 'POST'])
def add_admin():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    if session['role'] == 'user':
        flash('Sign in as an admin.', 'error')
        return redirect(url_for('dashboard'))
    elif session['role'] == 'admin':
        flash('Sign in as a superadmin.', 'error')
        return redirect(url_for('admin-dashboard'))
    else:
        if request.method == 'POST':
            email = request.form['email']
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            full_name = request.form['name']
            qualification = request.form['qualification']
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d')
            role = 'admin'

            new_user = User(email=email, username=username,
                            password=password, full_name=full_name, qualification=qualification, dob=dob, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Admin added successfully.', 'success')
            return redirect(url_for('admin-dashboard'))

        return render_template('add_admin.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('attempted_answers_dict', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
