# 3rd-party packages
from flask import render_template, request, redirect, url_for, flash
from flask_mongoengine import MongoEngine
from flask_login import (
    LoginManager,
    current_user,
    login_user,
    logout_user,
    login_required,
)

from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

# stdlib
from datetime import datetime

# local
from . import app, bcrypt, client
from .forms import (
    SearchForm,
    MovieReviewForm,
    RegistrationForm,
    LoginForm,
    UpdateUsernameForm,
    UpdateProfilePicForm,
)
from .models import User, Review, load_user
from .utils import current_time
import io
import base64

""" ************ View functions ************ """


@app.route("/", methods=["GET", "POST"])
def index():
    query_form = SearchForm()
    results = client.search("Marvel")
    img1= results[1].poster_url
    img2= results[2].poster_url
    img3= results[3].poster_url
    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    return render_template("index.html", query_form=query_form, img1= img1,img2=img2,img3=img3)


@app.route("/search-results/<query>", methods=["GET"])
def query_results(query):
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    try:
        results = client.search(query)
    except ValueError as e:
        return render_template("query.html", error_msg=str(e),query_form=query_form)

    return render_template("query.html", results=results,query_form=query_form)


@app.route("/movies/<movie_id>", methods=["GET", "POST"])
def movie_detail(movie_id):
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    try:
        result = client.retrieve_movie_by_id(movie_id)
    except ValueError as e:
        return render_template("movie_detail.html", error_msg=str(e),query_form=query_form)

    form = MovieReviewForm()
    if form.validate_on_submit():
        review = Review(
            commenter=current_user._get_current_object(),
            content=form.text.data,
            date=current_time(),
            imdb_id=movie_id,
            movie_title=result.title,
        )

        review.save()

        return redirect(request.path)

    reviews = Review.objects(imdb_id=movie_id)

    return render_template(
        "movie_detail.html", form=form, movie=result, reviews=reviews,query_form=query_form
    )


@app.route("/user/<username>")
def user_detail(username):
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    user= User.objects(username=username).first()
    if user is None:
        flash('User not found')
        return render_template('user_detail.html',query_form=query_form, exist = False)
    else:
        review_list = Review.objects(commenter=user)
        if user.picture is None:
            image = None
        else:
            bytes_im = io.BytesIO(user.picture.read())
            image = base64.b64encode(bytes_im.getvalue()).decode()
        size = len(review_list)
        return render_template('user_detail.html', reviews = review_list, image=image, username=username, num = size,query_form=query_form, exist=True)

@app.errorhandler(404)
def custom_404(e):
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    return render_template('404.html',query_form=query_form), 404


""" ************ User Management views ************ """


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.objects(username=form.username.data).first() is not None:
            flash("Username already taken")
            return redirect(url_for('register'))
        if User.objects(email=form.email.data).first() is not None:
            flash("Email already taken")
            return redirect(url_for('register'))
        hashed = bcrypt.generate_password_hash(form.password.data)#.decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed)
        user.save()
        return redirect(url_for('login'))
    
        
    return render_template('register.html', title='Register', form=form,query_form=query_form)



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = LoginForm()
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    if form.validate_on_submit():
        user = User.objects(username=form.username.data).first()

        if (user is not None and bcrypt.check_password_hash(user.password,form.password.data)):
            login_user(user)
            return redirect(url_for('account'))
        else:
            flash('login failed')
            return redirect(url_for('login'))

    return render_template('login.html', title='Login', form=form,query_form=query_form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    #forms
    picture_form = UpdateProfilePicForm()
    user_form = UpdateUsernameForm()
    query_form = SearchForm()

    if query_form.validate_on_submit():
        return redirect(url_for("query_results", query=query_form.search_query.data))

    
    if current_user.picture.get() is None:
        image = None
    else:
        bytes_im = io.BytesIO(current_user.picture.read())
        image = base64.b64encode(bytes_im.getvalue()).decode()
    #update picures
    if picture_form.validate_on_submit():
        img = picture_form.picture.data
        filename = secure_filename(img.filename)
        content_type = f'images/{filename[-3:]}'

        if current_user.picture.get() is None:
            current_user.picture.put(img.stream, content_type=content_type)
        else:
            current_user.picture.replace(img.stream, content_type=content_type)
    
        current_user.save()

        return redirect(url_for('account'))
    #check if username is taken
    if user_form.validate_on_submit():
        user = User.objects(username= user_form.username.data).first()
        if user is None:
            current_user.modify(username = user_form.username.data) # can also use .modify(username = new username)
            current_user.save()
        else:
            flash('Username not available')
        redirect(url_for('account'))

    return render_template('account.html',picture_form=picture_form,user_form=user_form, image=image,query_form=query_form)
