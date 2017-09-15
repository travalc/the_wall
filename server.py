from flask import Flask, request, render_template, redirect, session, flash
from mysqlconnection import MySQLConnector
import re, md5, os, binascii

app = Flask(__name__)
app.secret_key = 'mySecretKey'
mysql = MySQLConnector(app, 'the_wall')

@app.route('/', methods = ['GET'])
def index():
    session['logged_in'] = False
    session['user_id'] = None
    print session['first_name']
    return render_template('index.html')
@app.route('/registration', methods=['GET'])
def registration():
    return render_template('registration.html')
@app.route('/wall', methods=['GET'])
def logged_in():
    if session['new_registration_email']:
        select_query = 'SELECT * FROM users WHERE users.email = :email'
        select_data = { 'email': session['new_registration_email'] }
        user = mysql.query_db(select_query, select_data)
        session['user_id'] = user[0]['id']
        session['first_name'] = user[0]['first_name']
        session['last_name'] = user[0]['last_name']
        session['email'] = user[0]['email']
        session['new_registration_email'] = None
    select_query = 'SELECT messages.id, messages.message, users.first_name, users.last_name, messages.user_id, messages.created_at FROM messages JOIN users ON users.id = messages.user_id'
    messages = mysql.query_db(select_query)
    messages_and_comments = []
    for message in messages:
        message_with_comments = message
        comments_data = { 'message_id': int(message['id']) }
        comments_query = 'SELECT comments.id, comments.comment, comments.user_id, comments.created_at, comments.updated_at, users.first_name, users.last_name FROM comments JOIN users ON users.id = comments.user_id WHERE comments.message_id = :message_id'
        message_with_comments['comments'] = mysql.query_db(comments_query, comments_data)
        messages_and_comments.append(message_with_comments)
    messages_and_comments.reverse()
    print messages_and_comments[1]['user_id']
    return render_template('wall.html', all_messages = messages_and_comments)
@app.route('/register', methods=['POST'])
def register():  
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    email_regex = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
    select_query = 'SELECT * FROM users WHERE users.email = :email'
    select_data ={ 'email': email }
    users = mysql.query_db(select_query, select_data)
    if len(first_name) < 1 or len(last_name) < 1:
        flash('First name and last name are required')
        return redirect('/registration')
    if first_name.isalpha() == False or last_name.isalpha() == False:
        flash('First name and last name must contain letters only')
        return redirect('/registration')
    if len(email) < 1:
        flash('Email is required')
        return redirect('/registration')
    if not email_regex.match(email):
        flash('Invalid email')
        return redirect('/registration')
    for user in users:        
        if email == user['email'] :
            flash('That user/email already exists')
            return redirect('/registration')
    if len(password) < 1 or len(confirm_password) < 1:
        flash('Password and password confirmation are both required')
        return redirect('/registration')
    if password != confirm_password:
        flash('Password and confirm password must match!')
        return redirect('/registration')
    else:
        salt = binascii.b2a_hex(os.urandom(15))
        hashed_and_salted_password = md5.new(password + salt).hexdigest()
    insert_query = 'INSERT INTO users (first_name, last_name, email, password, salt, created_at, updated_at) VALUES(:first_name, :last_name, :email, :password, :salt, NOW(), NOW())'
    insert_data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'password': hashed_and_salted_password,
        'salt': salt
    }
    mysql.query_db(insert_query, insert_data)
    session['new_registration_email'] = email
    session['logged_in'] = True
    return redirect('/wall')
@app.route('/log_in', methods=['POST'])
def log_in():
    email = request.form['email']
    password = request.form['password']
    select_query = 'SELECT * FROM users WHERE users.email = :email'
    select_data = { 'email': email }
    user = mysql.query_db(select_query, select_data)
    if len(user) > 0:
        encrypted_password = md5.new(password + user[0]['salt']).hexdigest()
        if user[0]['password'] == encrypted_password:
            session['logged_in'] = True
            session['user_id'] = user[0]['id']
            session['first_name'] = user[0]['first_name']
            session['last_name'] = user[0]['last_name']
            session['email'] = user[0]['email']
            print user
            return redirect('/wall')
        else:
            flash('That password does not match the username')
            return redirect('/')
    else:
        flash('That username does not exist in our records')
        return redirect('/')
@app.route('/log_off', methods=['GET'])
def log_off():
    session['logged_in'] = False
    session['user_id'] = None
    session['first_name'] = None
    session['last_name'] = None
    session['email'] = None
    return redirect('/')
@app.route('/add_message', methods=['POST'])
def add_message():
    message = request.form['message']
    if len(message) < 1:
        flash('Messages cannot be empty')
    else:
        data = {
            'user_id': str(session['user_id']),
            'message': message,
        }
        insert_query = 'INSERT INTO messages (user_id, message, created_at, updated_at) VALUES (:user_id, :message, NOW(), NOW())'
        mysql.query_db(insert_query, data)
        flash('Message posted!')
    return redirect('/wall')
@app.route('/add_comment', methods=['POST'])
def add_comment():
    comment = request.form['comment']
    message_id = request.form['message_id']
    if len(comment) < 1:
        flash('Comments cannot be empty')
    else:
        data = {
            'message_id': message_id,
            'comment': comment,
            'user_id': session['user_id'],
        }
        insert_query = 'INSERT INTO comments (message_id, comment, user_id, created_at, updated_at) VALUES (:message_id, :comment, :user_id, NOW(), NOW())'
        mysql.query_db(insert_query, data)
        flash('Comment posted!')
    return redirect('wall')
@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    comment = request.form['comment_delete']
    data = {
        'comment_id': int(comment)
    }
    query = 'DELETE FROM comments WHERE comments.id = :comment_id'
    mysql.query_db(query, data)
    flash('Comment deleted')
    return redirect('/wall')
@app.route('/delete_message', methods=['POST'])
def delete_message():
    message = request.form['message_delete']
    print message
    data = {
        'message_id': int(message)
    }
    comment_query = 'DELETE FROM comments WHERE comments.message_id = :message_id'
    message_query = 'DELETE FROM messages WHERE messages.id = :message_id'
    mysql.query_db(comment_query, data)
    mysql.query_db(message_query, data)
    flash('Message deleted')
    return redirect('/wall')
app.run(debug=True)