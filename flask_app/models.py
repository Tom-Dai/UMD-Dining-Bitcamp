from flask_login import UserMixin
from datetime import datetime
from . import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.objects(email = user_id).first()


class User(db.Document, UserMixin):
    username = db.StringField(unique=True, required=True)
    email = db.StringField(unique=True, required=True)
    password = db.StringField(required = True)
    picture = db.ImageField()
    # Returns unique string identifying our object
    def get_id(self):
        #using email since that is guranteed to be unique and also cannot be changed
        return self.email


class Review(db.Document):
    commenter = db.ReferenceField(User)
    content = db.StringField()
    date = db.StringField()
    imdb_id = db.StringField(max_length = 9, min_length=9)
    movie_title = db.StringField(max_length = 100, min_length= 1)
    

