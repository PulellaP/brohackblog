from app import db, Article, Topics
from sqlalchemy.sql import select, text

#obj = Article.query.join(Topics, Article.topics).order_by(Article.article_id.desc()).paginate(per_page=5, page=1, error_out=True)
#obj = Article.query.outerjoin(Topics, Article.topics)

#obj2 = obj.order_by(Article.article_id)

#obj = db.session.execute(
#    select([text('article_id'), text('author'), text('title'), text('content'), text('date_time'), text('head_image')])
#    .select_from(
#        Article.outerjoin(Topics, Article.topics == Topics.topic_name)
#    )
#    )

obj = db.session.query(Article.article_id, Article.author, Article.title, Article.date_time, Article.head_image).outerjoin(Topics, Article.topics == Topics.topic_name)

obj2 = obj.all()
print(obj)
print(obj2)

#for x in obj.items:
#    print(x.topic_articles.append())
