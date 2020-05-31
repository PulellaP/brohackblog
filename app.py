from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_dance.contrib.github import make_github_blueprint, github
from flask_login import UserMixin, current_user, LoginManager, login_required, login_user, logout_user
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import secure_filename
import os
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nerdchat.db'
app.config['SECRET_KEY'] = 'thisissupposedtobesecret'
app.config['IMAGE_UPLOADS'] = os.getcwd()+'/static/images'
app.config['ALLOWED_IMAGE_EXTENSIONS'] = ['PNG', 'JPG', 'JPEG', 'SVG']
app.config['IMAGE_SIZE_LIMIT'] = 1603900
db = SQLAlchemy(app)
login_manager = LoginManager(app)

if os.path.isdir(app.config['IMAGE_UPLOADS']) == False:
    os.mkdir(app.config['IMAGE_UPLOADS'])

def allowed_image(filename):
    if not '.' in filename:
        return False
    ext = filename.rsplit('.', 1)[1]

    if ext.upper() in app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return True
    else:
        return False

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True)
    is_author = db.Column(db.Boolean, default=False, server_default="false")


class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)

class Article(db.Model):
    article_id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), db.ForeignKey(User.username))
    title = db.Column(db.String(250), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

make_github_blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user)

github_blueprint = make_github_blueprint(client_id='51f9ff7ae3641081141f', client_secret='063ab0b5f12d7dd73c4b39e8f889b65b9218ded1')

app.register_blueprint(github_blueprint, url_prefix='/github_login')

@app.route('/login')
def github_login():
    if not github.authorized:
        return redirect(url_for('github.login'))

    account_info = github.get('/user')
    account_info_json = account_info.json()

    account_user = User.query.filter_by(username=account_info_json['login']).first()
    if account_info_json['login'] == 'PulellaP' or 'RosarioPulella':
        account_user.is_author = True
        db.session.commit()

    if account_user.is_author == True:
        return f"<h1>Your github name is {account_info_json['login']} and you are an author</h1>"
    else:
        return f"<h1>Your github name is {account_info_json['login']}</h1>"

@oauth_authorized.connect_via(github_blueprint)
def github_logged_in(blueprint, token):
    account_info = blueprint.session.get('/user')

    if account_info.ok:
        account_info_json = account_info.json()
        username = account_info_json['login']

        query = User.query.filter_by(username=username)

        try:
            user = query.one()
        except NoResultFound:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        login_user(user)


@app.route('/')
def landing():
    return redirect(url_for('index', page_num=1))

@app.route('/home/<int:page_num>')
def index(page_num):
    page_name = 'Articles'
    post_page = Article.query.paginate(per_page=5, page=page_num, error_out=True)
    return render_template('index.html', post_page=post_page)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index', page_num=1))

@app.route('/Write-Article', methods=['GET', 'POST'])
@login_required
def Write_Article():
    if request.method == 'POST' and current_user.is_author == True:
        account_info = github.get('/user')
        account_info_json = account_info.json()
        author = account_info_json['login']
        post_title = request.form['title']
        post_content = request.form['content']
        if request.files:
            file = request.files['myImage']
            if file.filename == '':
                return render_template('Write-Article.html', page_name = 'New Post', alert = 'Image must have a filename')
            if allowed_image(file.filename) == False:
                return render_template('Write-Article.html', page_name = 'New Post', alert = 'Invalid filename')

            else:
                if sys.getsizeof(file) > app.config['IMAGE_SIZE_LIMIT']:
                    alertvar = 'Image size limit is ' + str(app.config['IMAGE_SIZE_LIMIT'])
                    return render_template('Write-Article.html', page_name = 'New Post', alert = alertvar)
                filename = secure_filename(file.filename)
                directory = os.path.join(app.config['IMAGE_UPLOADS'], author)
                if os.path.isdir(directory) == False:
                    os.mkdir(directory)
                file.save(os.path.join(directory, filename))
        new_post = Article(author = author, title = post_title, content = post_content)
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('index', page_num=1))

    else:
        return render_template('Write-Article.html', page_name = 'New Post')

@app.route('/users/<string:users>')
def show_users_page(users):
    account_user = User.query.filter_by(username=users).first()
    id = account_user.id
    username = account_user.username
    page_name = f'{username}\'s homepage'
    user_articles = Article.query.filter_by(author=username).all()
    return render_template('Userpages.html', page_name = page_name, Users_Articles=user_articles, username = username)

@app.route('/articles/<int:id>')
def display_article(id):
    article = Article.query.filter_by(article_id=id).first()
    return render_template('article.html', title = article.title, content = article.content, author = article.author)


if __name__ == "__main__":
    app.run(debug=True)
