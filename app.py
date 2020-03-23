from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_dance.contrib.github import make_github_blueprint, github
from flask_login import UserMixin, current_user, LoginManager, login_required, login_user, logout_user
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nerdchat.db'
app.config['SECRET_KEY'] = 'thisissupposedtobesecret'
db = SQLAlchemy(app)
login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True)

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

@app.route('/github')
def github_login():
    if not github.authorized:
        return redirect(url_for('github.login'))

    account_info = github.get('/user')
    account_info_json = account_info.json()

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
def index():
    page_name = 'Latest Posts'
    all_posts = Article.query.order_by(Article.date_time).all()
    return render_template('index.html', page_name=page_name, posts = all_posts)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/Write-Article', methods=['GET', 'POST'])
@login_required
def Write_Article():
    if request.method == 'POST':
        account_info = github.get('/user')
        account_info_json = account_info.json()
        author = account_info_json['login']
        post_title = request.form['title']
        post_content = request.form['content']
        new_post = Article(author = author, title = post_title, content = post_content)
        db.session.add(new_post)
        db.session.commit()

        return redirect('/')

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


if __name__ == "__main__":
    app.run(debug=True)
