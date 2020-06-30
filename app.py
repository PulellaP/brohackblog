from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime
from flask_dance.contrib.github import make_github_blueprint, github
from flask_login import UserMixin, current_user, LoginManager, login_required, login_user, logout_user
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import secure_filename
from markdown2 import Markdown
from config import database_string, github_client_secret, github_client_id
import os
import sys
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_string
app.config['SECRET_KEY'] = os.urandom(16)
db = SQLAlchemy(app)
login_manager = LoginManager(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True)
    is_author = db.Column(db.Boolean, default=False, server_default="false")


class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)

Topic_Article_join = db.Table('Topic_Article_join',
    db.Column('article_id', db.Integer, db.ForeignKey('article.article_id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topics.topic_id')),
    db.PrimaryKeyConstraint('article_id', 'topic_id')
    )

class Article(db.Model):
    article_id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), db.ForeignKey(User.username))
    title = db.Column(db.String(250), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    head_image = db.Column(db.String(500))
    topics = db.relationship('Topics', secondary=Topic_Article_join, back_populates='articles')

class Topics(db.Model):
    topic_id = db.Column(db.Integer, primary_key=True)
    topic_name = db.Column(db.String(20))
    articles = db.relationship('Article', secondary=Topic_Article_join, back_populates='topics')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

make_github_blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user)

github_blueprint = make_github_blueprint(client_id=github_client_id, client_secret=github_client_secret)

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
        return redirect(url_for('index', page_num=1))

    else:
        return redirect(url_for('index', page_num=1))

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
    #post_page = Article.query.join(Topics, Article.topics).order_by(Article.article_id.desc()).paginate(per_page=5, page=page_num, error_out=True)
    #post_page = Article.query.order_by(Article.article_id.desc()).paginate(per_page=5, page=page_num, error_out=True)
    query = Article.query.join(Topics, Article.topics)
    post_page = query.order_by(Article.article_id.desc()).paginate(per_page=5, page=page_num, error_out=True)
    topics_variable = Topics.query.all()
    return render_template('index.html', post_page=post_page, current_user= current_user, topicslist=topics_variable)

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
        subjects = re.split('::', request.form['subjects'])
        image_link = request.form['image']
        new_post = Article(author = author, title = post_title, content = post_content, head_image=image_link)
        for x in subjects:
            new_subjects = Topics(topic_name = x)
            new_post.topics.append(new_subjects)

        db.session.add(new_post)
        db.session.commit()
        # new_post = Article.query.filter_by(title = post_title).first()

        return redirect(url_for('index', page_num=1))

    else:
        return render_template('Write-Article.html', page_name = 'New Post')

@app.route('/article_topics/<string:name>')
def search_articles_by_topics(name):
    in_function_topic_variable = Topics(topic_name=name)
    return render_template('index.html', post_page=in_function_topic_variable.article_topics, current_user= current_user)



@app.route('/articles/<int:id>/edit', methods = ['GET', 'POST'])
@login_required
def Edit_Articles(id):
    article = Article.query.filter_by(article_id=id).first()
    if request.method == 'GET' and current_user.username == article.author:
        subjects = (x.topic_name for x in article.topics)
        subjects = "::".join(subjects)
        return render_template('edit.html', content = article.content, image = article.head_image, subjects = subjects, title = article.title, author = article.author, id = id)

    if request.method == 'POST' and current_user.username == article.author:
        article.content = request.form['content']
        article.head_image = request.form['image']
        if request.form['subjects'] == None:
            article.topics = ''
        else:
            subjects = re.split('::', request.form['subjects'])
            for x in subjects:
                new_subjects = Topics(topic_name = x)
                article.topics.append(new_subjects)

        db.session.commit()
        return redirect(url_for('display_article', id=id))


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
    md = Markdown()
    head_image = article.head_image
    return render_template('article.html', title = article.title, content = md.convert(article.content), author = article.author, head_image = head_image)


if __name__ == "__main__":
    app.run(debug=True)
